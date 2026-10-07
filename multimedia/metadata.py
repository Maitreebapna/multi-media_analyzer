"""Shared metadata entry points used by the standalone lab commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analyzers.audio_parser import AudioParser
from analyzers.image_parser import ImageParser
from analyzers.video_parser import VideoParser
from core.utils import MediaInspectorError

from .common import MediaError


def image_metadata(path: Path) -> dict[str, Any]:
    try:
        return ImageParser().analyze(path)
    except MediaInspectorError as exc:
        raise MediaError(str(exc)) from exc


def audio_metadata(path: Path) -> dict[str, Any]:
    try:
        return AudioParser().analyze(path)
    except MediaInspectorError as exc:
        raise MediaError(str(exc)) from exc


def wav_metadata(path: Path) -> dict[str, Any]:
    result = audio_metadata(path)
    if path.suffix.lower() != ".wav" or result.get("container") not in (
        "audio/wav",
        "audio/x-wav",
        "wav",
        "wave",
    ):
        raise MediaError("Audio processing accepts WAV files only.")
    result["sample_rate"] = result.get("sample_rate_hz")
    result["sample_width_bits"] = result.get("bits_per_sample")
    return result


def video_metadata(path: Path) -> dict[str, Any]:
    try:
        report = VideoParser().analyze(path)
    except MediaInspectorError as exc:
        raise MediaError(str(exc)) from exc
    stream = report.get("video_stream") or {}
    fps = stream.get("fps") or 0
    report.update({
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": fps,
        "frame_count": stream.get("frame_count"),
        "frame_count_estimated": True,
    })
    return report
