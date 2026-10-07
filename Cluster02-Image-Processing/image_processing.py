"""Run common image transforms and save the results as PNG files."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    import cv2
    import numpy as np
    from PIL import Image, ImageFilter, ImageOps
    from multimedia.cli import processing_cli
    from multimedia.common import MediaError, output_directory, validate_file
    from multimedia.metadata import image_metadata
except ImportError as exc:
    raise SystemExit(f"Missing dependency: {exc}. Run: python -m pip install -r requirements.txt")


def process_image(file_name, destination):
    path = validate_file(file_name)
    image_metadata(path)
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except OSError as exc:
        raise MediaError(f"Could not decode image '{path.name}': {exc}") from exc

    gray = ImageOps.grayscale(image)
    results = {
        "grayscale": gray,
        "resize_half": image.resize(
            (max(1, image.width // 2), max(1, image.height // 2)),
            Image.Resampling.LANCZOS,
        ),
        "threshold": gray.point(lambda value: 255 if value >= 128 else 0),
        "gaussian_blur": image.filter(ImageFilter.GaussianBlur(radius=2)),
        "canny_edges": Image.fromarray(cv2.Canny(np.asarray(gray), 100, 200)),
        "rotate_clockwise": image.transpose(Image.Transpose.ROTATE_270),
    }
    directory = output_directory(destination)
    paths = []
    for name, result in results.items():
        output = directory / f"{name}.png"
        result.save(output, format="PNG")
        paths.append(output)
    return paths


if __name__ == "__main__":
    raise SystemExit(processing_cli(process_image, "Image processing", "outputs/images"))
