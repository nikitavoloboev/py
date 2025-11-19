"""SnapVision CLI scaffolding.

The CLI captures a screenshot, funnels it through a configurable
vision backend (MLX by default), and reports structured results.
Rust acceleration can plug in later by swapping the backend factory.
"""

from __future__ import annotations

from .cli import app

__all__ = ["app"]
