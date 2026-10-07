# Multimedia Systems Lab

A Python multimedia project for inspecting and processing images, audio, and
video, plus an optional OCR pipeline and a separate voice-transformation web
app.

## Project contents

| Area | Features | Location |
| --- | --- | --- |
| Media analyzer | Image EXIF, audio tags/streams, video container and streams; JSON/Markdown reports | `main.py`, `analyzers/`, `core/` |
| Image lab | Metadata, grayscale, resize, threshold, blur, edges, rotate | `Cluster02-Image-Processing/` |
| Audio lab | Metadata, mono conversion, peak normalization, reverse | `Cluster03-Audio-Processing/` |
| Video lab | Metadata, grayscale, half-size resize, trim, reverse, thumbnails/frames | `Cluster04-Video-Processing/` |
| OCR pipeline | Image enhancement, deskewing, and local Tesseract OCR | `Cluster05-Task-Pipe/` |
| Voice transformer | Separate Node.js web app for speech-to-speech conversion | `voice-transformer/` |

## Setup (Windows PowerShell)

Python 3.10 or newer is required. OpenCV reads video files directly, so FFmpeg
and `ffprobe` do not need to be installed. Supported video codecs depend on the
OpenCV build and input file.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

OCR additionally needs the Tesseract executable and language data installed on
the machine; see [`Cluster05-Task-Pipe/README.md`](Cluster05-Task-Pipe/README.md).
The voice app needs Node.js 20 or newer and an ElevenLabs API key; it uses
Node's built-in modules, so no npm package installation is needed. See
[`voice-transformer/README.md`](voice-transformer/README.md). Never commit
`.env` files or API keys.

## Try it

Analyze the included image:

```powershell
python main.py analyze .\sample.png --format json
```

Each lab prints extracted metadata or the paths of the generated output files.
Image/audio/video processing creates a new timestamped folder so earlier lab
outputs are not overwritten. The OCR pipeline writes named files under its
output directory; choose a new `--output-dir` to keep earlier OCR results.
Checked-in example reports and transformed media are available in
[`outputs/demo/`](outputs/demo/README.md); other generated output remains ignored.
Run the report and processing commands there to see the committed JSON reports,
images, WAV/AVI examples, and OCR results page.

```powershell
python Cluster02-Image-Processing/image_metadata.py .\sample.png
python Cluster02-Image-Processing/image_processing.py .\sample.png

# Processing audio accepts mono or stereo, 16-bit PCM WAV.
python Cluster03-Audio-Processing/audio_metadata.py .\datasets\generated\sample.wav
python Cluster03-Audio-Processing/audio_processing.py .\datasets\generated\sample.wav

# Video workflows use OpenCV; codec support depends on your OpenCV build.
python Cluster04-Video-Processing/video_metadata.py .\datasets\generated\sample.avi
python Cluster04-Video-Processing/video_processing.py .\datasets\generated\sample.avi --start 0.5 --duration 1

# Enhance an image without OCR, or use OCR when Tesseract is installed.
python Cluster05-Task-Pipe/ocr_pipeline.py .\sample.png --no-ocr
```

Generate small synthetic WAV/AVI files for the processing examples:

```powershell
python .\datasets\generate_samples.py
```

Analyzer reports can also be Markdown, and can be written to a custom path:

```powershell
python main.py analyze .\sample.png --format md --output .\outputs\sample-report.md
```

To start and test the optional voice transformer:

```powershell
cd .\voice-transformer
Copy-Item .env.example .env
# Add your ELEVENLABS_API_KEY to .env, then:
npm start
# In another terminal in this folder:
npm test
```

## Report fields

| Media | Extracted information |
| --- | --- |
| Image | File size/type, format, dimensions, color mode, frame count, EXIF camera/date/settings |
| Audio | Duration, bitrate, sample rate, channels, codec, common and raw tags |
| Video | Container, duration, video/audio codecs and stream properties |

Processing is deliberately format-limited where the operation requires it:
audio transforms accept 16-bit PCM WAV; video exports are silent MJPEG AVI.

## Tests

Run the focused Python and web-app checks from the repository root:

```powershell
python -m unittest discover -s tests -v
python -m unittest discover -s Cluster05-Task-Pipe -p "test_*.py" -v
Push-Location .\voice-transformer
npm test
Pop-Location
```

The OCR unit tests cover preprocessing and reports without requiring Tesseract.
Actual text recognition requires the system Tesseract executable and requested
language data. Video metadata uses OpenCV and does not inspect audio tracks,
container tags, or exact bitrates.

## Structure

```text
.
├── analyzers/                         # Metadata extractors used by main.py
├── core/                              # Report writing and common checks
├── multimedia/                        # Shared lab metadata, validation, and CLI
├── .github/workflows/                 # Python and voice-app checks
├── Cluster02-Image-Processing/
├── Cluster03-Audio-Processing/
├── Cluster04-Video-Processing/
├── Cluster05-Task-Pipe/
├── datasets/                          # Synthetic sample generator
├── voice-transformer/                 # Independent web app
├── outputs/
├── main.py
└── requirements.txt
```
