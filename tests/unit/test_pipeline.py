"""Unit tests for Pipeline — uses mock layers to test orchestration logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from tokencrunch.layers import LayerStats
from tokencrunch.pipeline import Pipeline, PipelineStats


# ---------------------------------------------------------------------------
# Mock layer helper
# ---------------------------------------------------------------------------

class MockLayer:
    """Minimal CompressionLayer implementation for testing."""

    def __init__(self, name: str, enabled: bool = True, transform=None):
        self.name = name
        self.enabled = enabled
        self._transform = transform or (lambda msgs: msgs)
        self._stats = LayerStats()
        self.call_count = 0

    def compress_messages(self, messages: list[dict]) -> list[dict]:
        self.call_count += 1
        result = self._transform(messages)
        # Simulate some savings
        self._stats.chars_in += 100
        self._stats.chars_out += 80
        return result

    def reset_stats(self) -> None:
        self._stats = LayerStats()

    def get_stats(self) -> LayerStats:
        return self._stats


# ---------------------------------------------------------------------------
# Pipeline construction
# ---------------------------------------------------------------------------

class TestPipelineConstruction:
    def test_empty_pipeline(self):
        p = Pipeline()
        assert p.active_layers == []

    def test_add_layer(self):
        p = Pipeline()
        layer = MockLayer("a")
        p.add_layer(layer)
        assert len(p.active_layers) == 1

    def test_disabled_layer_not_in_active(self):
        p = Pipeline()
        p.add_layer(MockLayer("a", enabled=False))
        assert p.active_layers == []

    def test_mixed_layers_only_enabled_active(self):
        p = Pipeline()
        p.add_layer(MockLayer("a", enabled=True))
        p.add_layer(MockLayer("b", enabled=False))
        p.add_layer(MockLayer("c", enabled=True))
        assert len(p.active_layers) == 2

    def test_init_with_layer_list(self):
        layers = [MockLayer("a"), MockLayer("b")]
        p = Pipeline(layers=layers)
        assert len(p.active_layers) == 2


# ---------------------------------------------------------------------------
# Compression behavior
# ---------------------------------------------------------------------------

class TestPipelineCompress:
    def test_empty_pipeline_returns_messages_unchanged(self):
        p = Pipeline()
        messages = [{"role": "user", "content": "hello"}]
        result = p.compress(messages)
        assert result.messages == messages

    def test_disabled_layer_skipped(self):
        layer = MockLayer("a", enabled=False)
        p = Pipeline()
        p.add_layer(layer)
        p.compress([{"role": "user", "content": "hi"}])
        assert layer.call_count == 0

    def test_enabled_layer_called(self):
        layer = MockLayer("a", enabled=True)
        p = Pipeline()
        p.add_layer(layer)
        p.compress([{"role": "user", "content": "hi"}])
        assert layer.call_count == 1

    def test_layers_execute_in_order(self):
        call_order = []
        def make_transform(name):
            def transform(msgs):
                call_order.append(name)
                return msgs
            return transform

        p = Pipeline()
        p.add_layer(MockLayer("first", transform=make_transform("first")))
        p.add_layer(MockLayer("second", transform=make_transform("second")))
        p.add_layer(MockLayer("third", transform=make_transform("third")))
        p.compress([{"role": "user", "content": "hi"}])
        assert call_order == ["first", "second", "third"]

    def test_each_layer_receives_previous_output(self):
        def append_a(msgs):
            return [{**m, "content": m["content"] + "A"} for m in msgs]

        def append_b(msgs):
            return [{**m, "content": m["content"] + "B"} for m in msgs]

        p = Pipeline()
        p.add_layer(MockLayer("a", transform=append_a))
        p.add_layer(MockLayer("b", transform=append_b))
        result = p.compress([{"role": "user", "content": "X"}])
        assert result.messages[0]["content"] == "XAB"

    def test_original_messages_not_mutated(self):
        original = [{"role": "user", "content": "hello"}]
        snapshot = [{"role": "user", "content": "hello"}]

        def mutate(msgs):
            msgs[0]["content"] = "MUTATED"
            return msgs

        p = Pipeline()
        p.add_layer(MockLayer("m", transform=mutate))
        p.compress(original)
        assert original == snapshot


# ---------------------------------------------------------------------------
# Stats collection
# ---------------------------------------------------------------------------

class TestPipelineStats:
    def test_per_layer_stats_present(self):
        p = Pipeline()
        p.add_layer(MockLayer("a"))
        p.add_layer(MockLayer("b"))
        result = p.compress([{"role": "user", "content": "hi"}])
        assert "a" in result.per_layer
        assert "b" in result.per_layer

    def test_per_layer_stats_not_present_for_disabled(self):
        p = Pipeline()
        p.add_layer(MockLayer("a", enabled=False))
        result = p.compress([{"role": "user", "content": "hi"}])
        assert "a" not in result.per_layer

    def test_processing_time_set(self):
        p = Pipeline()
        p.add_layer(MockLayer("a"))
        result = p.compress([{"role": "user", "content": "hi"}])
        assert result.per_layer["a"].processing_time_ms >= 0

    def test_total_stats_bytes(self):
        p = Pipeline()
        result = p.compress([{"role": "user", "content": "hello"}])
        assert result.total_stats.original_bytes > 0
        assert result.total_stats.compressed_bytes > 0

    def test_layer_stats_reset_before_each_compress(self):
        layer = MockLayer("a")
        p = Pipeline()
        p.add_layer(layer)
        p.compress([{"role": "user", "content": "hi"}])
        first_chars_in = p.compress([{"role": "user", "content": "hi"}]).per_layer["a"].chars_in
        # After reset, stats reflect only the latest call
        assert first_chars_in == 100  # MockLayer always adds 100


# ---------------------------------------------------------------------------
# PipelineStats helpers
# ---------------------------------------------------------------------------

class TestPipelineStatsHelpers:
    def test_savings_ratio_zero_on_empty(self):
        stats = PipelineStats()
        assert stats.savings_ratio == 0.0

    def test_savings_ratio(self):
        stats = PipelineStats(original_bytes=200, compressed_bytes=150)
        assert stats.savings_ratio == pytest.approx(0.25)

    def test_savings_pct_format(self):
        stats = PipelineStats(original_bytes=200, compressed_bytes=150)
        assert stats.savings_pct == "25.0%"
