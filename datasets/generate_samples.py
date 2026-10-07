"""Generate short, synthetic WAV and AVI files for the processing exercises."""

from __future__ import annotations

import argparse
import math
import wave
from pathlib import Path

import cv2
import numpy as np


def generate_samples(destination: Path) -> tuple[Path, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    sample_rate = 44_100
    seconds = 5
    time = np.arange(sample_rate * seconds) / sample_rate
    signal = np.rint(12_000 * np.sin(2 * math.pi * 440 * time))
    wav_path = destination / "sample.wav"
    with wave.open(str(wav_path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(signal.astype("<i2").tobytes())

    video_path = destination / "sample.avi"
    fps, size = 12.0, (320, 240)
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), fps, size
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not initialize the MJPEG video encoder.")
    try:
        for frame_number in range(36):
            frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
            x = 20 + frame_number * 7
            cv2.rectangle(frame, (x % 270, 70), (x % 270 + 50, 120), (50, 180, 240), -1)
            cv2.putText(
                frame,
                f"Frame {frame_number + 1:02d}",
                (12, 210),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
            )
            writer.write(frame)
    finally:
        writer.release()
    return wav_path, video_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "generated",
        help="Directory in which to save the sample media",
    )
    args = parser.parse_args()
    wav_path, video_path = generate_samples(args.output_dir)
    print(f"Generated: {wav_path}")
    print(f"Generated: {video_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
