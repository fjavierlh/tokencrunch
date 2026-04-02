"""Integration tests for the proxy — FastAPI app with a mocked upstream.

Uses httpx.AsyncClient with ASGITransport to call the proxy without binding
to a real port, and respx to intercept the outbound httpx calls to upstream.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from tokencrunch.config import Config, ProxyConfig
from tokencrunch.layers.syntactic import SyntacticLayer
from tokencrunch.pipeline import Pipeline
from tokencrunch.proxy import create_app

UPSTREAM = "http://mock-upstream"


@pytest.fixture
def app():
    cfg = Config()
    cfg.proxy = ProxyConfig(port=7420, upstream=UPSTREAM, log_savings=False)
    pipeline = Pipeline()
    pipeline.add_layer(SyntacticLayer(enabled=True))
    return create_app(cfg, pipeline)


@pytest.fixture
def client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ---------------------------------------------------------------------------
# Message compression
# ---------------------------------------------------------------------------

class TestMessageCompression:
    @respx.mock
    async def test_messages_compressed_before_forwarding(self, client):
        """Proxy strips trailing whitespace from messages before sending to upstream."""
        upstream_received = {}

        def capture(request):
            upstream_received["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "msg_1"})

        respx.post(f"{UPSTREAM}/v1/messages").mock(side_effect=capture)

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 100,
            "messages": [{"role": "user", "content": "hello   \n\n\nworld   "}],
        }
        await client.post("/v1/messages", json=payload)

        compressed_content = upstream_received["body"]["messages"][0]["content"]
        assert "   " not in compressed_content
        assert compressed_content == "hello\n\nworld"

    @respx.mock
    async def test_non_message_fields_preserved(self, client):
        """model, max_tokens, system, etc. must pass through unchanged."""
        upstream_received = {}

        def capture(request):
            upstream_received["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "msg_1"})

        respx.post(f"{UPSTREAM}/v1/messages").mock(side_effect=capture)

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 512,
            "system": "You are helpful.",
            "messages": [{"role": "user", "content": "hi"}],
        }
        await client.post("/v1/messages", json=payload)

        body = upstream_received["body"]
        assert body["model"] == "claude-3-5-sonnet-20241022"
        assert body["max_tokens"] == 512
        assert body["system"] == "You are helpful."

    @respx.mock
    async def test_response_forwarded_to_client(self, client):
        """Response from upstream arrives at the client unchanged."""
        respx.post(f"{UPSTREAM}/v1/messages").mock(
            return_value=httpx.Response(200, json={"id": "msg_1", "content": "hello"})
        )
        payload = {
            "messages": [{"role": "user", "content": "hi"}],
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 10,
        }
        response = await client.post("/v1/messages", json=payload)
        assert response.status_code == 200
        assert response.json()["id"] == "msg_1"


# ---------------------------------------------------------------------------
# Passthrough for non-compressible requests
# ---------------------------------------------------------------------------

class TestPassthrough:
    @respx.mock
    async def test_non_json_body_passed_through(self, client):
        """Binary / non-JSON bodies must arrive at upstream unchanged."""
        upstream_received = {}

        def capture(request):
            upstream_received["body"] = request.content
            return httpx.Response(200, content=b"ok")

        respx.post(f"{UPSTREAM}/v1/other").mock(side_effect=capture)

        raw = b"\x00\x01\x02binary"
        await client.post("/v1/other", content=raw, headers={"content-type": "application/octet-stream"})
        assert upstream_received["body"] == raw

    @respx.mock
    async def test_json_without_messages_passed_through(self, client):
        """JSON body without a 'messages' key is forwarded as-is."""
        upstream_received = {}

        def capture(request):
            upstream_received["body"] = json.loads(request.content)
            return httpx.Response(200, json={})

        respx.post(f"{UPSTREAM}/v1/count_tokens").mock(side_effect=capture)

        payload = {"model": "claude-3-5-sonnet-20241022", "system": "hello"}
        await client.post("/v1/count_tokens", json=payload)
        assert upstream_received["body"] == payload

    @respx.mock
    async def test_get_request_forwarded(self, client):
        respx.get(f"{UPSTREAM}/v1/models").mock(
            return_value=httpx.Response(200, json={"models": []})
        )
        response = await client.get("/v1/models")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Header handling
# ---------------------------------------------------------------------------

class TestHeaders:
    @respx.mock
    async def test_authorization_header_forwarded(self, client):
        upstream_received = {}

        def capture(request):
            upstream_received["headers"] = dict(request.headers)
            return httpx.Response(200, json={})

        respx.post(f"{UPSTREAM}/v1/messages").mock(side_effect=capture)

        await client.post(
            "/v1/messages",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"authorization": "Bearer sk-test"},
        )
        assert upstream_received["headers"].get("authorization") == "Bearer sk-test"

    @respx.mock
    async def test_hop_by_hop_headers_not_forwarded(self, client):
        upstream_received = {}

        def capture(request):
            upstream_received["headers"] = dict(request.headers)
            return httpx.Response(200, json={})

        respx.post(f"{UPSTREAM}/v1/messages").mock(side_effect=capture)

        await client.post(
            "/v1/messages",
            json={"messages": [{"role": "user", "content": "hi"}]},
            headers={"connection": "keep-alive"},
        )
        assert "connection" not in upstream_received["headers"]


# ---------------------------------------------------------------------------
# SSE streaming
# ---------------------------------------------------------------------------

class TestSSEStreaming:
    @respx.mock
    async def test_sse_response_streamed_back(self, client):
        """Proxy must pass SSE chunks through to the client."""
        sse_body = b"data: {}\n\ndata: [DONE]\n\n"
        respx.post(f"{UPSTREAM}/v1/messages").mock(
            return_value=httpx.Response(
                200,
                content=sse_body,
                headers={"content-type": "text/event-stream"},
            )
        )
        payload = {
            "messages": [{"role": "user", "content": "hi"}],
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 10,
            "stream": True,
        }
        response = await client.post("/v1/messages", json=payload)
        assert response.status_code == 200
        assert b"data:" in response.content
