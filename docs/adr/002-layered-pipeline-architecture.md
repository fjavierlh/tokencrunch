# ADR-002: Layered pipeline architecture

**Status:** Accepted
**Date:** 2026-04-02

## Context

There are multiple token compression techniques (syntactic, serialization,
deduplication, semantic, cache). We need to decide how to combine them.

## Decision

Each compression technique is an **independent layer** with a common interface.
Layers execute sequentially forming a pipeline. Each layer can be
enabled/disabled individually.

```
Request → [Syntactic] → [Serialize] → [Dedup] → [Semantic] → [Cache] → API
Response ← [Syntactic] ← [Serialize] ← [Dedup] ←            ← [Cache] ← API
```

### Layer interface

```python
class CompressionLayer(Protocol):
    name: str
    def compress_request(self, messages: list[dict]) -> list[dict]: ...
    def compress_response(self, response: dict) -> dict: ...
    def get_stats(self) -> LayerStats: ...
```

### Execution order

The order matters and is fixed by design:

1. **Syntactic** first: transforms code/text to minimal form. This makes
   subsequent layers work with less text.
2. **Serialize**: converts data structures to compact formats.
3. **Dedup**: detects repeated sequences (more effective after normalization).
4. **Semantic**: ML compression (the most time-expensive, applied last).
5. **Cache**: if the entire request has been seen before, the API is skipped entirely.

## Alternatives considered

### Monolith (everything in one function)
- ❌ Impossible to disable individual techniques
- ❌ Hard to test and debug
- ❌ Does not let the user adjust risk level

### Dynamic plugin system (runtime plugin loading)
- ✅ Maximum extensibility
- ❌ Over-engineering for 5 known layers
- ❌ Adds complexity of discovery, ordering, and dependency resolution

## Consequences

### Positive
- The user controls exactly which layers to use (risk management)
- Each layer is tested in isolation
- Per-layer metrics show which technique contributes the most savings
- Easy to add new layers without touching existing ones

### Negative
- Overhead of passing data between layers (message copies). Mitigable with
  references/views.
- The fixed order may not be optimal for all cases. We accept this as a
  trade-off for simplicity.
