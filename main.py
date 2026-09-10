"""MediaInspector — Typer CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from analyzers.audio_parser import AudioParser
from analyzers.image_parser import ImageParser
from analyzers.video_parser import VideoParser
from core.report_writer import write_report
from core.utils import MediaInspectorError, detect_media_kind, ensure_file_exists

app = typer.Typer(
    help="Analyze image, audio, and video files and export deep metadata reports.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
)


@app.callback()
def _root() -> None:
    """MediaInspector command-line interface."""
console = Console(stderr=True)
stdout = Console()

PARSERS = {
    "image": ImageParser(),
    "audio": AudioParser(),
    "video": VideoParser(),
}


@app.command()
def analyze(
    filepath: str = typer.Argument(..., help="Path to an image, audio, or video file."),
    format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Report format: json or md.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional custom report path. Defaults to outputs/.",
    ),
) -> None:
    """Inspect a multimedia file and write a JSON or Markdown report."""
    try:
        path = ensure_file_exists(filepath)
        kind = detect_media_kind(path)
        data = PARSERS[kind].analyze(path)
        report_path = _save_report(data, format, path, output)
    except MediaInspectorError as exc:
        console.print(Panel(str(exc), title="MediaInspector", border_style="red", title_align="left"))
        raise typer.Exit(code=1) from exc
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(code=130)

    _print_summary(data)
    stdout.print(f"\n[green]Report saved:[/green] {report_path}")


def _save_report(data: dict[str, Any], fmt: str, source: Path, custom: Path | None) -> Path:
    if custom is None:
        return write_report(data, fmt, source)

    custom.parent.mkdir(parents=True, exist_ok=True)
    written = write_report(data, fmt, source)
    custom.write_bytes(written.read_bytes())
    written.unlink(missing_ok=True)
    return custom


def _print_summary(data: dict[str, Any]) -> None:
    kind = str(data.get("kind", "media")).title()
    file_info = data.get("file") or {}

    table = Table(title=f"{kind} Summary", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("File", str(file_info.get("name", "")))
    table.add_row("Size", str(file_info.get("size_human", "")))
    table.add_row("MIME", str(file_info.get("mime_type", "")))

    if data.get("kind") == "image":
        table.add_row("Format", str(data.get("format")))
        table.add_row("Dimensions", str(data.get("dimensions")))
        table.add_row("Color mode", str(data.get("mode")))
        camera = (data.get("exif") or {}).get("camera") or {}
        table.add_row("Camera", _join_parts(camera.get("make"), camera.get("model")))
        table.add_row("Capture date", str(camera.get("capture_date") or "n/a"))
    elif data.get("kind") == "audio":
        table.add_row("Duration", str(data.get("duration") or "n/a"))
        table.add_row("Bitrate", _kbps(data.get("bitrate_kbps")))
        table.add_row("Sample rate", _hz(data.get("sample_rate_hz")))
        table.add_row("Channels", str(data.get("channels") or "n/a"))
        tags = (data.get("tags") or {}).get("common") or {}
        table.add_row("Title", str(tags.get("title") or "n/a"))
        table.add_row("Artist", str(tags.get("artist") or "n/a"))
        table.add_row("Album", str(tags.get("album") or "n/a"))
    else:
        table.add_row("Duration", str(data.get("duration") or "n/a"))
        container = data.get("container") or {}
        table.add_row("Container", str(container.get("format_long_name") or container.get("format_name") or "n/a"))
        video = data.get("video_stream") or {}
        audio = data.get("audio_stream") or {}
        table.add_row(
            "Video",
            f"{video.get('resolution') or 'n/a'} @ {video.get('fps') or 'n/a'} fps ({video.get('codec') or 'n/a'})",
        )
        table.add_row("Audio", f"{audio.get('codec') or 'n/a'} / {audio.get('channels') or 'n/a'} ch")

    stdout.print(table)


def _join_parts(*parts: Any) -> str:
    values = [str(part).strip() for part in parts if part]
    return " ".join(values) if values else "n/a"


def _kbps(value: Any) -> str:
    return f"{value} kbps" if value else "n/a"


def _hz(value: Any) -> str:
    return f"{value} Hz" if value else "n/a"


@app.command()
def version() -> None:
    """Print the application version."""
    stdout.print("MediaInspector 1.0.0")


if __name__ == "__main__":
    app()
