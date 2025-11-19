"""Module entrypoint for ``python -m cli.snapvision``."""

from __future__ import annotations

from .cli import entrypoint


def main() -> None:
    entrypoint()


if __name__ == "__main__":
    main()
