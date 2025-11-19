from __future__ import annotations

from dataclasses import dataclass

from .backends import InferenceResult, VisionBackend
from .screenshot import ScreenshotResult, ScreenshotTaker


@dataclass(slots=True)
class RunSummary:
    screenshot: ScreenshotResult
    inference: InferenceResult

    def to_dict(self) -> dict[str, object]:
        return {
            "screenshot": {
                "path": str(self.screenshot.path),
                "captured_at": self.screenshot.captured_at,
                "monitor_index": self.screenshot.monitor_index,
            },
            "inference": self.inference.to_dict(),
        }


class CaptureAndInferService:
    def __init__(self, screenshotter: ScreenshotTaker, backend: VisionBackend) -> None:
        self._screenshotter = screenshotter
        self._backend = backend

    def run(self, *, prompt: str | None = None) -> RunSummary:
        screenshot = self._screenshotter.capture()
        inference = self._backend.predict(screenshot.pixels, prompt=prompt)
        return RunSummary(screenshot=screenshot, inference=inference)
