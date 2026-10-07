"""Image enhancement and multilingual OCR pipeline powered by Pillow and Tesseract."""

from __future__ import annotations

import argparse
import html
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError


IMAGE_SUFFIXES = {".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


@dataclass
class ImageResult:
    source: str
    enhanced_image: str | None
    width: int | None
    height: int | None
    deskew_angle: float | None
    language: str
    text: str
    status: str
    error: str | None = None


def _foreground_projection_score(image: Image.Image) -> float:
    """Score row alignment for a small grayscale document image."""
    pixels = image.load()
    width, height = image.size
    row_counts = []
    foreground = 0
    for y in range(height):
        count = sum(1 for x in range(width) if pixels[x, y] < 180)
        row_counts.append(count)
        foreground += count

    ratio = foreground / max(width * height, 1)
    if ratio < 0.002 or ratio > 0.55:
        return 0.0

    mean = sum(row_counts) / max(height, 1)
    variance = sum((count - mean) ** 2 for count in row_counts) / max(height, 1)
    return variance


def estimate_skew(image: Image.Image) -> float:
    """Estimate a small text-line rotation; return zero for low-confidence cases."""
    probe = ImageOps.grayscale(image)
    probe.thumbnail((900, 900), Image.Resampling.LANCZOS)
    if min(probe.size) < 32:
        return 0.0

    baseline = _foreground_projection_score(probe)
    if baseline <= 0:
        return 0.0

    best_angle = 0.0
    best_score = baseline
    # A coarse-to-fine projection search is fast at the reduced probe size.
    for angle in (step / 2 for step in range(-10, 11)):
        if angle == 0:
            continue
        rotated = probe.rotate(
            angle,
            resample=Image.Resampling.BILINEAR,
            expand=False,
            fillcolor=255,
        )
        score = _foreground_projection_score(rotated)
        if score > best_score:
            best_score, best_angle = score, angle

    if best_angle:
        center = best_angle
        for step in range(-4, 5):
            angle = center + step * 0.1
            rotated = probe.rotate(
                angle,
                resample=Image.Resampling.BILINEAR,
                expand=False,
                fillcolor=255,
            )
            score = _foreground_projection_score(rotated)
            if score > best_score:
                best_score, best_angle = score, angle

    if best_score < baseline * 1.025 or abs(best_angle) < 0.35:
        return 0.0
    return best_angle


def enhance_image(image: Image.Image) -> tuple[Image.Image, float]:
    """Normalize contrast, deskew, upscale small text, and sharpen for OCR."""
    enhanced = ImageOps.grayscale(ImageOps.exif_transpose(image))
    enhanced = ImageOps.autocontrast(enhanced, cutoff=1)
    angle = estimate_skew(enhanced)
    if angle:
        enhanced = enhanced.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=True,
            fillcolor=255,
        )

    largest = max(enhanced.size)
    if largest < 1800:
        scale = min(2.0, 1800 / max(largest, 1))
        enhanced = enhanced.resize(
            (max(1, round(enhanced.width * scale)), max(1, round(enhanced.height * scale))),
            Image.Resampling.LANCZOS,
        )
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.15)
    enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=1.2, percent=125, threshold=3))
    return enhanced, angle


