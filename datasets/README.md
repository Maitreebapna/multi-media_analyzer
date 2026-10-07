# Sample media

Run `python datasets/generate_samples.py` to create small, synthetic media files
for the audio and video processing labs. It writes a five-second 16-bit PCM WAV
and a short MJPEG AVI under `datasets/generated/`. No external media assets are
downloaded or needed.

The generator uses NumPy and OpenCV from the root `requirements.txt`. The
project reads the generated AVI with OpenCV and does not require FFmpeg.
