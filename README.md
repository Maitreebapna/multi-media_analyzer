# MediaInspector

Modern Python CLI that inspects **images**, **audio**, and **video** files, prints a Rich summary in the terminal, and writes a full JSON or Markdown report to `outputs/`.

## Requirements

- Python 3.10 or newer
- [FFmpeg](https://ffmpeg.org/) (needed for video analysis via `ffprobe`)

## Install

```bash
cd multi-media_analyzer
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Install FFmpeg

Video inspection shells out to `ffprobe`. If it is missing, MediaInspector prints a clean error instead of a stack trace.

### Windows

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

### macOS

```bash
brew install ffmpeg
```

### Linux (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install ffmpeg
```

## Quick start

This workspace already includes a sample image you can analyze immediately:

```powershell
cd C:\Users\maitree\multi-media_analyzer
.\.venv\Scripts\Activate.ps1
python main.py analyze .\sample.png --format json
```

Or use the helper script:

```powershell
cd C:\Users\maitree\multi-media_analyzer
powershell -ExecutionPolicy Bypass -File .\run.ps1 -Path .\sample.png -Format json
```

## Usage

Analyze a file and write a JSON report (default):

```bash
python main.py analyze path/to/photo.jpg --format json
```

Markdown report:

```bash
python main.py analyze path/to/song.mp3 --format md
```

Video example:

```bash
python main.py analyze path/to/clip.mp4 --format json
```

Write to a custom path:

```bash
python main.py analyze photo.jpg --format md --output ./my-report.md
```

The CLI auto-detects media type from extension and MIME type.

## What gets extracted

| Kind | Fields |
|------|--------|
| Image | File size, format, dimensions, color mode, EXIF (camera make/model, capture date, and remaining tags) |
| Audio | Duration, bitrate, sample rate, channels, tags (artist, album, title, and others) |
| Video | Container, duration, video stream (resolution, fps, codec), audio stream (codec, channels) |

Reports land in `outputs/` as `<filename>_<UTC-timestamp>.json` or `.md`.

## Project layout

```
multi-media_analyzer/
├── main.py                  # Typer CLI
├── requirements.txt
├── analyzers/
│   ├── image_parser.py      # Pillow / EXIF
│   ├── audio_parser.py      # mutagen
│   └── video_parser.py      # ffprobe
├── core/
│   ├── report_writer.py
│   └── utils.py
└── outputs/
```

## Error handling

Corrupt files, missing paths, unsupported types, and a missing `ffprobe` binary are reported with a red Rich panel. Full Python stack traces are not shown for these expected failures.

## License

Use and modify freely for personal or commercial projects.
