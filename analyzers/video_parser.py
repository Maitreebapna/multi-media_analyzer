"""Video metadata extraction using OpenCV's built-in video reader."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2

from core.utils import MediaInspectorError, detect_mime_type, format_duration, human_size


class VideoParser:
    """Extract basic container and video-stream details without ffprobe."""

    def analyze(self, path: Path) -> dict[str, Any]:
        capture = cv2.VideoCapture(str(path))
        try:
            if not capture.isOpened():
                raise MediaInspectorError(
                    f"Could not open video '{path.name}'. Its format or codec may not be supported by OpenCV."
                )

            width = self._positive_int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = self._positive_int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self._positive_float(capture.get(cv2.CAP_PROP_FPS))
            frame_count = self._positive_int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            fourcc_value = self._positive_int(capture.get(cv2.CAP_PROP_FOURCC))

            ok, _ = capture.read()
            if not ok or not width or not height:
                raise MediaInspectorError(
                    f"Could not decode video '{path.name}'. The file may be corrupted or use an unsupported codec."
                )
        except cv2.error as exc:
            raise MediaInspectorError(f"OpenCV could not analyze '{path.name}': {exc}") from exc
        finally:
            capture.release()

        duration = frame_count / fps if frame_count and fps else None
        suffix = path.suffix.lower().lstrip(".")
        codec = self._fourcc(fourcc_value)
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
                "format_name": suffix or None,
                "format_long_name": f"{suffix.upper()} video" if suffix else None,
                "bit_rate_bps": None,
            },
            "duration_seconds": round(duration, 3) if duration is not None else None,
            "duration": format_duration(duration),
            "video_stream": {
                "codec": codec,
                "codec_long_name": None,
                "profile": None,
                "width": width,
                "height": height,
                "resolution": f"{width}x{height}" if width and height else None,
                "fps": round(fps, 3) if fps is not None else None,
                "pixel_format": None,
                "bit_rate_bps": None,
                "frame_count": frame_count,
            },
            "audio_stream": None,
            "stream_count": 1,
            "metadata_note": (
                "OpenCV provides basic video-track metadata only. Audio streams, "
                "container tags, and exact bitrates are not inspected."
            ),
        }

    @staticmethod
    def _positive_int(value: float) -> int | None:
        if not math.isfinite(value) or value <= 0:
            return None
        return int(round(value))

    @staticmethod
    def _positive_float(value: float) -> float | None:
        if not math.isfinite(value) or value <= 0:
            return None
        return value

    @staticmethod
    def _fourcc(value: int | None) -> str | None:
        if not value:
            return None
        code = "".join(chr((value >> (8 * index)) & 0xFF) for index in range(4))
        readable = "".join(character for character in code if character.isprintable()).strip()
        return readable or None
