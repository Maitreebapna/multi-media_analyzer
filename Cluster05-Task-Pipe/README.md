# Cluster 05 — Multilingual OCR image enhancement

A standalone Python CLI that prepares scanned/document images for recognition, estimates and corrects small text skew, runs multilingual OCR through Tesseract, and creates per-image JSON reports plus an HTML results page. It uses Pillow for image processing and does not call an external API.

## Requirements

- Python 3.10+
- Install the workspace dependencies: `pip install -r requirements.txt`
- Install the **Tesseract OCR engine** separately and make `tesseract` available on `PATH`.
- Install Tesseract trained data for every requested language. The default `eng` needs English data; multiple languages can be selected with `--lang eng+fra`, for example.

The Python `pytesseract` package is only a bridge to the local Tesseract executable; recognition and language data are not bundled with this project. If the executable or language data is missing, enhancement still runs and the error is recorded in each JSON/HTML result.

## Usage

From the workspace root:

```powershell
python .\Cluster05-Task-Pipe\ocr_pipeline.py .\scan.jpg
python .\Cluster05-Task-Pipe\ocr_pipeline.py .\scans --lang eng+hin --output-dir .\ocr-results
python .\Cluster05-Task-Pipe\ocr_pipeline.py .\scan.png --no-ocr
```

A directory is searched recursively for BMP, GIF, JPEG, PNG, TIFF, and WebP images. Animated files are processed using their first frame. OCR language codes and page-segmentation modes are passed to Tesseract.

By default, results are written under `Cluster05-Task-Pipe/outputs/`:

```text
outputs/
├── enhanced/        # Contrast-adjusted, deskewed, upscaled PNGs
└── reports/
    ├── <image>_<ext>.json # OCR text, language, dimensions, deskew estimate, status
    └── results.html # Linked image previews and recognized text
```

Use `--output-dir` to select another output root. Output assets are named `<image-stem>_<source-extension>.png/.json` to avoid collisions between images with the same stem and different formats. For a directory input, its relative subdirectory structure is retained in both output folders. Expected unreadable-image/OCR failures are saved in reports; the command exits nonzero if any occur.

## Tests

Run focused tests with:

```powershell
python -m unittest discover -s .\Cluster05-Task-Pipe -p "test_*.py"
```
