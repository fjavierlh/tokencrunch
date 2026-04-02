"""Shared fixtures for all test levels."""

from __future__ import annotations

import pytest

from tokencrunch.config import Config, LayersConfig, ProxyConfig
from tokencrunch.layers.syntactic import SyntacticLayer
from tokencrunch.pipeline import Pipeline
from tokencrunch.proxy import create_app


@pytest.fixture
def syntactic_layer() -> SyntacticLayer:
    return SyntacticLayer(enabled=True)


@pytest.fixture
def pipeline_with_syntactic(syntactic_layer: SyntacticLayer) -> Pipeline:
    p = Pipeline()
    p.add_layer(syntactic_layer)
    return p


@pytest.fixture
def config() -> Config:
    """Default config with syntactic layer enabled, upstream pointing to a test URL."""
    cfg = Config()
    cfg.proxy = ProxyConfig(port=7420, upstream="http://mock-upstream", log_savings=False)
    return cfg


@pytest.fixture
def app(config, pipeline_with_syntactic):
    return create_app(config, pipeline_with_syntactic)


@pytest.fixture
def noisy_messages() -> list[dict]:
    """Messages with redundant whitespace, blank lines and tabs."""
    return [
        {
            "role": "user",
            "content": "Please review this:\n\n\n\ndef foo():\n\treturn 1   \n\n\n",
        },
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Sure!   \n\n\n\nLooks good.   "},
                {"type": "image", "source": {"type": "base64", "data": "abc123"}},
            ],
        },
    ]
