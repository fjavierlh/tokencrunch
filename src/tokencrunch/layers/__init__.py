"""CompressionLayer protocol and LayerStats used across all layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class LayerStats:
    """Metrics produced by a single compression layer."""

    chars_in: int = 0
    chars_out: int = 0
    processing_time_ms: float = 0.0

    @property
    def savings_ratio(self) -> float:
        """Fraction of characters removed (0.0 = no savings, 1.0 = all removed)."""
        if self.chars_in == 0:
            return 0.0
        return 1.0 - (self.chars_out / self.chars_in)


@runtime_checkable
class CompressionLayer(Protocol):
    """Protocol every compression layer must implement.

    Layers are stateful (they accumulate stats between compress_messages calls)
    and must be reset between requests via reset_stats().
    """

    name: str
    enabled: bool

    def compress_messages(self, messages: list[dict]) -> list[dict]:
        """Compress the messages list and return the result."""
        ...

    def reset_stats(self) -> None:
        """Reset accumulated stats to zero."""
        ...

    def get_stats(self) -> LayerStats:
        """Return stats accumulated since the last reset_stats() call."""
        ...
