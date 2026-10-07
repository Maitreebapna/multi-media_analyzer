# Example outputs

This folder contains small generated examples from the analyzer and processing
labs. They are committed intentionally so the repository includes visible
results without requiring the reviewer to run every command first.

- `reports/`: sample image, audio, and video metadata reports.
- `samples/`: synthetic WAV and AVI inputs produced by
  `python datasets/generate_samples.py --output-dir outputs/demo/samples`.
- `images/`, `audio/`, and `video/`: example transformation results.
- `ocr/`: enhanced sample image and browser-viewable HTML results page. OCR is
  disabled for this demonstration; actual recognition needs Tesseract.
- The separate voice transformer cannot include a real converted-audio result:
  it requires a private ElevenLabs API key and account access.

To regenerate media outputs from the repository root, first create the sample
inputs, then run:

```powershell
python main.py analyze .\sample.png --format json --output .\outputs\demo\reports\image.json
python main.py analyze .\outputs\demo\samples\sample.wav --format json --output .\outputs\demo\reports\audio.json
python main.py analyze .\outputs\demo\samples\sample.avi --format json --output .\outputs\demo\reports\video.json
python .\Cluster02-Image-Processing\image_processing.py .\sample.png --output-dir .\outputs\demo\images
python .\Cluster03-Audio-Processing\audio_processing.py .\outputs\demo\samples\sample.wav --output-dir .\outputs\demo\audio
python .\Cluster04-Video-Processing\video_processing.py .\outputs\demo\samples\sample.avi --output-dir .\outputs\demo\video
python .\Cluster05-Task-Pipe\ocr_pipeline.py .\sample.png --no-ocr --output-dir .\outputs\demo\ocr
```

Processing commands create a new timestamped subfolder on every run; remove
old generated folders manually if you want a fresh, compact demonstration.
