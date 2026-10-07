"""Shared validation, output, and CLI helpers for the multimedia labs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


class MediaError(Exception):
    """An expected, user-facing media or processing error."""


def validate_file(file_name: str | Path) -> Path:
    path = Path(file_name).expanduser().resolve()
    if not path.exists():
        raise MediaError(f"File not found: {path}")
    if not path.is_file():
        raise MediaError(f"Path is not a file: {path}")
    return path


def output_directory(destination: str | Path) -> Path:
    root = Path(destination).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = root / stamp
    directory.mkdir()
    return directory


def _report_cli(
    extract: Callable[[Path], dict[str, Any]],
    title: str,
    standalone: bool,
) -> int:
    parser = argparse.ArgumentParser(description=f"Extract {title}.")
    parser.add_argument("file", help="Path to a media file")
    parser.add_argument("--json", dest="json_path", type=Path, help="Save the report as JSON")
    args = parser.parse_args()

    try:
        report = extract(validate_file(args.file))
        serialized = json.dumps(report, indent=2, ensure_ascii=False)
        print(serialized)
        if args.json_path:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            args.json_path.write_text(serialized + "\n", encoding="utf-8")
            print(f"\nReport saved: {args.json_path}")
    except (MediaError, OSError) as exc:
        print(f"{title}: {exc}", file=sys.stderr)
        return 1
    return 0


def metadata_cli(
    extract: Callable[[Path], dict[str, Any]],
    title: str,
    standalone: bool = False,
) -> int:
    return _report_cli(extract, title, standalone)


def processing_cli(
    process: Callable[..., list[Path]],
    title: str,
    default_output: str,
    video: bool = False,
) -> int:
    parser = argparse.ArgumentParser(description=title)
    parser.add_argument("file", help="Path to a media file")
    parser.add_argument("--output-dir", default=default_output, help="Directory for a new results folder")
    if video:
        parser.add_argument("--start", type=float, default=0.0, help="Trim start time in seconds")
        parser.add_argument("--duration", type=float, default=2.0, help="Trim duration in seconds")
    args = parser.parse_args()

    try:
        if video:
            outputs = process(args.file, args.output_dir, args.start, args.duration)
        else:
            outputs = process(args.file, args.output_dir)
        for path in outputs:
            print(path)
    except (MediaError, OSError, ValueError) as exc:
        print(f"{title}: {exc}", file=sys.stderr)
        return 1
    return 0
