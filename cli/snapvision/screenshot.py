from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

import mss
import numpy as np
from PIL import Image

from .config import ScreenshotConfig


@dataclass(slots=True)
class ScreenshotResult:
    pixels: np.ndarray
    path: Path
    captured_at: float
    monitor_index: int


class ScreenshotTaker:
    """Capture the desktop using mss and persist the image to disk."""

    def __init__(self, config: ScreenshotConfig) -> None:
        self._config = config

    def capture(self) -> ScreenshotResult:
        with mss.mss() as sct:
            monitors = sct.monitors
            if not monitors:
                raise RuntimeError("No monitors detected for screenshot capture.")
            monitor_index = self._resolve_monitor_index(monitors)
            monitor = monitors[monitor_index]
            # mss does not expose cursor capture; setting include_cursor documents intent.
            raw = sct.grab(monitor)

        pixels = np.array(raw, dtype=np.uint8)
        pixels = pixels[:, :, :3]
        pixels = pixels[:, :, ::-1]

        path = self._prepare_output_path()
        image = Image.fromarray(pixels)
        image.save(path)

        return ScreenshotResult(
            pixels=pixels,
            path=path,
            captured_at=time.time(),
            monitor_index=monitor_index,
        )

    def _resolve_monitor_index(self, monitors: list[dict[str, int]]) -> int:
        requested = self._config.monitor
        if requested is None:
            return 0
        if requested < 0 or requested >= len(monitors):
            raise ValueError(f"Monitor index {requested} is out of range (found {len(monitors) - 1}).")
        return requested

    def _prepare_output_path(self) -> Path:
        configured = self._config.output_path
        if configured is None:
            default_dir = Path.home() / "tmp"
            default_dir.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(prefix="snapvision-", suffix=".png", dir=default_dir, delete=False) as tmp:
                return Path(tmp.name)
        path = configured.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
