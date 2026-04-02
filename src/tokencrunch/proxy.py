"""Transparent HTTP proxy for LLM API traffic.

This module implements the core proxy that sits between a coding assistant
and the LLM provider. It:

1. Receives HTTP requests on localhost (typically POST /v1/messages)
2. Extracts the messages array from the request body
3. Runs the compression pipeline on the messages
4. Forwards the compressed request to the upstream API
5. Streams the response back to the client (SSE passthrough)
6. Logs compression metrics

The proxy is intentionally minimal — it doesn't try to understand the full
Anthropic API spec, it just focuses on compressing the `messages` field
and passing everything else through unchanged.
"""

from __future__ import annotations

import json
import logging
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from tokencrunch.config import Config
from tokencrunch.pipeline import Pipeline

logger = logging.getLogger("tokencrunch.proxy")


def create_app(config: Config, pipeline: Pipeline) -> FastAPI:
    """Create the FastAPI proxy application.

    Args:
        config: Validated tokencrunch configuration.
        pipeline: The compression pipeline with active layers.

    Returns:
        FastAPI app ready to be served by uvicorn.
    """
    app = FastAPI(
        title="tokencrunch proxy",
        version="0.1.0",
        docs_url=None,  # No need for Swagger UI on a proxy
        redoc_url=None,
    )

    # Persistent HTTP client for upstream connections
    # Using HTTP/2 for better connection reuse with Anthropic's API
    client = httpx.AsyncClient(
        base_url=config.proxy.upstream,
        timeout=httpx.Timeout(300.0, connect=10.0),
        http2=True,
    )

    @app.on_event("shutdown")
    async def shutdown():
        await client.aclose()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_request(request: Request, path: str):
        """Forward any request to upstream, compressing messages if present."""

        # Read the raw body
        body = await request.body()

        # Build headers to forward (skip hop-by-hop headers)
        forward_headers = _build_forward_headers(request.headers)

        # Try to compress if it's a messages request with a JSON body
        compressed_body = body
        stats_line = None

        if request.method == "POST" and body:
            try:
                data = json.loads(body)
                if "messages" in data:
                    result = pipeline.compress(data["messages"])
                    data["messages"] = result.messages
                    compressed_body = json.dumps(data, ensure_ascii=False).encode("utf-8")

                    if config.proxy.log_savings:
                        stats_line = (
                            f"[tokencrunch] {result.total_stats.savings_pct} saved "
                            f"({result.total_stats.original_bytes}→"
                            f"{result.total_stats.compressed_bytes} bytes, "
                            f"{result.total_stats.total_time_ms:.1f}ms)"
                        )
                        for name, layer_stats in result.per_layer.items():
                            logger.info(
                                f"  └ {name}: {layer_stats.savings_ratio:.1%} savings, "
                                f"{layer_stats.processing_time_ms:.1f}ms"
                            )
            except (json.JSONDecodeError, KeyError):
                # Not a JSON request or no messages field — pass through
                pass

        # Forward to upstream
        start = time.perf_counter()
        upstream_response = await client.request(
            method=request.method,
            url=f"/{path}",
            headers=forward_headers,
            content=compressed_body,
            params=dict(request.query_params),
        )
        latency_ms = (time.perf_counter() - start) * 1000

        if stats_line:
            logger.info(f"{stats_line} | upstream: {latency_ms:.0f}ms")

        # Check if this is a streaming response (SSE)
        content_type = upstream_response.headers.get("content-type", "")

        if "text/event-stream" in content_type:
            # SSE streaming — pass through chunks as they arrive
            return StreamingResponse(
                _stream_sse(upstream_response),
                status_code=upstream_response.status_code,
                headers=_build_response_headers(upstream_response.headers),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming — return the full response
            response_body = upstream_response.content
            return StreamingResponse(
                iter([response_body]),
                status_code=upstream_response.status_code,
                headers=_build_response_headers(upstream_response.headers),
                media_type=content_type,
            )


    return app


async def _stream_sse(response: httpx.Response):
    """Stream SSE events from upstream to client.

    We pass through SSE events byte-for-byte without modification.
    Future versions may compress assistant responses in-flight.
    """
    async for chunk in response.aiter_bytes():
        yield chunk


# Headers that should NOT be forwarded between client and upstream
_HOP_BY_HOP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
    "content-length",  # Will be recalculated
})


def _build_forward_headers(headers) -> dict[str, str]:
    """Extract headers to forward to upstream, skipping hop-by-hop headers."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in _HOP_BY_HOP
    }


def _build_response_headers(headers) -> dict[str, str]:
    """Extract headers to return to client from upstream response."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in _HOP_BY_HOP
    }
