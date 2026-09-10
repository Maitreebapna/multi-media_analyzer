"""Video metadata extraction via ffprobe."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from core.utils import MediaInspectorError, detect_mime_type, format_duration, human_size


class VideoParser:
    """Extract container, duration, and video/audio stream details."""

    def analyze(self, path: Path) -> dict[str, Any]:
        payload = self._run_ffprobe(path)
        fmt = payload.get("format") or {}
        streams = payload.get("streams") or []

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        duration = self._to_float(fmt.get("duration"))
        if duration is None and video_stream:
            duration = self._to_float(video_stream.get("duration"))

        return {
            "kind": "video",
            "file": {
                "path": str(path),
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "size_human": human_size(path.stat().st_size),
                "mime_type": detect_mime_type(path),
            },
            "container": {
                "format_name": fmt.get("format_name"),
                "format_long_name": fmt.get("format_long_name"),
                "bit_rate_bps": self._to_int(fmt.get("bit_rate")),
            },
            "duration_seconds": duration,
            "duration": format_duration(duration),
            "video_stream": self._video_details(video_stream) if video_stream else None,
            "audio_stream": self._audio_details(audio_stream) if audio_stream else None,
            "stream_count": len(streams),
        }

    def _run_ffprobe(self, path: Path) -> dict[str, Any]:
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise MediaInspectorError(
                "FFmpeg/ffprobe was not found on PATH. Install FFmpeg and try again. "
                "See README.md for install instructions."
            )

        command = [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise MediaInspectorError(f"Failed to run ffprobe: {exc}") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip() or "unknown ffprobe error"
            raise MediaInspectorError(
                f"Could not analyze video '{path.name}'. The file may be corrupted. ({stderr})"
            )

        try:
            data = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise MediaInspectorError("ffprobe returned invalid JSON.") from exc

        if not data.get("format") and not data.get("streams"):
            raise MediaInspectorError(
                f"No streams found in '{path.name}'. The file may be corrupted or not a video."
            )
        return data

    def _video_details(self, stream: dict[str, Any]) -> dict[str, Any]:
        width = stream.get("width")
        height = stream.get("height")
        fps = self._parse_rate(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
        return {
            "codec": stream.get("codec_name"),
            "codec_long_name": stream.get("codec_long_name"),
            "profile": stream.get("profile"),
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}" if width and height else None,
            "fps": fps,
            "pixel_format": stream.get("pix_fmt"),
            "bit_rate_bps": self._to_int(stream.get("bit_rate")),
        }

    def _audio_details(self, stream: dict[str, Any]) -> dict[str, Any]:
        return {
            "codec": stream.get("codec_name"),
            "codec_long_name": stream.get("codec_long_name"),
            "channels": stream.get("channels"),
            "channel_layout": stream.get("channel_layout"),
            "sample_rate_hz": self._to_int(stream.get("sample_rate")),
            "bit_rate_bps": self._to_int(stream.get("bit_rate")),
        }

    @staticmethod
    def _parse_rate(value: str | None) -> float | None:
        if not value or value in {"0/0", "N/A"}:
            return None
        try:
            if "/" in value:
                num, den = value.split("/", 1)
                denominator = float(den)
                if denominator == 0:
                    return None
                return round(float(num) / denominator, 3)
            return round(float(value), 3)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: Any) -> int | None:
        try:
            return int(float(value)) if value is not None else None
        except (TypeError, ValueError):
            return None
