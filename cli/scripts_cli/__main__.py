"""Run the scripts CLI with ``python -m cli.scripts_cli``."""

from __future__ import annotations

from .cli import entrypoint


if __name__ == "__main__":
    raise SystemExit(entrypoint())
