#!/usr/bin/env python3
"""
Split an MP3 file into a subclip using ffmpeg.

Example:
    python scripts/split_mp3.py ~/music/song.mp3 3:00 5:11
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def parse_timestamp(value: str) -> float:
    """Parse a timestamp in H:M:S, M:S, or S format into seconds."""
    parts = value.strip().split(":")
    if not parts or any(part.strip() == "" for part in parts):
        raise ValueError(f"Invalid timestamp: {value!r}")

    seconds = 0.0
    for part in parts:
        try:
            component = float(part)
        except ValueError as exc:
            raise ValueError(f"Invalid timestamp: {value!r}") from exc
        if component < 0:
            raise ValueError("Timestamp values must be non-negative.")
        seconds = seconds * 60 + component

    return seconds


def ffmpeg_timestamp(seconds: float) -> str:
    """Format seconds into a timestamp string accepted by ffmpeg."""
    if seconds < 0:
        raise ValueError("Timestamp must be non-negative.")

    total_milliseconds = round(seconds * 1000)
    total_seconds, milliseconds = divmod(total_milliseconds, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, full_seconds = divmod(remainder, 60)

    if milliseconds:
        return f"{hours:02d}:{minutes:02d}:{full_seconds:02d}.{milliseconds:03d}"

    return f"{hours:02d}:{minutes:02d}:{full_seconds:02d}"


def filename_label(seconds: float) -> str:
    """Create a readable label for filenames from a second count."""
    total_milliseconds = round(seconds * 1000)
    total_seconds, milliseconds = divmod(total_milliseconds, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, full_seconds = divmod(remainder, 60)

    parts: list[str] = []
    if hours:
        parts.append(f"{hours:02d}h")
    parts.append(f"{minutes:02d}m")
    parts.append(f"{full_seconds:02d}s")
    if milliseconds:
        parts.append(f"{milliseconds:03d}ms")

    return "".join(parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split an MP3 into a subclip using ffmpeg.",
    )
    parser.add_argument("input", help="Path to the source MP3 file.")
    parser.add_argument("start", help="Clip start time (e.g. 3:00 or 00:03:00).")
    parser.add_argument("end", help="Clip end time (must be after start).")
    parser.add_argument(
        "-o",
        "--output",
        help="Path for the output MP3. Defaults to the input name with a suffix.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        parser.error("ffmpeg is required but was not found on PATH.")

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        parser.error(f"Input file does not exist: {input_path}")

    try:
        start_seconds = parse_timestamp(args.start)
        end_seconds = parse_timestamp(args.end)
    except ValueError as exc:
        parser.error(str(exc))

    if start_seconds >= end_seconds:
        parser.error("End time must be greater than start time.")

    if args.output:
        output_path = Path(args.output).expanduser()
    else:
        suffix = filename_label(start_seconds) + "-" + filename_label(end_seconds)
        output_path = input_path.with_name(
            f"{input_path.stem}_{suffix}{input_path.suffix}"
        )

    if output_path.exists() and not args.overwrite:
        parser.error(
            f"Output file {output_path} already exists. Pass --overwrite to replace it."
        )

    command = [
        ffmpeg_path,
        ("-y" if args.overwrite else "-n"),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-ss",
        ffmpeg_timestamp(start_seconds),
        "-to",
        ffmpeg_timestamp(end_seconds),
        "-c",
        "copy",
        str(output_path),
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        parser.error(f"ffmpeg failed with exit code {exc.returncode}.")

    print(f"Created clip at {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
