"""Create grayscale, resized, trimmed, reversed, and sampled video outputs."""

import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import cv2
    import numpy as np
    from multimedia.cli import processing_cli
    from multimedia.common import MediaError, output_directory, validate_file
    from multimedia.metadata import video_metadata
except ImportError as exc:
    raise SystemExit(f"Missing dependency: {exc}. Run: python -m pip install -r requirements.txt")


def _save_png(path, frame):
    success, encoded = cv2.imencode(".png", frame)
    if not success:
        raise MediaError(f"Could not encode image '{path.name}'.")
    path.write_bytes(encoded.tobytes())


def process_video(file_name, destination, start=0.0, duration=2.0):
    if not math.isfinite(start) or start < 0 or not math.isfinite(duration) or duration <= 0:
        raise MediaError("Trim start must be nonnegative; duration must be positive.")
    path = validate_file(file_name)
    metadata = video_metadata(path)
    if metadata.get("duration_seconds") and start >= metadata["duration_seconds"]:
        raise MediaError("Trim start is beyond the end of the video.")

    capture = cv2.VideoCapture(str(path))
    writers = {}
    try:
        if not capture.isOpened():
            raise MediaError("OpenCV could not open this video.")
        fps = capture.get(cv2.CAP_PROP_FPS)
        success, first = capture.read()
        if not success or not math.isfinite(fps) or fps <= 0:
            raise MediaError("Video has no readable frames or valid frame rate.")
        height, width = first.shape[:2]
        if width < 4 or height < 4 or width % 2 or height % 2:
            raise MediaError("Video dimensions must be even and at least 4 pixels.")

        directory = output_directory(destination)
        frame_dir = directory / "frames"
        frame_dir.mkdir()
        output_paths = {
            name: directory / f"{name}.avi"
            for name in ("grayscale", "resize_half", "trimmed", "reversed")
        }
        half = (max(2, width // 4 * 2), max(2, height // 4 * 2))
        for name, output in output_paths.items():
            size = half if name == "resize_half" else (width, height)
            writer = cv2.VideoWriter(
                str(output), cv2.VideoWriter_fourcc(*"MJPG"), fps, size
            )
            if not writer.isOpened():
                raise MediaError("OpenCV MJPEG video encoder is unavailable.")
            writers[name] = writer

        thumbnail = directory / "thumbnail.png"
        _save_png(thumbnail, first)
        exported = [*output_paths.values(), thumbnail]
        frame_count = 0
        trimmed_count = 0
        frame_bytes = first.nbytes
        with tempfile.TemporaryFile(dir=directory) as spool:
            frame = first
            while success:
                if frame.shape != first.shape:
                    raise MediaError("Video changes resolution midstream.")
                timestamp = frame_count / fps
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                writers["grayscale"].write(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
                writers["resize_half"].write(
                    cv2.resize(frame, half, interpolation=cv2.INTER_AREA)
                )
                if start <= timestamp < start + duration:
                    writers["trimmed"].write(frame)
                    trimmed_count += 1
                if frame_count == 0 or int(timestamp) > int((frame_count - 1) / fps):
                    sample = frame_dir / f"frame_{frame_count:06d}.png"
                    _save_png(sample, frame)
                    exported.append(sample)
                spool.write(frame.tobytes())
                frame_count += 1
                success, frame = capture.read()
            if not trimmed_count:
                raise MediaError("Selected trim range contains no video frames.")
            for index in range(frame_count - 1, -1, -1):
                spool.seek(index * frame_bytes)
                reversed_frame = np.frombuffer(spool.read(frame_bytes), dtype=np.uint8)
                writers["reversed"].write(reversed_frame.reshape(first.shape))

        return [*output_paths.values(), thumbnail, *sorted(frame_dir.glob("*.png"))]
    except cv2.error as exc:
        raise MediaError(f"OpenCV could not process the video: {exc}") from exc
    finally:
        capture.release()
        for writer in writers.values():
            writer.release()


if __name__ == "__main__":
    raise SystemExit(
        processing_cli(
            process_video,
            "Video processing (silent MJPEG AVI outputs)",
            "outputs/video",
            video=True,
        )
    )
