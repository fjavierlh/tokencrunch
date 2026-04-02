"""Configuration loading and validation.

tokencrunch uses a TOML config file. This module defines the schema with
pydantic so we get clear error messages if the config is invalid.

The config is loaded from (in priority order):
1. Path passed via --config CLI flag
2. ./tokencrunch.toml in the current directory
3. ~/.config/tokencrunch/config.toml
4. Built-in defaults (everything enabled except semantic layer)
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class LayersConfig(BaseModel):
    """Which compression layers are active."""

    syntactic: bool = True
    serialization: bool = True
    dedup: bool = True
    semantic: bool = False  # Off by default: requires model download
    cache: bool = True


class SemanticConfig(BaseModel):
    """Settings for the LLMLingua-2 semantic compression layer."""

    rate: float = Field(default=0.5, ge=0.1, le=0.9)
    model: str = "microsoft/llmlingua-2-xlm-roberta-large-meetingbank"


class ProxyConfig(BaseModel):
    """HTTP proxy settings."""

    port: int = Field(default=7420, ge=1024, le=65535)
    upstream: str = "https://api.anthropic.com"
    log_savings: bool = True


class Config(BaseModel):
    """Root configuration for tokencrunch."""

    layers: LayersConfig = LayersConfig()
    semantic: SemanticConfig = SemanticConfig()
    proxy: ProxyConfig = ProxyConfig()


# Paths searched in order
_SEARCH_PATHS = [
    Path("tokencrunch.toml"),
    Path.home() / ".config" / "tokencrunch" / "config.toml",
]


def load_config(path: Path | None = None) -> Config:
    """Load config from a TOML file, falling back to defaults.

    Args:
        path: Explicit path to a config file. If None, searches default locations.

    Returns:
        Validated Config instance.
    """
    if path and path.exists():
        return _parse(path)

    for search_path in _SEARCH_PATHS:
        if search_path.exists():
            return _parse(search_path)

    # No config file found — use defaults
    return Config()


def _parse(path: Path) -> Config:
    """Parse and validate a TOML config file."""
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    return Config.model_validate(raw)
