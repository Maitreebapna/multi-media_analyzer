"""Standalone image metadata command."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    from multimedia.cli import metadata_cli
    from multimedia.metadata import image_metadata
except ImportError as exc:
    raise SystemExit(f"Missing dependency: {exc}. Run: python -m pip install -r requirements.txt")


if __name__ == "__main__":
    raise SystemExit(metadata_cli(image_metadata, "image metadata", standalone=True))
