# Multimedia Analyzer
Modern Python CLI that inspects **images**, **audio**, and **video** files, prints a Rich summary in the terminal, and writes a full JSON or Markdown report to `outputs/`.
CLI for pulling metadata out of images, audio, and video. It prints a short table in the terminal and dumps the full result as JSON or Markdown under `outputs/`.
## Requirements
Python 3.10+ is required. Video files also need FFmpeg (`ffprobe` on your PATH).
- Python 3.10 or newer
- [FFmpeg](https://ffmpeg.org/) (needed for video analysis via `ffprobe`)
## Setup
## Install
```
# Windows
Windows:
```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```
## Install FFmpeg
## FFmpeg (video only)
Video inspection shells out to `ffprobe`. If it is missing, MediaInspector prints a clean error instead of a stack trace.
`ffprobe` is what we use for video. Images and audio work without it. If it's missing, you'll get a short error in the terminal, not a stack trace.
### Windows
**Windows** — easiest path is:
1. Download a build from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) (for example, Gyan or BtbN builds).
2. Unzip it and add the `bin` folder (the one that contains `ffprobe.exe`) to your PATH.
3. Open a new terminal and confirm:
```powershell
ffprobe -version
```
Alternatively with winget:
```powershell
winget install Gyan.FFmpeg
```
## Quick start
## Try it
This workspace already includes a sample image you can analyze immediately:
There's a `sample.png` in the repo if you just want to see it work:
```powershell
cd C:\Users\maitree\multi-media_analyzer

[1 line collapsed]

python main.py analyze .\sample.png --format json
```
Or use the helper script:
Same thing via `run.ps1`:
```powershell
cd C:\Users\maitree\multi-media_analyzer
powershell -ExecutionPolicy Bypass -File .\run.ps1 -Path .\sample.png -Format json
```
## Usage
## Commands
Analyze a file and write a JSON report (default):
JSON (default):
```bash
python main.py analyze path/to/photo.jpg --format json
```
Markdown report:
Markdown:
```bash
python main.py analyze path/to/song.mp3 --format md
```
Video example:
Video:
```bash
python main.py analyze path/to/clip.mp4 --format json
```
Write to a custom path:
Write somewhere other than `outputs/`:
```bash
python main.py analyze photo.jpg --format md --output ./my-report.md
```
The CLI auto-detects media type from extension and MIME type.
The tool picks image / audio / video from the file extension and MIME type.
## What gets extracted
## What's in the report
| Kind | Fields |
|------|--------|
| Image | File size, format, dimensions, color mode, EXIF (camera make/model, capture date, and remaining tags) |
| Audio | Duration, bitrate, sample rate, channels, tags (artist, album, title, and others) |
| Video | Container, duration, video stream (resolution, fps, codec), audio stream (codec, channels) |
- **Image** — size, format, width/height, color mode, EXIF (camera, capture date, plus the rest of the tags if they're there)
- **Audio** — duration, bitrate, sample rate, channels, tags like artist / album / title
- **Video** — container, duration, video stream (resolution, fps, codec), audio stream (codec, channels)
Reports land in `outputs/` as `<filename>_<UTC-timestamp>.json` or `.md`.
Files are named like `photo_20260910T104854Z.json` (UTC timestamp) and land in `outputs/` unless you pass `--output`.
## Project layout
## Layout
```
multi-media_analyzer/
├── main.py                  # Typer CLI
├── main.py              # typer entry point
├── run.ps1              # optional Windows helper
├── requirements.txt
├── analyzers/
│   ├── image_parser.py      # Pillow / EXIF
│   ├── audio_parser.py      # mutagen
│   └── video_parser.py      # ffprobe
│   ├── image_parser.py  # Pillow
│   ├── audio_parser.py  # mutagen
│   └── video_parser.py  # ffprobe
├── core/
│   ├── report_writer.py
│   └── utils.py
└── outputs/
```
## Error handling
Missing files, junk media, unsupported types, and a missing `ffprobe` all show up as a red panel. We don't dump a traceback for those.
Corrupt files, missing paths, unsupported types, and a missing `ffprobe` binary are reported with a red Rich panel. Full Python stack traces are not shown for these expected failures.
