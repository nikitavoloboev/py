"""Flow CLI command dispatcher.

Add new commands by applying the ``@command`` decorator to a function that
accepts the parsed ``argparse.Namespace``. Optionally pass a ``configure``
callable to add arguments to that command's parser.

Example::

    @command(
        "ping",
        help="Ping something",
        configure=lambda parser: parser.add_argument("target"),
    )
    def ping(args: argparse.Namespace) -> int:
        print(f"Pinging {args.target}...")
        return 0

Run with ``python -m cli.flow ping example`` or, after installing, ``flow ping example``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Callable, List, Sequence

CommandConfigure = Callable[[argparse.ArgumentParser], None]
CommandHandler = Callable[[argparse.Namespace], int | None]


@dataclass(frozen=True)
class CommandSpec:
    name: str
    help: str
    configure: CommandConfigure
    handler: CommandHandler


_COMMANDS: list[CommandSpec] = []


def command(
    name: str,
    *,
    help: str,
    configure: CommandConfigure | None = None,
) -> Callable[[CommandHandler], CommandHandler]:
    """Register a new subcommand.

    ``configure`` receives the sub-parser so additional arguments can be added.
    Raises ``ValueError`` when a duplicate name is registered.
    """

    def decorator(func: CommandHandler) -> CommandHandler:
        if any(spec.name == name for spec in _COMMANDS):
            msg = f"Command '{name}' already registered"
            raise ValueError(msg)

        spec = CommandSpec(
            name=name,
            help=help,
            configure=configure or (lambda parser: None),
            handler=func,
        )
        _COMMANDS.append(spec)
        return func

    return decorator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flow", description="A place to vibe new commands into."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for spec in _COMMANDS:
        subparser = subparsers.add_parser(spec.name, help=spec.help)
        spec.configure(subparser)
        subparser.set_defaults(_handler=spec.handler)

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = getattr(args, "_handler", None)

    if handler is None:
        parser.print_help()
        return 1

    result = handler(args)
    return int(result or 0)


@command(
    "hello",
    help="Say hello to someone.",
    configure=lambda parser: parser.add_argument(
        "name",
        nargs="?",
        default="world",
        help="Who to greet.",
    ),
)
def hello(args: argparse.Namespace) -> int:
    print(f"Hello, {args.name}!")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run(argv)
