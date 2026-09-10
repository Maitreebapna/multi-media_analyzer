"""File checks, MIME detection, and shared helpers."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Literal

MediaKind = Literal["image", "audio", "video"]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".aiff"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv", ".m4v", ".mpeg", ".mpg"}


class MediaInspectorError(Exception):
    """User-facing application error (shown without a stack trace)."""


def ensure_file_exists(filepath: str | Path) -> Path:
    path = Path(filepath).expanduser().resolve()
    if not path.exists():
        raise MediaInspectorError(f"File not found: {path}")
    if not path.is_file():
        raise MediaInspectorError(f"Path is not a file: {path}")
    return path


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{num_bytes} B"


def detect_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def detect_media_kind(path: Path) -> MediaKind:
    suffix = path.suffix.lower()
    mime = detect_mime_type(path)

    if suffix in IMAGE_EXTENSIONS or mime.startswith("image/"):
        return "image"
    if suffix in AUDIO_EXTENSIONS or mime.startswith("audio/"):
        return "audio"
    if suffix in VIDEO_EXTENSIONS or mime.startswith("video/"):
        return "video"

    raise MediaInspectorError(
        f"Unsupported media type for '{path.name}'. "
        "Supported: images (JPEG, PNG, GIF, WebP, TIFF, BMP), "
        "audio (MP3, FLAC, WAV, OGG, M4A), "
        "video (MP4, MKV, AVI, MOV, WebM)."
    )


def format_duration(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
