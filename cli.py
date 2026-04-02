"""Command-line interface for tokencrunch.

Usage:
    tokencrunch start              # Start the proxy with defaults
    tokencrunch start --port 8080  # Custom port
    tokencrunch start --config my.toml
    tokencrunch info               # Show active config and layers
"""

from __future__ import annotations

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from tokencrunch import __version__
from tokencrunch.config import Config, load_config
from tokencrunch.layers.syntactic import SyntacticLayer
from tokencrunch.pipeline import Pipeline
from tokencrunch.proxy import create_app

console = Console()


def _setup_logging() -> None:
    """Configure logging with a clean format for terminal output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )


def _build_pipeline(config: Config) -> Pipeline:
    """Build the compression pipeline from config.

    Each layer is instantiated and added in the correct order.
    Layers that are disabled in config are still added (for metrics)
    but their `enabled` flag is False so the pipeline skips them.
    """
    pipeline = Pipeline()

    # Layer 1: Syntactic (lossless)
    pipeline.add_layer(SyntacticLayer(enabled=config.layers.syntactic))

    # Layers 2-5 are stubs for now — will be implemented in Phase 2
    # pipeline.add_layer(SerializationLayer(enabled=config.layers.serialization))
    # pipeline.add_layer(DedupLayer(enabled=config.layers.dedup))
    # pipeline.add_layer(SemanticLayer(enabled=config.layers.semantic, ...))
    # pipeline.add_layer(CacheLayer(enabled=config.layers.cache))

    return pipeline


@click.group()
@click.version_option(version=__version__)
def main():
    """tokencrunch — Multi-layer token compression proxy for AI coding assistants."""
    pass


@main.command()
@click.option("--port", "-p", type=int, help="Port to listen on (default: from config)")
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), help="Config file path")
def start(port: int | None, config_path: str | None):
    """Start the compression proxy."""
    import uvicorn

    _setup_logging()

    # Load config
    path = Path(config_path) if config_path else None
    config = load_config(path)

    # Override port if provided via CLI
    if port:
        config.proxy.port = port

    # Build pipeline
    pipeline = _build_pipeline(config)

    # Show startup banner
    _print_banner(config, pipeline)

    # Create and run the app
    app = create_app(config, pipeline)
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=config.proxy.port,
        log_level="warning",  # We handle our own logging
    )


@main.command()
@click.option("--config", "-c", "config_path", type=click.Path(exists=True), help="Config file path")
def info(config_path: str | None):
    """Show current configuration and active layers."""
    path = Path(config_path) if config_path else None
    config = load_config(path)
    pipeline = _build_pipeline(config)
    _print_banner(config, pipeline)


def _print_banner(config: Config, pipeline: Pipeline) -> None:
    """Print a nice startup banner showing active layers."""
    console.print()
    console.print(f"[bold cyan]🗜️  tokencrunch v{__version__}[/]")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Layer", style="white")
    table.add_column("Status", justify="center")
    table.add_column("Type", style="dim")

    layer_info = [
        ("syntactic", config.layers.syntactic, "lossless"),
        ("serialization", config.layers.serialization, "lossless"),
        ("dedup", config.layers.dedup, "lossless"),
        ("semantic", config.layers.semantic, "lossy"),
        ("cache", config.layers.cache, "cache"),
    ]

    for name, enabled, layer_type in layer_info:
        status = "[green]● ON[/]" if enabled else "[dim]○ OFF[/]"
        table.add_row(name, status, layer_type)

    console.print(table)
    console.print()
    console.print(f"  Proxy:    [bold]http://127.0.0.1:{config.proxy.port}[/]")
    console.print(f"  Upstream: {config.proxy.upstream}")
    console.print()
    console.print("[dim]  Set ANTHROPIC_BASE_URL=http://127.0.0.1:"
                  f"{config.proxy.port} in your coding assistant[/]")
    console.print()


if __name__ == "__main__":
    main()
