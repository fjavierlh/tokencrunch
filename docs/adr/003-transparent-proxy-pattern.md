# ADR-003: Transparent HTTP proxy pattern

**Status:** Accepted
**Date:** 2026-04-02

## Context

We need to decide how tokencrunch integrates with existing coding assistants
(Claude Code, opencode, aider, etc.).

## Decision

tokencrunch works as a **transparent HTTP proxy** on localhost. The user
only needs to change one environment variable:

```bash
export ANTHROPIC_BASE_URL=http://localhost:7420
```

The proxy receives requests as-is, applies compression, forwards them to the
real upstream (api.anthropic.com), receives the response, processes it, and
returns it to the client.

## Alternatives considered

### SDK wrapper (library that wraps the API)
```python
from tokencrunch import CompressedClient
client = CompressedClient()  # wraps anthropic.Client
```
- ✅ Fine-grained control per message
- ❌ Requires changing user code
- ❌ Needs per-language implementation (Python, TS, Rust...)
- ❌ Does not work with CLI tools that don't expose their client

### Monkey-patching / import hook
- ✅ Zero config for Python apps
- ❌ Only works with Python
- ❌ Fragile, breaks with library updates

### MCP Server
- ✅ Native integration with Claude
- ❌ The agent must invoke the tool explicitly
- ❌ Adds overhead tokens (tool definitions, tool calls)
- ❌ Does not compress existing traffic, only adds tools

## Consequences

### Positive
- **Zero code changes**: works with ANY tool that supports a
  custom base URL (Claude Code, opencode, aider, direct API)
- A single proxy serves Python, TypeScript, Rust, curl, etc.
- The user can inspect traffic (useful for debugging)
- Easy to disable: remove the environment variable

### Negative
- Complexity of handling SSE streaming (chunks must be parsed and reassembled)
- The proxy must correctly forward ALL API headers
  (anthropic-version, anthropic-beta, authorization, etc.)
- On localhost we use plain HTTP (not HTTPS), which is safe but may confuse
  some tools. We document this.
- We cannot compress what does not go through HTTP (e.g., local files that
  Claude Code reads directly). A complementary CLI hook would be needed for
  that (future work).
