"""Convert, normalize, and reverse 16-bit PCM WAV audio."""

import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import numpy as np
    from multimedia.cli import processing_cli
    from multimedia.common import MediaError, output_directory, validate_file
    from multimedia.metadata import wav_metadata
except ImportError as exc:
    raise SystemExit(f"Missing dependency: {exc}. Run: python -m pip install -r requirements.txt")


def process_audio(file_name, destination):
    path = validate_file(file_name)
    metadata = wav_metadata(path)
    channels = metadata.get("channels")
    if metadata.get("sample_width_bits") != 16 or channels not in (1, 2):
        raise MediaError("Audio processing requires mono or stereo 16-bit PCM WAV.")
    try:
        with wave.open(str(path), "rb") as source:
            if source.getcomptype() != "NONE":
                raise MediaError("Compressed WAV files are not supported.")
            samples = np.frombuffer(
                source.readframes(source.getnframes()), dtype="<i2"
            ).reshape(-1, channels)
    except (wave.Error, ValueError) as exc:
        raise MediaError(f"Could not decode WAV file '{path.name}': {exc}") from exc
    if samples.size == 0:
        raise MediaError("WAV file contains no audio frames.")

    wide_samples = samples.astype(np.float64)
    peak = np.max(np.abs(wide_samples))
    normalized = wide_samples * (32767 / peak) if peak else wide_samples
    results = {
        "mono": np.rint(wide_samples.mean(axis=1)).astype("<i2").reshape(-1, 1),
        "normalized": np.clip(np.rint(normalized), -32768, 32767).astype("<i2"),
        "reversed": samples[::-1],
    }
    directory = output_directory(destination)
    outputs = []
    for name, result in results.items():
        output = directory / f"{name}.wav"
        with wave.open(str(output), "wb") as target:
            target.setnchannels(result.shape[1])
            target.setsampwidth(2)
            target.setframerate(metadata["sample_rate"])
            target.writeframes(result.tobytes())
        outputs.append(output)
    return outputs


if __name__ == "__main__":
    raise SystemExit(processing_cli(process_audio, "WAV audio processing", "outputs/audio"))
