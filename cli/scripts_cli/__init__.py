"""Utility CLI to run scripts from the ``scripts`` directory."""

from __future__ import annotations

__all__ = ["main", "entrypoint"]

from .cli import entrypoint, main  # noqa: E402,WPS347 (re-export for package API)
