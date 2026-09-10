"""Audio metadata extraction using mutagen."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.flac import FLAC
from mutagen.id3 import ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from core.utils import MediaInspectorError, detect_mime_type, format_duration, human_size

TAG_ALIASES = {
    "artist": ("artist", "TPE1", "\xa9ART", "Author"),
    "album": ("album", "TALB", "\xa9alb"),
    "title": ("title", "TIT2", "\xa9nam"),
    "album_artist": ("albumartist", "TPE2", "aART"),
    "genre": ("genre", "TCON", "\xa9gen"),
    "year": ("date", "year", "TDRC", "TYER", "\xa9day"),
    "track": ("tracknumber", "TRCK", "trkn"),
    "comment": ("comment", "COMM", "\xa9cmt"),
}


class AudioParser:
    """Extract duration, bitrate, sample rate, channels, and tags."""

    def analyze(self, path: Path) -> dict[str, Any]:
        try:
            audio = MutagenFile(path)
        except ID3NoHeaderError as exc:
            raise MediaInspectorError(
                f"Could not read audio tags from '{path.name}': {exc}"
            ) from exc
        except Exception as exc:
            raise MediaInspectorError(
                f"Could not read audio file '{path.name}'. The file may be corrupted."
            ) from exc

        if audio is None:
            raise MediaInspectorError(
                f"Unsupported or unreadable audio file '{path.name}'."
            )

        info = getattr(audio, "info", None)
        length = getattr(info, "length", None)
        bitrate = getattr(info, "bitrate", None)
        sample_rate = getattr(info, "sample_rate", None)
        channels = getattr(info, "channels", None)
        bits_per_sample = getattr(info, "bits_per_sample", None)

        return {
            "kind": "audio",
            "file": {
                "path": str(path),
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "size_human": human_size(path.stat().st_size),
                "mime_type": detect_mime_type(path),
            },
            "container": audio.mime[0] if getattr(audio, "mime", None) else path.suffix.lstrip("."),
            "duration_seconds": round(float(length), 3) if length is not None else None,
            "duration": format_duration(length),
            "bitrate_bps": int(bitrate) if bitrate else None,
            "bitrate_kbps": round(bitrate / 1000) if bitrate else None,
            "sample_rate_hz": int(sample_rate) if sample_rate else None,
            "channels": int(channels) if channels else None,
            "bits_per_sample": int(bits_per_sample) if bits_per_sample else None,
            "codec": type(audio).__name__,
            "tags": self._extract_tags(audio),
        }

    def _extract_tags(self, audio: Any) -> dict[str, Any]:
        raw_tags: dict[str, Any] = {}
        if audio.tags:
            for key, value in audio.tags.items():
                raw_tags[str(key)] = self._normalize_tag_value(value)

        common: dict[str, Any] = {}
        for field, aliases in TAG_ALIASES.items():
            common[field] = self._lookup_tag(audio, raw_tags, aliases)

        extra = {k: v for k, v in raw_tags.items() if v not in (None, "", [])}
        return {
            "common": {k: v for k, v in common.items() if v not in (None, "")},
            "all": extra,
        }

    def _lookup_tag(self, audio: Any, raw_tags: dict[str, Any], aliases: tuple[str, ...]) -> str | None:
        if isinstance(audio, MP4):
            for alias in aliases:
                if alias in audio.tags:
                    return self._normalize_tag_value(audio.tags[alias])
        if isinstance(audio, (MP3, FLAC, OggVorbis, WAVE)) or audio.tags is not None:
            for alias in aliases:
                values = audio.tags.get(alias) if audio.tags else None
                if values:
                    return self._normalize_tag_value(values)
                for key, value in raw_tags.items():
                    if key.lower() == alias.lower() or key.lower().endswith(alias.lower()):
                        return str(value)
        return None

    @staticmethod
    def _normalize_tag_value(value: Any) -> str:
        if isinstance(value, (list, tuple)):
            if not value:
                return ""
            first = value[0]
            if isinstance(first, tuple):
                return "/".join(str(part) for part in first)
            return str(first)
        return str(value)
