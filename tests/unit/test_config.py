"""Unit tests for configuration loading and validation."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tokencrunch.config import Config, LayersConfig, ProxyConfig, SemanticConfig, load_config


class TestDefaults:
    def test_layers_defaults(self):
        cfg = Config()
        assert cfg.layers.syntactic is True
        assert cfg.layers.serialization is True
        assert cfg.layers.dedup is True
        assert cfg.layers.semantic is False  # off by default
        assert cfg.layers.cache is True

    def test_proxy_defaults(self):
        cfg = Config()
        assert cfg.proxy.port == 7420
        assert cfg.proxy.upstream == "https://api.anthropic.com"
        assert cfg.proxy.log_savings is True

    def test_semantic_defaults(self):
        cfg = Config()
        assert cfg.semantic.rate == pytest.approx(0.5)
        assert "llmlingua" in cfg.semantic.model.lower()


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path):
        cfg = load_config(tmp_path / "nonexistent.toml")
        assert isinstance(cfg, Config)
        assert cfg.proxy.port == 7420

    def test_loads_valid_toml(self, tmp_path):
        toml_file = tmp_path / "tokencrunch.toml"
        toml_file.write_text(textwrap.dedent("""\
            [proxy]
            port = 8080
            log_savings = false

            [layers]
            syntactic = true
            semantic = false
        """))
        cfg = load_config(toml_file)
        assert cfg.proxy.port == 8080
        assert cfg.proxy.log_savings is False

    def test_partial_toml_uses_defaults_for_missing_keys(self, tmp_path):
        toml_file = tmp_path / "tokencrunch.toml"
        toml_file.write_text("[proxy]\nport = 9000\n")
        cfg = load_config(toml_file)
        assert cfg.proxy.port == 9000
        assert cfg.proxy.upstream == "https://api.anthropic.com"

    def test_returns_defaults_when_path_is_none(self, monkeypatch, tmp_path):
        # Ensure no config files exist in search paths
        monkeypatch.chdir(tmp_path)
        cfg = load_config(None)
        assert isinstance(cfg, Config)


class TestValidation:
    def test_invalid_port_too_low(self):
        with pytest.raises(Exception):
            Config(proxy=ProxyConfig(port=80))

    def test_invalid_port_too_high(self):
        with pytest.raises(Exception):
            Config(proxy=ProxyConfig(port=99999))

    def test_semantic_rate_below_minimum(self):
        with pytest.raises(Exception):
            Config(semantic=SemanticConfig(rate=0.05))

    def test_semantic_rate_above_maximum(self):
        with pytest.raises(Exception):
            Config(semantic=SemanticConfig(rate=0.95))

    def test_valid_boundary_rates(self):
        cfg_low = Config(semantic=SemanticConfig(rate=0.1))
        cfg_high = Config(semantic=SemanticConfig(rate=0.9))
        assert cfg_low.semantic.rate == pytest.approx(0.1)
        assert cfg_high.semantic.rate == pytest.approx(0.9)
