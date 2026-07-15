#!/usr/bin/env python3
"""Regression tests for masked pixel-diff comparison coverage."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def cv2_python() -> str | None:
    candidates = [sys.executable, "/usr/local/bin/python3"]
    for candidate in candidates:
        if not Path(candidate).exists():
            continue
        probe = subprocess.run(
            [candidate, "-c", "import cv2, numpy"],
            text=True,
            capture_output=True,
        )
        if probe.returncode == 0:
            return candidate
    return None


class PixelDiffCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.python = cv2_python()
        if not cls.python:
            raise unittest.SkipTest("no Python interpreter with cv2 + numpy")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pixel-diff-coverage-"))
        self.mockup = self.tmp / "mockup.png"
        self.rendered = self.tmp / "rendered.png"
        subprocess.run(
            [
                self.python,
                "-c",
                (
                    "import cv2,numpy as np,sys; "
                    "im=np.zeros((100,100,3),dtype=np.uint8); "
                    "cv2.imwrite(sys.argv[1],im); cv2.imwrite(sys.argv[2],im)"
                ),
                str(self.mockup),
                str(self.rendered),
            ],
            check=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_diff(self, *extra: str) -> dict:
        report = self.tmp / "report.json"
        proc = subprocess.run(
            [
                self.python,
                "scripts/pixel_diff.py",
                str(self.mockup),
                str(self.rendered),
                "--out",
                str(report),
                *extra,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return json.loads(report.read_text(encoding="utf-8"))

    def test_low_coverage_cannot_be_good_even_when_compared_pixels_match(self):
        report = self.run_diff("--mask", "0,0,88,100")
        self.assertEqual(report["diff_ratio"], 0)
        self.assertAlmostEqual(report["comparison_coverage"], 0.12, places=2)
        self.assertFalse(report["coverage_sufficient"])
        self.assertEqual(report["pixel_verdict"], "good")
        self.assertEqual(report["verdict"], "insufficient_coverage")

    def test_hybrid_default_accepts_twenty_percent_or_more(self):
        report = self.run_diff("--mask", "0,0,75,100")
        self.assertAlmostEqual(report["comparison_coverage"], 0.25, places=2)
        self.assertTrue(report["coverage_sufficient"])
        self.assertEqual(report["verdict"], "good")

    def test_pixel_clone_uses_stricter_default_coverage(self):
        manifest = self.tmp / "manifest.json"
        manifest.write_text(json.dumps({"mode": "pixel-clone", "elements": []}), encoding="utf-8")
        report = self.run_diff("--manifest", str(manifest), "--mask", "0,0,60,100")
        self.assertAlmostEqual(report["comparison_coverage"], 0.40, places=2)
        self.assertEqual(report["min_comparison_coverage"], 0.50)
        self.assertEqual(report["verdict"], "insufficient_coverage")

    def test_hybrid_generated_photo_uses_remaining_eligible_pixels(self):
        manifest = self.tmp / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "mode": "hybrid",
                    "image": str(self.mockup),
                    "elements": [
                        {
                            "id": "hero.photo",
                            "mediaClass": "photo",
                            "assetStrategy": "generated",
                            "sourceImage": str(self.mockup),
                            "bbox": {"x": 0, "y": 0, "w": 60, "h": 100},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        report = self.run_diff("--manifest", str(manifest))

        self.assertAlmostEqual(report["generated_media_coverage"], 0.60, places=2)
        self.assertAlmostEqual(report["comparison_coverage"], 0.40, places=2)
        self.assertAlmostEqual(report["eligible_comparison_coverage"], 1.0, places=2)
        self.assertTrue(report["coverage_sufficient"])
        self.assertEqual(report["verdict"], "good")
        self.assertEqual(report["auto_generated_media_masks"], ["hero.photo"])

    def test_full_frame_generated_photo_reports_explicit_not_applicable(self):
        manifest = self.tmp / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "mode": "hybrid",
                    "image": str(self.mockup),
                    "elements": [
                        {
                            "id": "hero.photo",
                            "mediaClass": "photo",
                            "assetStrategy": "generated",
                            "sourceImage": str(self.mockup),
                            "bbox": {"x": 0, "y": 0, "w": 100, "h": 100},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        report = self.run_diff("--manifest", str(manifest))

        self.assertEqual(report["comparison_coverage"], 0)
        self.assertEqual(report["eligible_non_generated_media_px"], 0)
        self.assertFalse(report["pixel_evidence_applicable"])
        self.assertEqual(report["pixel_verdict"], "not_applicable")
        self.assertEqual(report["verdict"], "not_applicable_generated_media")

    def test_opaque_foreground_is_reincluded_after_full_frame_generated_mask(self):
        manifest = self.tmp / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "mode": "hybrid",
                    "image": str(self.mockup),
                    "elements": [
                        {
                            "id": "hero.photo",
                            "mediaClass": "photo",
                            "assetStrategy": "generated",
                            "sourceImage": str(self.mockup),
                            "bbox": {"x": 0, "y": 0, "w": 100, "h": 100},
                        },
                        {
                            "id": "hero.cta",
                            "pixelDiffForeground": True,
                            "bbox": {"x": 10, "y": 20, "w": 30, "h": 20},
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        report = self.run_diff("--manifest", str(manifest))

        self.assertEqual(report["foreground_reincluded_px"], 600)
        self.assertEqual(report["auto_foreground_carveouts"], ["hero.cta"])
        self.assertEqual(report["eligible_non_generated_media_px"], 600)
        self.assertTrue(report["pixel_evidence_applicable"])
        self.assertEqual(report["verdict"], "good")


if __name__ == "__main__":
    unittest.main()
