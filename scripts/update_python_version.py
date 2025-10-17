#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_uv_python_list() -> list[dict[str, object]]:
    """Return the available Python downloads as JSON."""
    result = subprocess.run(
        ["uv", "python", "list", "--only-downloads", "--output-format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"Failed to parse uv output as JSON: {exc}") from exc


def choose_latest_cpython(downloads: list[dict[str, object]]) -> tuple[str, str]:
    """Pick the latest stable CPython download."""
    stable_re = re.compile(r"^\d+\.\d+\.\d+$")
    stable_releases = [
        entry
        for entry in downloads
        if entry.get("implementation") == "cpython"
        and entry.get("variant") == "default"
        and stable_re.match(str(entry.get("version", "")))
    ]
    if not stable_releases:
        raise SystemExit("No stable CPython releases found in uv output.")

    def version_key(entry: dict[str, object]) -> tuple[int, int, int]:
        parts = entry.get("version_parts")
        if not isinstance(parts, dict):
            raise SystemExit("uv output missing 'version_parts'.")
        try:
            return (
                int(parts["major"]),
                int(parts["minor"]),
                int(parts["patch"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit(f"Invalid version_parts in uv output: {parts}") from exc

    latest = max(stable_releases, key=version_key)
    parts = latest["version_parts"]  # type: ignore[index]
    major = int(parts["major"])  # type: ignore[index]
    minor = int(parts["minor"])  # type: ignore[index]
    python_spec = f"{major}.{minor}"
    full_version = str(latest["version"])
    return python_spec, full_version


def current_python_spec(taskfile: Path) -> str:
    text = taskfile.read_text()
    match = re.search(r'default "(\d+\.\d+)" \.PYTHON_SPEC', text)
    if not match:
        raise SystemExit("Could not find current Python spec in Taskfile.yml.")
    return match.group(1)


def replace_text(path: Path, pattern: str, replacement: str) -> bool:
    text = path.read_text()
    new_text, count = re.subn(pattern, replacement, text)
    if count == 0:
        raise SystemExit(f"Pattern not found in {path}")
    if text != new_text:
        path.write_text(new_text)
        return True
    return False


def update_files(python_spec: str) -> list[str]:
    updates: list[str] = []

    taskfile = ROOT / "Taskfile.yml"
    if replace_text(
        taskfile,
        r'default "\d+\.\d+" \.PYTHON_SPEC',
        f'default "{python_spec}" .PYTHON_SPEC',
    ):
        updates.append("Taskfile.yml")

    pyproject = ROOT / "pyproject.toml"
    if replace_text(
        pyproject,
        r'requires-python = ">=\d+\.\d+"',
        f'requires-python = ">={python_spec}"',
    ):
        updates.append("pyproject.toml")

    uv_lock = ROOT / "uv.lock"
    if uv_lock.exists():
        if replace_text(
            uv_lock,
            r'requires-python = ">=\d+\.\d+"',
            f'requires-python = ">={python_spec}"',
        ):
            updates.append("uv.lock")

    return updates


def main() -> None:
    downloads = run_uv_python_list()
    python_spec, full_version = choose_latest_cpython(downloads)

    taskfile = ROOT / "Taskfile.yml"
    current_spec = current_python_spec(taskfile)

    if current_spec == python_spec:
        print(f"Already using the latest CPython minor release ({python_spec}, {full_version}).")
        return

    updated_files = update_files(python_spec)
    if not updated_files:
        raise SystemExit("No files were updated, but an update was expected.")

    updated_list = ", ".join(updated_files)
    print(
        f"Updated Python version spec to {python_spec} (latest release {full_version}) "
        f"in {updated_list}."
    )


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr or "")
        raise SystemExit(exc.returncode) from exc
