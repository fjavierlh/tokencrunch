# Roadmap

## Phase 1 — Functional proxy (MVP)
> The proxy starts up, forwards requests to the API, and measures tokens.

- [x] Project structure and base documentation
- [ ] HTTP proxy with FastAPI that forwards requests to upstream
- [ ] SSE streaming passthrough support
- [ ] Token counting (before/after) with metrics in logs
- [ ] CLI: `tokencrunch start` / `tokencrunch stop`

## Phase 2 — Lossless layers
> Compression with no risk of quality loss.

- [ ] **Syntactic layer**: strip whitespace, comments, empty lines
- [ ] **Serialization layer**: JSON minification, TOON conversion
- [ ] **Dedup layer**: LTSC-style repeated sequence replacement
- [ ] TOML config with per-layer toggle
- [ ] Per-layer metrics dashboard (terminal)

## Phase 3 — Advanced layers
> ML-based compression and smart caching.

- [ ] **Semantic layer**: LLMLingua-2 integration
- [ ] **Cache layer**: embedding-based semantic cache
- [ ] Configurable rate limiting per layer
- [ ] Quality regression tests

## Phase 4 — Production
> Ready for daily use.

- [ ] Publish to PyPI
- [ ] Complete documentation
- [ ] Reproducible benchmarks
- [ ] Tested integration with Claude Code, opencode, aider
- [ ] GitHub Actions CI/CD
