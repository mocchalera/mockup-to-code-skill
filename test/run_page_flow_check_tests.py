#!/usr/bin/env python3
"""Regression tests for Web-native multi-frame page-flow checks."""
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "test" / "work" / "page_flow"
SCRIPT = ROOT / "scripts" / "page_flow_check.py"
ONE_PX_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def base_manifest():
    sections = ["hero", "value", "cta"]
    return {
        "mode": "hybrid",
        "viewport": {"width": 1440, "height": 900},
        "image": "mockups/hero.png",
        "photoLed": False,
        "referenceImages": [
            {"path": f"mockups/{section}.png", "use": "section-comp", "section": section}
            for section in sections
        ],
        "pageComposition": {
            "referenceFrameHeight": 900,
            "sections": [
                {"section": "hero", "heightStrategy": "immersive", "density": "balanced", "overflowPolicy": "visible"},
                {"section": "value", "heightStrategy": "content-led", "density": "dense", "overflowPolicy": "bleed-to-next"},
                {"section": "cta", "heightStrategy": "breathing", "density": "airy", "overflowPolicy": "visible"},
            ],
            "seams": [
                {"from": "hero", "to": "value", "type": "color-handoff", "transitionSpacePx": 96, "evidencePath": "reports/crops/seam-hero-value.png"},
                {"from": "value", "to": "cta", "type": "breathing-space", "transitionSpacePx": 140, "evidencePath": "reports/crops/seam-value-cta.png"},
            ],
        },
        "elements": [
            {"id": section, "el": section, "role": "section", "bbox": {"x": 0, "y": 0, "w": 1440, "h": 900}, "priority": "high"}
            for section in sections
        ],
    }


def rects(heights):
    y = 0
    rows = []
    for section, height in zip(("hero", "value", "cta"), heights):
        rows.append({"el": section, "x": 0, "y": y, "w": 1440, "h": height})
        y += height
    return {"docHeight": y, "rects": rows}


def enable_art_directed_seam(manifest):
    seam = manifest["pageComposition"]["seams"][0]
    seam["type"] = "motif-bridge"
    seam["bridgeElements"] = ["hero", "value"]
    seam["continuity"] = {
        "required": True,
        "sourceRef": {"path": "reports/seam-source.txt", "quote": "seamless"},
        "surfaceOwner": "to-section",
        "geometryPrimitive": "bezier",
        "layers": ["outgoing-environment", "target-surface", "incoming-preview"],
        "previewTargets": ["value"],
        "desktopEvidencePath": "reports/crops/seam-hero-value.png",
        "mobileEvidencePath": "reports/crops/seam-hero-value-mobile.png",
        "colorSampleReport": "reports/crops/seam-hero-value-color.json",
    }
    return manifest


