from __future__ import annotations

import ctypes
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from PIL import Image

try:
    import mlx.core as mx
except Exception:  # pragma: no cover - optional dependency guard
    mx = None


@dataclass(slots=True)
class InferenceResult:
    backend: str
    prompt: str | None
    predictions: list[str]
    latency_ms: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "prompt": self.prompt,
            "predictions": self.predictions,
            "latency_ms": self.latency_ms,
            "metadata": self.metadata,
        }


class VisionBackend(Protocol):
    name: str

    def predict(self, image: np.ndarray, *, prompt: str | None = None) -> InferenceResult:  # pragma: no cover - runtime wiring
        ...


class MlxBackend:
    name = "mlx"

    def __init__(self, model_path: Path | None = None) -> None:
        if mx is None:  # pragma: no cover - import guard
            raise RuntimeError("MLX is not available. Ensure mlx is installed and importable.")
        self._model_path = model_path

    def predict(self, image: np.ndarray, *, prompt: str | None = None) -> InferenceResult:
        start = time.perf_counter()
        arr = mx.array(image, dtype=mx.float32) / 255.0
        summary = self._summarize(arr)
        latency_ms = (time.perf_counter() - start) * 1000
        description = self._describe(summary, prompt)
        metadata = {
            "pixel_mean": summary["mean"],
            "pixel_std": summary["std"],
            "shape": list(image.shape),
            "model_path": str(self._model_path) if self._model_path else None,
        }
        return InferenceResult(
            backend=self.name,
            prompt=prompt,
            predictions=[description],
            latency_ms=latency_ms,
            metadata=metadata,
        )

    def _summarize(self, arr: Any) -> dict[str, float]:
        mean = float(mx.mean(arr).item())
        std = float(mx.std(arr).item())
        brightness = max(0.0, min(1.0, mean))
        return {"mean": mean, "std": std, "brightness": brightness}

    def _describe(self, summary: dict[str, float], prompt: str | None) -> str:
        brightness = summary["brightness"]
        if brightness > 0.7:
            mood = "very bright"
        elif brightness > 0.4:
            mood = "well lit"
        else:
            mood = "dim"
        prompt_part = f" Prompt: {prompt}" if prompt else ""
        return f"Scene looks {mood} (mean pixel {summary['mean']:.3f}, std {summary['std']:.3f}).{prompt_part}"


class MlxVlmBackend:
    name = "mlx-vlm"

    def __init__(
        self,
        *,
        model_id: str,
        adapter_path: Path | None = None,
        revision: str | None = None,
        max_tokens: int = 128,
        temperature: float = 0.1,
        force_download: bool = False,
    ) -> None:
        if not model_id:
            raise ValueError("model_id is required for the mlx-vlm backend.")
        try:
            from mlx_vlm import load as load_model  # type: ignore[import-not-found]
            from mlx_vlm.generate import generate as generate_text  # type: ignore[import-not-found]
            from mlx_vlm.prompt_utils import apply_chat_template  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency guard
            raise RuntimeError(
                "mlx-vlm is required for backend 'mlx-vlm'. Install it with `uv pip install mlx-vlm`."
            ) from exc

        self._model_id = model_id
        self._adapter_path = adapter_path
        self._revision = revision
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._force_download = force_download
        self._load_model = load_model
        self._generate = generate_text
        self._apply_chat_template = apply_chat_template

        adapter = str(adapter_path) if adapter_path else None
        self._model, self._processor = self._load_model(
            model_id,
            adapter_path=adapter,
            revision=revision,
            trust_remote_code=True,
            force_download=force_download,
        )

    def predict(self, image: np.ndarray, *, prompt: str | None = None) -> InferenceResult:
        pil_image = Image.fromarray(image.astype(np.uint8))
        formatted_prompt = self._apply_chat_template(
            self._processor,
            self._model.config,
            prompt or "Describe what is happening in this screenshot.",
            num_images=1,
            num_audios=0,
        )
        start = time.perf_counter()
        result = self._generate(
            self._model,
            self._processor,
            formatted_prompt,
            image=[pil_image],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        description = result.text.strip() or "(no response)"
        metadata = {
            "model_id": self._model_id,
            "adapter_path": str(self._adapter_path) if self._adapter_path else None,
            "revision": self._revision,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "prompt_tokens": result.prompt_tokens,
            "generation_tokens": result.generation_tokens,
            "total_tokens": result.total_tokens,
            "prompt_tps": result.prompt_tps,
            "generation_tps": result.generation_tps,
            "peak_memory_gb": result.peak_memory,
            "force_download": self._force_download,
        }
        return InferenceResult(
            backend=self.name,
            prompt=prompt,
            predictions=[description],
            latency_ms=latency_ms,
            metadata=metadata,
        )


class RustAcceleratedBackend:
    name = "rust"

    def __init__(self, library_path: Path) -> None:
        self._library_path = library_path.expanduser().resolve()
        self._lib: ctypes.CDLL | None = None
        self._run_inference: Any | None = None

    def predict(self, image: np.ndarray, *, prompt: str | None = None) -> InferenceResult:
        if not self._library_path.exists():
            raise FileNotFoundError(f"Rust dynamic library {self._library_path} not found.")
        self._load()
        contiguous = np.ascontiguousarray(image, dtype=np.uint8)
        height, width, channels = contiguous.shape
        start = time.perf_counter()
        result_ptr = self._run_inference(  # type: ignore[misc]
            contiguous.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            ctypes.c_size_t(height),
            ctypes.c_size_t(width),
            ctypes.c_size_t(channels),
            ctypes.c_char_p(prompt.encode("utf-8") if prompt else None),
        )
        latency_ms = (time.perf_counter() - start) * 1000
        if not result_ptr:
            raise RuntimeError("Rust backend returned a null pointer.")
        message = ctypes.cast(result_ptr, ctypes.c_char_p).value
        if message is None:
            raise RuntimeError("Rust backend response decoding failed.")
        decoded = message.decode("utf-8")
        try:
            payload = json.loads(decoded)
            predictions = payload.get("predictions") or [payload.get("result", "(no result)")]
            metadata = {"library_path": str(self._library_path), "raw": payload}
        except json.JSONDecodeError:
            predictions = [decoded]
            metadata = {"library_path": str(self._library_path)}
        return InferenceResult(
            backend=self.name,
            prompt=prompt,
            predictions=[str(pred) for pred in predictions],
            latency_ms=latency_ms,
            metadata=metadata,
        )

    def _load(self) -> None:
        if self._lib is not None and self._run_inference is not None:
            return
        self._lib = ctypes.CDLL(str(self._library_path))
        func = getattr(self._lib, "run_inference", None)
        if func is None:
            raise AttributeError(
                "Rust library must export a 'run_inference' function with signature "
                "(uint8_t*, size_t, size_t, size_t, const char*) -> const char*."
            )
        func.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_size_t,
            ctypes.c_char_p,
        ]
        func.restype = ctypes.c_void_p
        self._run_inference = func
