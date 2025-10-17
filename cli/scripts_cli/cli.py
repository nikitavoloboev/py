"""Discover and run project scripts with fuzzy selection."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from unicodedata import normalize

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT / "scripts"


@dataclass(frozen=True)
class ScriptEntry:
    name: str
    path: Path

    @property
    def display(self) -> str:
        return f"{self.name}  ({self.path.relative_to(ROOT)})"


def iter_scripts() -> list[ScriptEntry]:
    entries: list[ScriptEntry] = []
    if not SCRIPTS_DIR.exists():
        return entries

    for path in sorted(SCRIPTS_DIR.iterdir()):
        if path.name.startswith("_") or path.name == "__pycache__":
            continue
        if path.is_file() and path.suffix == ".py":
            entries.append(ScriptEntry(name=path.stem, path=path))
    return entries


def normalize_text(value: str) -> str:
    return normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def fuzzy_filter(query: str, entries: Iterable[ScriptEntry]) -> list[ScriptEntry]:
    if not query:
        return list(entries)

    pattern = ".*?".join(map(re.escape, normalize_text(query.lower())))
    matches: list[tuple[int, int, ScriptEntry]] = []
    for entry in entries:
        haystack = normalize_text(entry.name.lower())
        match = re.search(pattern, haystack)
        if match:
            score = match.end() - match.start()
            matches.append((score, match.start(), entry))

    matches.sort(key=lambda item: (item[0], item[1], item[2].name))
    return [entry for _, _, entry in matches]


def run_with_fzf(entries: list[ScriptEntry]) -> ScriptEntry | None:
    fzf_path = shutil.which("fzf")
    if not fzf_path:
        return None

    display = "\n".join(entry.display for entry in entries)
    result = subprocess.run(
        [fzf_path],
        input=display,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None

    selected_display = result.stdout.strip()
    selected = next(
        (entry for entry in entries if entry.display == selected_display),
        None,
    )
    return selected


def prompt_manual_selection(entries: list[ScriptEntry]) -> ScriptEntry | None:
    remaining = entries
    while True:
        if not remaining:
            print("No scripts matched. Try again.", file=sys.stderr)
        else:
            for index, entry in enumerate(remaining[:10], start=1):
                print(f"{index}. {entry.display}")

        try:
            query = input(
                "Enter number to run, or type search query (Ctrl+C to cancel): "
            ).strip()
        except KeyboardInterrupt:
            print("", file=sys.stderr)
            return None

        if query.isdigit() and remaining:
            choice = int(query)
            if 1 <= choice <= min(10, len(remaining)):
                return remaining[choice - 1]
            print("Invalid selection. Try again.", file=sys.stderr)
            continue

        remaining = fuzzy_filter(query, entries)


def execute_script(script: ScriptEntry, args: Sequence[str]) -> int:
    from shlex import quote

    cmd = [sys.executable, str(script.path), *args]
    env = os.environ.copy()
    rel_path = script.path.relative_to(ROOT)
    arg_display = " ".join(quote(str(arg)) for arg in args)
    message = f"→ Running {rel_path}"
    if arg_display:
        message = f"{message} {arg_display}"
    print(message)
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    return result.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="py-scripts",
        description="Fuzzy pick and run Python scripts from the scripts/ directory.",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Optional search terms to pre-filter scripts. Remaining args after '--' are passed to the script.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available scripts and exit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]

    if "--" in argv:
        idx = argv.index("--")
        cli_args = argv[:idx]
        script_args = tuple(argv[idx + 1 :])
    else:
        cli_args = argv
        script_args = tuple()

    args = parser.parse_args(cli_args)
    entries = iter_scripts()
    if not entries:
        parser.error("No scripts found in the scripts/ directory.")

    if args.list:
        for entry in entries:
            print(entry.display)
        return 0

    pre_query = " ".join(args.query).strip()
    selection: ScriptEntry | None = None
    filtered = fuzzy_filter(pre_query, entries) if pre_query else entries

    if len(filtered) == 1 and pre_query:
        selection = filtered[0]
    else:
        selection = run_with_fzf(filtered)
        if selection is None:
            selection = prompt_manual_selection(filtered)

    if selection is None:
        print("No script selected.", file=sys.stderr)
        return 1

    return execute_script(selection, script_args)


def entrypoint() -> int:
    return main()
