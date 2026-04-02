"""Compression pipeline — orchestrates layers in sequence.

The pipeline is the heart of tokencrunch. It:
1. Takes an API request
2. Runs it through each enabled layer in order
3. Collects per-layer metrics
4. Returns the compressed request

The layer order is fixed by design (see ADR-002):
  Syntactic → Serialization → Dedup → Semantic → Cache

This order maximizes compound savings: syntactic normalization makes
dedup more effective, and both reduce the work for semantic compression.
"""

from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field

from tokencrunch.layers import CompressionLayer, LayerStats


@dataclass
class PipelineResult:
    """Result of running the compression pipeline on a request."""

    messages: list[dict]
    total_stats: PipelineStats
    per_layer: dict[str, LayerStats]
    cache_hit: bool = False


@dataclass
class PipelineStats:
    """Aggregate stats across all layers."""

    original_bytes: int = 0
    compressed_bytes: int = 0
    total_time_ms: float = 0.0

    @property
    def savings_ratio(self) -> float:
        if self.original_bytes == 0:
            return 0.0
        return 1.0 - (self.compressed_bytes / self.original_bytes)

    @property
    def savings_pct(self) -> str:
        return f"{self.savings_ratio * 100:.1f}%"


class Pipeline:
    """Sequential compression pipeline.

    Usage:
        pipeline = Pipeline(layers=[syntactic, serialize, dedup])
        result = pipeline.compress(messages)
        # result.messages → compressed messages to send to API
        # result.total_stats → aggregate metrics
    """

    def __init__(self, layers: list[CompressionLayer] | None = None):
        self._layers = layers or []

    def add_layer(self, layer: CompressionLayer) -> None:
        """Append a layer to the end of the pipeline."""
        self._layers.append(layer)

    @property
    def active_layers(self) -> list[CompressionLayer]:
        """Only layers that are currently enabled."""
        return [layer for layer in self._layers if layer.enabled]

    def compress(self, messages: list[dict]) -> PipelineResult:
        """Run all active layers on the messages.

        Creates a deep copy of messages to avoid mutating the original.
        Each layer receives the output of the previous layer.
        """
        # Deep copy so layers can safely transform without side effects
        current = copy.deepcopy(messages)
        original_size = _estimate_size(current)

        per_layer: dict[str, LayerStats] = {}
        total_time = 0.0

        for layer in self.active_layers:
            layer.reset_stats()

            start = time.perf_counter()
            current = layer.compress_messages(current)
            elapsed_ms = (time.perf_counter() - start) * 1000

            stats = layer.get_stats()
            stats.processing_time_ms = elapsed_ms
            per_layer[layer.name] = stats
            total_time += elapsed_ms

        compressed_size = _estimate_size(current)

        return PipelineResult(
            messages=current,
            total_stats=PipelineStats(
                original_bytes=original_size,
                compressed_bytes=compressed_size,
                total_time_ms=total_time,
            ),
            per_layer=per_layer,
        )


def _estimate_size(messages: list[dict]) -> int:
    """Rough byte size estimation for metrics.

    This is NOT exact token counting — it's a fast approximation for
    showing relative savings. For exact counts, use Anthropic's
    count_tokens endpoint.
    """
    return len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