def _iter_images(source: Path) -> Iterable[Path]:
    if source.is_file():
        yield source
        return
    yield from sorted(
        path for path in source.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def _relative_path(path: Path, source: Path) -> Path:
    if source.is_dir():
        return path.relative_to(source)
    return Path(path.name)


def process_image(
    path: Path,
    source: Path,
    output_dir: Path,
    language: str = "eng",
    psm: int = 3,
    run_ocr: bool = True,
) -> ImageResult:
    relative = _relative_path(path, source)
    output_stem = relative.stem
    if relative.suffix:
        output_stem = f"{output_stem}_{relative.suffix[1:].lower()}"
    enhanced_relative = Path("enhanced") / relative.with_name(f"{output_stem}.png")
    report_relative = Path("reports") / relative.with_name(f"{output_stem}.json")
    enhanced_path = output_dir / enhanced_relative
    report_path = output_dir / report_relative

    try:
        with Image.open(path) as opened:
            opened.seek(0)
            prepared, angle = enhance_image(opened.copy())
        enhanced_path.parent.mkdir(parents=True, exist_ok=True)
        prepared.save(enhanced_path, format="PNG", optimize=True)

        text = ""
        status = "enhanced"
        error = None
        if run_ocr:
            try:
                import pytesseract

                text = pytesseract.image_to_string(
                    prepared,
                    lang=language,
                    config=f"--psm {psm}",
                ).strip()
                status = "ok"
            except ImportError:
                status = "ocr_error"
                error = "pytesseract is not installed; install dependencies from requirements.txt."
            except Exception as exc:  # Tesseract binary/data errors are expected runtime conditions.
                status = "ocr_error"
                error = str(exc)

        result = ImageResult(
            source=str(path.resolve()),
            enhanced_image=str(enhanced_relative),
            width=prepared.width,
            height=prepared.height,
            deskew_angle=round(angle, 2),
            language=language,
            text=text,
            status=status,
            error=error,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        result = ImageResult(
            source=str(path.resolve()),
            enhanced_image=None,
            width=None,
            height=None,
            deskew_angle=None,
            language=language,
            text="",
            status="image_error",
            error=str(exc),
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
        return result


def write_html_report(results: list[ImageResult], output_dir: Path, language: str) -> Path:
    report_path = output_dir / "reports" / "results.html"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    cards = []
    for result in results:
        name = html.escape(Path(result.source).name)
        image_link = ""
        if result.enhanced_image:
            relative_link = "../" + result.enhanced_image.replace("\\", "/")
            image_link = (
                f'<a href="{html.escape(relative_link, quote=True)}">'
                f'<img src="{html.escape(relative_link, quote=True)}" alt="Enhanced {name}"></a>'
            )
        error = f'<p class="error">{html.escape(result.error)}</p>' if result.error else ""
        cards.append(
            "<article>"
            f"<h2>{name}</h2><p>Status: <strong>{html.escape(result.status)}</strong>"
            f" · Deskew: {result.deskew_angle if result.deskew_angle is not None else 'n/a'}°</p>"
            f"{image_link}{error}<pre>{html.escape(result.text or '(No recognized text)')}</pre>"
            "</article>"
        )
    generated = datetime.now(timezone.utc).isoformat()
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OCR results</title><style>
body{{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#202124}}
article{{border:1px solid #ddd;border-radius:8px;padding:1rem;margin:1rem 0}}
img{{max-width:100%;max-height:360px;object-fit:contain;background:#eee}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f5;padding:1rem}}
.error{{color:#a00}}small{{color:#555}}
</style></head><body><h1>Multilingual OCR results</h1>
<p>Language: {html.escape(language)} · Images: {len(results)} · Generated: {html.escape(generated)}</p>
{''.join(cards)}
</body></html>"""
    report_path.write_text(document, encoding="utf-8")
    return report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enhance, deskew, and OCR one image or a directory of images with Tesseract."
    )
    parser.add_argument("path", type=Path, help="Image file or directory (searched recursively).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output root (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--lang",
        default="eng",
        help="Tesseract language code(s), e.g. eng, hin, or eng+fra (traineddata must be installed).",
    )
    parser.add_argument("--psm", type=int, default=3, choices=range(0, 14), help="Tesseract page segmentation mode (0-13).")
    parser.add_argument("--no-ocr", action="store_true", help="Only enhance images; skip Tesseract OCR.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = args.path.expanduser().resolve()
    if not source.exists():
        print(f"Input does not exist: {source}", file=sys.stderr)
        return 2
    if not source.is_file() and not source.is_dir():
        print(f"Input is not a file or directory: {source}", file=sys.stderr)
        return 2
    images = list(_iter_images(source))
    if source.is_dir():
        output_root = args.output_dir.expanduser().resolve()
        if output_root == source:
            images = [
                path for path in images
                if path.relative_to(source).parts[0] not in {"enhanced", "reports"}
            ]
        else:
            images = [path for path in images if not path.is_relative_to(output_root)]
    if not images:
        print(f"No supported images found in: {source}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = [
        process_image(path, source, args.output_dir, args.lang, args.psm, not args.no_ocr)
        for path in images
    ]
    html_path = write_html_report(results, args.output_dir, args.lang)
    success_count = sum(result.status in {"ok", "enhanced"} for result in results)
    ocr_failures = sum(result.status == "ocr_error" for result in results)
    image_failures = sum(result.status == "image_error" for result in results)
    print(f"Processed {len(results)} image(s): {success_count} successful, {ocr_failures} OCR error(s), {image_failures} image error(s).")
    print(f"HTML report: {html_path}")
    if ocr_failures:
        print("Check Tesseract installation and requested language data; see the README.", file=sys.stderr)
    return 1 if ocr_failures or image_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
