from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


BackendName = Literal["mlx", "rust", "mlx-vlm"]


@dataclass(slots=True)
class ScreenshotConfig:
    monitor: int | None = None
    include_cursor: bool = False
    output_path: Path | None = None


@dataclass(slots=True)
class BackendConfig:
    backend: BackendName = "mlx"
    model_path: Path | None = None
    rust_library: Path | None = None
    prompt: str | None = None
    adapter_path: Path | None = None
    revision: str | None = None
    max_tokens: int = 128
    temperature: float = 0.1
    force_download: bool = False


@dataclass(slots=True)
class RunConfig:
    screenshot: ScreenshotConfig
    backend: BackendConfig
    json_output: bool = False
