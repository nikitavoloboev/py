"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["Settings", "settings"]


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Static metadata and environment-aware flags."""

    app_name: str = os.getenv("APP_NAME", "py API")
    environment: str = os.getenv("APP_ENV", "development")
    version: str = os.getenv("APP_VERSION", "0.1.0")
    debug: bool = _truthy(os.getenv("APP_DEBUG"))


settings = Settings()
