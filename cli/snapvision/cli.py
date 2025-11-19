from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .backends import MlxBackend, MlxVlmBackend, RustAcceleratedBackend, VisionBackend
from .config import BackendConfig, RunConfig, ScreenshotConfig
from .screenshot import ScreenshotTaker
from .service import CaptureAndInferService, RunSummary

console = Console(highlight=False)
app = typer.Typer(help="Capture a screenshot and run lightweight vision inference.")


def entrypoint() -> None:
    app()


@app.command()
def capture(
    monitor: Annotated[int | None, typer.Option(help="Monitor index (0 = all displays).")] = None,
    include_cursor: Annotated[bool, typer.Option(help="Attempt to include cursor if the platform supports it.")] = False,
    output: Annotated[Path | None, typer.Option(help="Save screenshot PNG to this path.")] = None,
    backend: Annotated[
        str, typer.Option("--backend", case_sensitive=False, help="Select the inference backend.")
    ] = "mlx",
    model_path: Annotated[
        Path | None, typer.Option(help="Path or Hugging Face repo for MLX/MLX-VLM backends.")
    ] = None,
    rust_lib: Annotated[Path | None, typer.Option(help="Path to the Rust dynamic library for acceleration.")] = None,
    prompt: Annotated[str | None, typer.Option(help="Optional natural-language hint passed to the backend.")] = None,
    adapter_path: Annotated[
        Path | None, typer.Option(help="Optional LoRA adapter path for the mlx-vlm backend.")
    ] = None,
    revision: Annotated[str | None, typer.Option(help="Specific revision when downloading mlx-vlm models.")] = None,
    max_tokens: Annotated[
        int, typer.Option("--max-tokens", help="Maximum tokens to generate (mlx-vlm backend).", min=1)
    ] = 128,
    temperature: Annotated[
        float, typer.Option("--temperature", help="Sampling temperature (mlx-vlm backend).", min=0.0)
    ] = 0.1,
    force_download: Annotated[
        bool, typer.Option(help="Force re-download of the specified mlx-vlm model.")
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON only.")] = False,
) -> None:
    backend_choice = backend.lower()
    if backend_choice not in ("mlx", "rust", "mlx-vlm"):
        raise typer.BadParameter("Backend must be 'mlx', 'mlx-vlm', or 'rust'.")
    screenshot_cfg = ScreenshotConfig(
        monitor=monitor,
        include_cursor=include_cursor,
        output_path=output,
    )
    backend_cfg = BackendConfig(
        backend=backend_choice,  # type: ignore[arg-type]
        model_path=model_path,
        rust_library=rust_lib,
        prompt=prompt,
        adapter_path=adapter_path,
        revision=revision,
        max_tokens=max_tokens,
        temperature=temperature,
        force_download=force_download,
    )
    run_cfg = RunConfig(screenshot=screenshot_cfg, backend=backend_cfg, json_output=json_output)
    _run_cli(run_cfg)


def _run_cli(config: RunConfig) -> None:
    screenshotter = ScreenshotTaker(config.screenshot)
    backend = _build_backend(config.backend)
    service = CaptureAndInferService(screenshotter, backend)
    summary = service.run(prompt=config.backend.prompt)
    if config.json_output:
        typer.echo(json.dumps(summary.to_dict(), indent=2))
        return
    _print_human_readable(summary)


def _build_backend(config: BackendConfig) -> VisionBackend:
    if config.backend == "mlx":
        return MlxBackend(model_path=config.model_path)
    if config.backend == "mlx-vlm":
        if config.model_path is None:
            raise typer.BadParameter("--model-path is required when backend='mlx-vlm'.")
        return MlxVlmBackend(
            model_id=str(config.model_path),
            adapter_path=config.adapter_path,
            revision=config.revision,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            force_download=config.force_download,
        )
    if config.backend == "rust":
        if config.rust_library is None:
            raise typer.BadParameter("--rust-lib is required when backend='rust'.")
        return RustAcceleratedBackend(config.rust_library)
    raise typer.BadParameter(f"Unsupported backend '{config.backend}'.")


def _print_human_readable(summary: RunSummary) -> None:
    table = Table(title="SnapVision run", show_edge=False, box=None)
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", overflow="fold")
    table.add_row("Screenshot", str(summary.screenshot.path))
    table.add_row("Monitor", str(summary.screenshot.monitor_index))
    table.add_row("Backend", summary.inference.backend)
    table.add_row("Predictions", "\n".join(summary.inference.predictions))
    table.add_row("Latency (ms)", f"{summary.inference.latency_ms:.2f}")
    metadata = summary.inference.metadata
    if metadata:
        table.add_row("Metadata", json.dumps(metadata, indent=2))
    console.print(table)
