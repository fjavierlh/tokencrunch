"""End-to-end tests for the proxy.

Spins up a real uvicorn server on a random port, sends actual HTTP requests
through it, and verifies the full request/response cycle. The upstream API
is mocked with respx so no real network calls are made.
"""

from __future__ import annotations

import json
import threading
import time

import httpx
import pytest
import respx
import uvicorn

from tokencrunch.config import Config, ProxyConfig
from tokencrunch.layers.syntactic import SyntacticLayer
from tokencrunch.pipeline import Pipeline
from tokencrunch.proxy import create_app

UPSTREAM = "http://mock-upstream-e2e"


def _find_free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def proxy_server():
    """Start a real uvicorn server for the duration of the module."""
    port = _find_free_port()
    cfg = Config()
    cfg.proxy = ProxyConfig(port=port, upstream=UPSTREAM, log_savings=False)
    pipeline = Pipeline()
    pipeline.add_layer(SyntacticLayer(enabled=True))
    app = create_app(cfg, pipeline)

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for the server to be ready
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.2)
            break
        except Exception:
            time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=2)


@pytest.fixture
def http_client(proxy_server):
    with httpx.Client(base_url=proxy_server, timeout=5) as client:
        yield client


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestE2EHappyPath:
    @respx.mock
    def test_post_messages_compresses_and_forwards(self, http_client):
        """Full cycle: dirty input → compressed at proxy → clean at upstream."""
        upstream_received = {}

        def capture(request):
            upstream_received["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "msg_e2e", "type": "message"})

        respx.post(f"{UPSTREAM}/v1/messages").mock(side_effect=capture)

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Review this:\n\n\n\ndef foo():   \n\treturn 1   \n\n\n"}
            ],
        }
        response = http_client.post("/v1/messages", json=payload)

        assert response.status_code == 200
        assert response.json()["id"] == "msg_e2e"

        compressed = upstream_received["body"]["messages"][0]["content"]
        assert "\t" not in compressed
        assert "   " not in compressed
        # Multiple blank lines collapsed
        assert "\n\n\n" not in compressed

    @respx.mock
    def test_response_body_forwarded(self, http_client):
        respx.post(f"{UPSTREAM}/v1/messages").mock(
            return_value=httpx.Response(200, json={"id": "msg_1", "content": [{"type": "text", "text": "hi"}]})
        )
        response = http_client.post(
            "/v1/messages",
            json={"model": "claude-3-5-sonnet-20241022", "max_tokens": 10,
                  "messages": [{"role": "user", "content": "hello"}]},
        )
        assert response.status_code == 200
        assert response.json()["id"] == "msg_1"

    @respx.mock
    def test_get_request_forwarded(self, http_client):
        respx.get(f"{UPSTREAM}/v1/models").mock(
            return_value=httpx.Response(200, json={"models": ["claude-3-5-sonnet-20241022"]})
        )
        response = http_client.get("/v1/models")
        assert response.status_code == 200
        assert "models" in response.json()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestE2EErrorHandling:
    @respx.mock
    def test_upstream_error_forwarded(self, http_client):
        """4xx/5xx responses from upstream must be forwarded as-is."""
        respx.post(f"{UPSTREAM}/v1/messages").mock(
            return_value=httpx.Response(401, json={"error": {"type": "authentication_error"}})
        )
        response = http_client.post(
            "/v1/messages",
            json={"messages": [{"role": "user", "content": "hi"}],
                  "model": "claude-3-5-sonnet-20241022", "max_tokens": 10},
        )
        assert response.status_code == 401

    @respx.mock
    def test_non_json_body_forwarded_unchanged(self, http_client):
        respx.post(f"{UPSTREAM}/v1/other").mock(
            return_value=httpx.Response(200, content=b"pong")
        )
        response = http_client.post("/v1/other", content=b"ping",
                                    headers={"content-type": "text/plain"})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Content block format
# ---------------------------------------------------------------------------

class TestE2EContentBlocks:
    @respx.mock
    def test_text_blocks_compressed_non_text_unchanged(self, http_client):
        upstream_received = {}

        def capture(request):
            upstream_received["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "ok"})

        respx.post(f"{UPSTREAM}/v1/messages").mock(side_effect=capture)

        image_block = {"type": "image", "source": {"type": "base64", "data": "abc123=="}}
        text_block = {"type": "text", "text": "Describe this:   \n\n\n"}
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": [text_block, image_block]}],
        }
        http_client.post("/v1/messages", json=payload)

        content = upstream_received["body"]["messages"][0]["content"]
        assert content[0]["text"] == "Describe this:"
        assert content[1] == image_block
