"""Image metadata extraction using Pillow."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, UnidentifiedImageError

from core.utils import MediaInspectorError, detect_mime_type, human_size


class ImageParser:
    """Extract size, format, dimensions, color mode, and EXIF fields."""

    def analyze(self, path: Path) -> dict[str, Any]:
        try:
            with Image.open(path) as image:
                image.load()
                info = {
                    "kind": "image",
                    "file": {
                        "path": str(path),
                        "name": path.name,
                        "size_bytes": path.stat().st_size,
                        "size_human": human_size(path.stat().st_size),
                        "mime_type": detect_mime_type(path),
                    },
                    "format": image.format,
                    "mode": image.mode,
                    "width": image.width,
                    "height": image.height,
                    "dimensions": f"{image.width}x{image.height}",
                    "animated": bool(getattr(image, "is_animated", False)),
                    "frames": int(getattr(image, "n_frames", 1) or 1),
                    "exif": self._extract_exif(image),
                }
        except UnidentifiedImageError as exc:
            raise MediaInspectorError(
                f"Could not read image '{path.name}'. The file may be corrupted or not a valid image."
            ) from exc
        except OSError as exc:
            raise MediaInspectorError(f"Failed to open image '{path.name}': {exc}") from exc
        return info

    def _extract_exif(self, image: Image.Image) -> dict[str, Any]:
        try:
            raw = image.getexif()
        except Exception:
            return {}

        if not raw:
            return {}

        decoded: dict[str, Any] = {}
        for tag_id, value in raw.items():
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            decoded[name] = self._stringify(value)

        camera = {
            "make": decoded.get("Make"),
            "model": decoded.get("Model"),
            "lens_model": decoded.get("LensModel"),
            "software": decoded.get("Software"),
            "capture_date": self._first_present(
                decoded,
                ("DateTimeOriginal", "DateTimeDigitized", "DateTime"),
            ),
            "orientation": decoded.get("Orientation"),
            "exposure_time": decoded.get("ExposureTime"),
            "f_number": decoded.get("FNumber"),
            "iso": decoded.get("ISOSpeedRatings") or decoded.get("PhotographicSensitivity"),
            "focal_length": decoded.get("FocalLength"),
        }

        return {
            "camera": {k: v for k, v in camera.items() if v not in (None, "")},
            "all_tags": decoded,
        }

    @staticmethod
    def _first_present(tags: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = tags.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _stringify(value: Any) -> Any:
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="replace").strip("\x00")
            except Exception:
                return repr(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (int, float, str, bool)) or value is None:
            return value
        return str(value)
