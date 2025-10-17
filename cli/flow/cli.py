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
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
from unicodedata import normalize

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

    raw_args = list(argv) if argv is not None else sys.argv[1:]
    if (
        not raw_args
        and sys.stdin.isatty()
        and sys.stdout.isatty()
        and sys.stderr.isatty()
    ):
        new_args, exit_code = _interactive_select_args()
        if new_args is None:
            return exit_code or 0
        raw_args = new_args

    args = parser.parse_args(raw_args)
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


def _command_entries() -> list[CommandSpec]:
    return sorted(_COMMANDS, key=lambda spec: spec.name.lower())


def _interactive_select_args() -> tuple[list[str] | None, int | None]:
    entries = _command_entries()
    if not entries:
        print("No commands are registered.", file=sys.stderr)
        return None, 1

    selected, exit_code = _run_with_fzf(entries)
    if selected is not None:
        return [selected.name], exit_code or 0
    if exit_code not in (None, 0):
        return None, exit_code

    selected, cancelled = _prompt_manual_selection(entries)
    if selected is None:
        return None, 130 if cancelled else 0
    return [selected.name], 0


def _run_with_fzf(entries: Sequence[CommandSpec]) -> tuple[CommandSpec | None, int | None]:
    fzf_path = shutil.which("fzf")
    if not fzf_path:
        return None, None

    lines = []
    by_name: dict[str, CommandSpec] = {}
    for spec in entries:
        display = f"{spec.name}\t{spec.help}"
        lines.append(display)
        by_name[spec.name] = spec

    result = subprocess.run(
        [
            fzf_path,
            "--height=40%",
            "--layout=reverse-list",
            "--border=rounded",
            "--prompt",
            "flow> ",
            "--info=inline",
            "--no-multi",
            "--with-nth=1,2",
            "--delimiter",
            "\t",
            "--header",
            "Select a flow command (Enter to run, ESC to cancel)",
        ],
        input="\n".join(lines),
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        return None, result.returncode

    selected_line = result.stdout.strip()
    if not selected_line:
        return None, 0

    name = selected_line.split("\t", 1)[0].strip()
    spec = by_name.get(name)
    return spec, 0 if spec else 1


def _prompt_manual_selection(
    entries: Sequence[CommandSpec],
) -> tuple[CommandSpec | None, bool]:
    entries = list(entries)
    filtered = entries

    while True:
        if not filtered:
            print("No commands matched. Try again.", file=sys.stderr)
        else:
            for index, spec in enumerate(filtered[:10], start=1):
                print(f"{index}. {spec.name:<20} {spec.help}")

        try:
            raw = input(
                "Enter number to run, type to filter, or press Ctrl+C to cancel: "
            ).strip()
        except KeyboardInterrupt:
            print("", file=sys.stderr)
            return None, True

        if not raw:
            if len(filtered) == 1:
                return filtered[0], False
            continue

        if raw.isdigit() and filtered:
            choice = int(raw)
            if 1 <= choice <= min(10, len(filtered)):
                return filtered[choice - 1], False
            print("Invalid selection. Try again.", file=sys.stderr)
            continue

        for spec in entries:
            if spec.name == raw:
                return spec, False

        filtered = _fuzzy_filter(raw, entries)


def _normalize_text(value: str) -> str:
    return normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _fuzzy_filter(query: str, entries: Iterable[CommandSpec]) -> list[CommandSpec]:
    if not query:
        return list(entries)

    normalized_query = _normalize_text(query.lower())
    pattern = ".*?".join(map(re.escape, normalized_query))

    matches: list[tuple[int, int, CommandSpec]] = []
    for spec in entries:
        best: tuple[int, int] | None = None
        for candidate in (spec.name, spec.help):
            haystack = _normalize_text(candidate.lower())
            match = re.search(pattern, haystack)
            if match:
                score = match.end() - match.start()
                start = match.start()
                if best is None or (score, start) < best:
                    best = (score, start)
        if best is not None:
            matches.append((*best, spec))

    matches.sort(key=lambda item: (item[0], item[1], item[2].name))
    return [spec for _, _, spec in matches]
