from __future__ import annotations

import importlib.util
import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


image_processing = load_module(
    "image_processing", "Cluster02-Image-Processing/image_processing.py"
)
audio_processing = load_module(
    "audio_processing", "Cluster03-Audio-Processing/audio_processing.py"
)
video_processing = load_module(
    "video_processing", "Cluster04-Video-Processing/video_processing.py"
)
generate_samples = load_module("generate_samples", "datasets/generate_samples.py")


class ProcessingLabTests(unittest.TestCase):
    def test_image_processing_writes_six_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "input.png"
            Image.new("RGB", (32, 24), color=(120, 60, 30)).save(image)

            outputs = image_processing.process_image(image, root / "results")

            self.assertEqual(len(outputs), 6)
            self.assertTrue(all(path.is_file() and path.stat().st_size for path in outputs))

    def test_audio_processing_writes_three_valid_wav_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wav_path, _ = generate_samples.generate_samples(root / "samples")

            outputs = audio_processing.process_audio(wav_path, root / "results")

            self.assertEqual({path.stem for path in outputs}, {"mono", "normalized", "reversed"})
            for output in outputs:
                with wave.open(str(output), "rb") as result:
                    self.assertEqual(result.getsampwidth(), 2)
                    self.assertEqual(result.getframerate(), 44_100)
                    self.assertEqual(result.getnframes(), 220_500)

    def test_video_metadata_and_processing_work_without_ffprobe(self) -> None:
        from analyzers.video_parser import VideoParser

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, video_path = generate_samples.generate_samples(root / "samples")

            metadata = VideoParser().analyze(video_path)
            outputs = video_processing.process_video(
                video_path, root / "video-results", start=0.5, duration=1
            )

            self.assertEqual(metadata["video_stream"]["resolution"], "320x240")
            self.assertAlmostEqual(metadata["video_stream"]["fps"], 12.0)
            self.assertEqual(metadata["video_stream"]["frame_count"], 36)
            self.assertIsNone(metadata["audio_stream"])
            self.assertEqual(
                {path.name for path in outputs if path.suffix == ".avi"},
                {"grayscale.avi", "resize_half.avi", "trimmed.avi", "reversed.avi"},
            )


if __name__ == "__main__":
    unittest.main()
