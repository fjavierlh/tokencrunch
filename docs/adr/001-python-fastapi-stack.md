# ADR-001: Python + FastAPI as the main stack

**Status:** Accepted
**Date:** 2026-04-02

## Context

We need to choose the language and framework to build an HTTP proxy that
intercepts LLM API calls and applies compression in real time.

Key requirements:
- Low added latency (the proxy must not noticeably slow down calls)
- SSE (Server-Sent Events) streaming support, which is how Claude sends responses
- Direct integration with LLMLingua-2 (Microsoft's Python library)
- Low barrier to contribution for the open-source community

## Decision

We use **Python 3.12+** with **FastAPI** and **uvicorn** as the ASGI server.

## Alternatives considered

### Rust (like lessloss and RTK)
- ✅ Maximum performance, single binary with no dependencies
- ❌ LLMLingua-2 is Python → would require FFI or subprocess, adding complexity
- ❌ High entry barrier for contributors
- ❌ Slower development for a prototype

### TypeScript/Bun
- ✅ Good performance, rich npm ecosystem
- ❌ Same problem with LLMLingua-2 (would need a Python child process)
- ❌ Much weaker ML/NLP ecosystem than Python

### Go
- ✅ Good performance, single binary, great for HTTP proxies
- ❌ Same problem with LLMLingua-2
- ❌ Limited ML ecosystem

## Consequences

### Positive
- Native integration with LLMLingua-2, tree-sitter, and the full Python ML ecosystem
- Low contribution barrier (Python is the most popular language)
- FastAPI auto-generates OpenAPI documentation for the proxy
- uvicorn is async, handling concurrent connections and streaming well

### Negative
- Higher memory usage than Rust/Go (~50-100MB vs ~10MB)
- Slightly higher latency (~5-20ms per request vs ~1ms in Rust)
- Requires Python installed (not a self-contained binary)
- Python's GIL limits CPU-bound parallelism (mitigable with ProcessPoolExecutor)

### Mitigations
- Proxy latency (~10ms) is negligible compared to LLM latency (~1-5s)
- We can package with PyInstaller or similar for distribution
- CPU-intensive layers (tree-sitter, LLMLingua) run in a process pool