class PageFlowCheckTests(unittest.TestCase):
    def setUp(self):
        if WORK.exists():
            shutil.rmtree(WORK)
        (WORK / "reports" / "crops").mkdir(parents=True)
        for name in ("seam-hero-value.png", "seam-value-cta.png"):
            (WORK / "reports" / "crops" / name).write_bytes(ONE_PX_PNG)

    def run_check(self, manifest, rect_data, expected_code):
        write_json(WORK / "manifest.json", manifest)
        write_json(WORK / "reports" / "rects.json", rect_data)
        out = WORK / "reports" / "page-flow.json"
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(WORK / "manifest.json"), str(WORK / "reports" / "rects.json"), "--work-root", str(WORK), "--out", str(out)],
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_repeated_reference_heights_are_needs_work(self):
        report = self.run_check(base_manifest(), rects([900, 900, 900]), 1)
        self.assertEqual(report["status"], "needs_work")
        self.assertTrue(report["metrics"]["stackedFrameLock"])
        self.assertIn("stacked-frames", {item["id"] for item in report["checks"]})

    def test_old_manifest_without_page_composition_still_emits_fresh_report(self):
        manifest = base_manifest()
        manifest.pop("pageComposition")
        report = self.run_check(manifest, rects([900, 900, 900]), 1)
        self.assertEqual(report["status"], "needs_work")
        self.assertEqual(report["metrics"]["referenceFrameHeightSource"], "viewport-diagnostic-fallback")
        self.assertIn("reference-frame-height-missing", {item["id"] for item in report["checks"]})

    def test_varied_content_led_heights_and_seams_pass(self):
        report = self.run_check(base_manifest(), rects([900, 1180, 1040]), 0)
        self.assertEqual(report["status"], "pass")
        self.assertFalse(report["metrics"]["stackedFrameLock"])
        self.assertEqual(report["metrics"]["nonHardSeamCount"], 2)

    def test_uniform_non_reference_heights_are_still_needs_work(self):
        report = self.run_check(base_manifest(), rects([1080, 1080, 1080]), 1)
        self.assertTrue(report["metrics"]["stackedFrameLock"])
        self.assertFalse(report["metrics"]["referenceFrameLock"])

    def test_uniform_heights_require_verbatim_human_intent(self):
        manifest = base_manifest()
        manifest["pageComposition"]["uniformHeightIntent"] = {
            "reason": "The approved direction is a sequence of equal-height immersive chapters.",
            "userQuote": "全セクションを同じ高さの章として見せてください。",
        }
        report = self.run_check(manifest, rects([900, 900, 900]), 0)
        self.assertEqual(report["status"], "pass")
        self.assertIn("uniform-height-human-intent", {item["id"] for item in report["checks"]})

    def test_missing_seam_evidence_is_needs_work(self):
        (WORK / "reports" / "crops" / "seam-value-cta.png").unlink()
        report = self.run_check(base_manifest(), rects([900, 1180, 1040]), 1)
        self.assertIn("seam-evidence-missing", {item["id"] for item in report["checks"]})

    def test_seam_evidence_must_be_a_readable_image(self):
        (WORK / "reports" / "crops" / "seam-value-cta.png").write_text("not an image", encoding="utf-8")
        report = self.run_check(base_manifest(), rects([900, 1180, 1040]), 1)
        self.assertIn("seam-evidence-missing", {item["id"] for item in report["checks"]})

    def test_all_sections_clipped_needs_human_intent(self):
        manifest = base_manifest()
        for spec in manifest["pageComposition"]["sections"]:
            spec["overflowPolicy"] = "clip"
            spec["clipReason"] = "Rounded chapter frame"
        report = self.run_check(manifest, rects([900, 1180, 1040]), 1)
        self.assertIn("all-sections-clipped", {item["id"] for item in report["checks"]})

    def test_seam_requires_a_transition_type(self):
        manifest = base_manifest()
        manifest["pageComposition"]["seams"][0].pop("type")
        report = self.run_check(manifest, rects([900, 1180, 1040]), 1)
        self.assertIn("seam-strategy-incomplete", {item["id"] for item in report["checks"]})

    def test_art_directed_seam_requires_desktop_mobile_and_pixel_proof(self):
        manifest = enable_art_directed_seam(base_manifest())

        report = self.run_check(manifest, rects([900, 1180, 1040]), 1)

        check = next(item for item in report["checks"] if item["id"] == "art-directed-seam-evidence")
        self.assertEqual(check["status"], "needs_work")
        self.assertTrue(any("mobileEvidencePath" in value for value in check["failures"]))
        self.assertTrue(any("colorSampleReport" in value for value in check["failures"]))

    def test_art_directed_seam_passes_with_image_bound_color_report(self):
        manifest = enable_art_directed_seam(base_manifest())
        desktop = WORK / "reports" / "crops" / "seam-hero-value.png"
        mobile = WORK / "reports" / "crops" / "seam-hero-value-mobile.png"
        mobile.write_bytes(ONE_PX_PNG)
        write_json(WORK / "reports" / "crops" / "seam-hero-value-color.json", {
            "schemaVersion": "seam-pixel-check/v1",
            "status": "pass",
            "from": "hero",
            "to": "value",
            "imagePath": "reports/crops/seam-hero-value.png",
            "imageSha256": hashlib.sha256(desktop.read_bytes()).hexdigest(),
            "expectedHex": "#fcfbf4",
            "tolerance": 1,
            "maxChannelDelta": 0,
            "samples": [
                {"role": "bridge-fill", "status": "pass"},
                {"role": "next-surface", "status": "pass"},
            ],
        })

        report = self.run_check(manifest, rects([900, 1180, 1040]), 0)

        check = next(item for item in report["checks"] if item["id"] == "art-directed-seam-evidence")
        self.assertEqual(check["status"], "pass")


if __name__ == "__main__":
    unittest.main()
