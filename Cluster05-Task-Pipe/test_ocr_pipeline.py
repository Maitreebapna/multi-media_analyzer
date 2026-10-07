"""Focused tests for OCR image preprocessing and HTML report safety."""

from __future__ import annotations

import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from ocr_pipeline import ImageResult, enhance_image, estimate_skew, write_html_report


class OcrPipelineTests(unittest.TestCase):
    def test_enhancement_converts_and_upscales_small_image(self) -> None:
        image = Image.new("RGB", (320, 180), "white")
        ImageDraw.Draw(image).text((20, 60), "OCR 123", fill="black")

        enhanced, angle = enhance_image(image)

        self.assertEqual(enhanced.mode, "L")
        self.assertGreater(enhanced.width, image.width)
        self.assertGreater(enhanced.height, image.height)
        self.assertIsInstance(angle, float)

    def test_blank_image_has_no_detectable_skew(self) -> None:
        self.assertEqual(estimate_skew(Image.new("L", (300, 100), "white")), 0.0)

    def test_projection_search_estimates_small_rotation(self) -> None:
        page = Image.new("L", (500, 240), "white")
        draw = ImageDraw.Draw(page)
        for y in range(35, 210, 25):
            draw.rectangle((45, y, 450, y + 7), fill="black")

        skewed = page.rotate(3, resample=Image.Resampling.BICUBIC, fillcolor="white")

        self.assertAlmostEqual(estimate_skew(skewed), -3.0, delta=0.6)

    def test_html_report_escapes_text_and_links_enhanced_image(self) -> None:
        output = Path(__file__).resolve().parent / "test-output"
        result = ImageResult(
            source=r"C:\input\<script>.png",
            enhanced_image=r"enhanced\<script>.png",
            width=100,
            height=100,
            deskew_angle=0.0,
            language="eng",
            text="<script>alert(1)</script>",
            status="ok",
        )
        try:
            report = write_html_report([result], output, "eng")
            contents = report.read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;", contents)
            self.assertNotIn("<script>alert", contents)
            self.assertIn("../enhanced/&lt;script&gt;.png", contents)
        finally:
            report_dir = output / "reports"
            if report_dir.exists():
                for file in report_dir.iterdir():
                    file.unlink()
                report_dir.rmdir()
            if output.exists():
                output.rmdir()


if __name__ == "__main__":
    unittest.main()
