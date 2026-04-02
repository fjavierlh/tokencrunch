# CLAUDE.md — Project context for Claude Code

## What is tokencrunch?

A transparent HTTP proxy that compresses LLM API traffic to reduce token costs
by 30–70%. It sits between AI coding assistants (Claude Code, opencode, aider)
and the LLM provider, applying a configurable pipeline of compression layers.

## Architecture overview

```
Client (Claude Code) → localhost:7420 → [Compression Pipeline] → api.anthropic.com
```

### Compression pipeline (5 layers, executed in order)

1. **Syntactic** (lossless, ~25% savings) — Strip whitespace, comments, blank lines
2. **Serialization** (lossless, ~40% on structured data) — JSON → TOON, minification
3. **Dedup** (lossless, ~20-45%) — LTSC-style repeated token sequence replacement
4. **Semantic** (lossy, ~50%) — LLMLingua-2 ML-based prompt compression
5. **Cache** (N/A, ~100% on hits) — Embedding-based semantic similarity cache

Each layer implements the `CompressionLayer` protocol (see `src/tokencrunch/layers/__init__.py`).
Layers are toggled independently via `tokencrunch.toml`.

### Key design decisions

All documented as ADRs in `docs/adr/`:
- **ADR-001**: Python + FastAPI (because LLMLingua-2 is Python-native)
- **ADR-002**: Layered pipeline (each layer testable and toggleable)
- **ADR-003**: Transparent HTTP proxy (zero code changes for the user)
- **ADR-004**: TOML config (Python stdlib, supports comments)

## Project structure

```
src/tokencrunch/
├── __init__.py          # Package version
├── cli.py               # Click CLI: `tokencrunch start`, `tokencrunch info`
├── config.py            # TOML loading + pydantic validation
├── pipeline.py          # Orchestrates layers in sequence
├── proxy.py             # FastAPI HTTP proxy with SSE streaming
└── layers/
    ├── __init__.py      # CompressionLayer protocol + LayerStats
    └── syntactic.py     # Layer 1: lossless text normalization
tests/
    └── test_core.py     # Unit tests for syntactic layer + pipeline
docs/adr/                # Architecture Decision Records
```

## Current status (Phase 1 in progress)

### What's done
- Project structure, ADRs, README, ROADMAP
- Config system (TOML + pydantic + default path search)
- CompressionLayer protocol and Pipeline orchestrator
- Syntactic layer (blank line collapse, whitespace strip, tab normalization, optional comment removal)
- HTTP proxy skeleton with SSE streaming passthrough
- CLI with `start` and `info` commands
- Unit tests for syntactic layer and pipeline

### What's NOT done yet
- Layers 2-5 (serialization, dedup, semantic, cache) — stubs only
- Tests haven't been verified to pass yet (need `pip install -e ".[dev]"` first)
- No integration tests for the proxy
- No token counting (using byte-size approximation for now)
- No published package on PyPI

## Development commands

```bash
# Setup
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check src/ tests/

# Start the proxy
tokencrunch start
tokencrunch start --port 8080
tokencrunch info

# Run with config
tokencrunch start --config tokencrunch.toml
```

## Conventions

- **Commits**: Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`)
- **Branches**: Feature branches (`feat/layer-name`, `fix/issue-description`)
- **Merge**: Always `--no-ff` to preserve branch history in the graph
- **Tests**: Every layer needs unit tests. Pipeline tests verify orchestration.
- **ADRs**: New ADR for any decision that's hard to reverse or affects architecture.
- **Code style**: ruff with rules E, F, I, N, UP, B, SIM. Line length 100.

## Key technical notes

### SSE streaming
The Anthropic API uses Server-Sent Events for streaming responses. The proxy
must pass through SSE chunks byte-for-byte. Response compression (compressing
the assistant's output) is a future goal but tricky with streaming.

### Token counting
Exact token counting requires the model's tokenizer. We use byte-size
approximation (~4 bytes/token) for metrics. Anthropic offers a free
`/v1/messages/count_tokens` endpoint for exact counts — consider integrating
this for the metrics dashboard.

### Message format
Messages can have content as a string OR as a list of content blocks:
```python
# Simple string
{"role": "user", "content": "hello"}

# Content blocks (text, images, tool_use, tool_result)
{"role": "user", "content": [
    {"type": "text", "text": "look at this"},
    {"type": "image", "source": {"type": "base64", ...}},
]}
```
All layers MUST handle both formats. Only compress `type: "text"` blocks.

### Important research findings
- Compression sweet spot is r=0.5 (50% compression ratio)
- Aggressive compression (r=0.2) can INCREASE costs because the LLM generates
  more verbose output to compensate for missing context
- Syntactic compression (whitespace/formatting removal) has zero quality impact
- Binary formats (MessagePack, protobuf) do NOT reduce LLM tokens — LLMs
  consume text, and base64-encoding binary actually increases tokens by ~33%
- TOON format achieves ~40% fewer tokens than JSON with +2.7% accuracy improvement

## Next priorities (ROADMAP Phase 2)

1. Serialization layer (JSON minification + TOON conversion)
2. Dedup layer (LTSC repeated sequence replacement)
3. Config TOML toggle integration for new layers
4. Terminal metrics dashboard showing per-layer savings
