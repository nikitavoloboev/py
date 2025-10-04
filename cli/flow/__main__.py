"""Run the flow CLI with ``python -m cli.flow``."""

from __future__ import annotations

from .cli import main


def entrypoint() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(entrypoint())
