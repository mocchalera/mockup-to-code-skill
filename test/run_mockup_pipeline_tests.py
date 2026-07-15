#!/usr/bin/env python3
"""Regression tests for the unified mockup-to-code pipeline runner."""
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MockupPipelineTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="mockup-pipeline-")) / "run"

    def tearDown(self):
        shutil.rmtree(self.work.parent)

    def run_phase(self, phase, expected):
        proc = subprocess.run(
            [sys.executable, "scripts/mockup_pipeline.py", str(self.work), "--phase", phase],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        summary = json.loads((self.work / "reports" / "pipeline-summary.json").read_text(encoding="utf-8"))
        return summary

    def test_init_copies_machine_shaped_starters(self):
        summary = self.run_phase("init", 0)
        self.assertEqual(summary["status"], "pass")
        self.assertTrue((self.work / "manifest.json").is_file())
        self.assertTrue((self.work / "reports" / "section-scores.json").is_file())
        manifest = json.loads((self.work / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["reviewPolicy"]["independentReviewRequired"])
        self.assertGreaterEqual(len(manifest["detailInventory"]), 2)

    def test_init_refuses_to_overwrite_existing_run(self):
        self.run_phase("init", 0)
        original = (self.work / "manifest.json").read_bytes()
        summary = self.run_phase("init", 2)
        self.assertEqual(summary["status"], "blocked")
        self.assertEqual((self.work / "manifest.json").read_bytes(), original)

    def test_next_blocks_below_fv_scope_until_fv_boxes_pass(self):
        self.run_phase("init", 0)
        manifest = json.loads((self.work / "manifest.json").read_text(encoding="utf-8"))
        data = (self.work / "manifest.json").read_bytes()
        receipt = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        asset_receipts = []
        for element in manifest["elements"]:
            payload_name = {"generated": "generatedAsset", "replace": "replacedAsset", "crop-asset": "croppedAsset"}.get(element.get("assetStrategy"))
            payload = element.get(payload_name, {}) if payload_name else {}
            relative = payload.get("workspacePath")
            if not relative:
                continue
            path = self.work / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"adopted raster")
            asset_receipts.append({
                "elementId": element["id"],
                "path": relative,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size": path.stat().st_size,
            })
        (self.work / "reports" / "contract-doctor.json").write_text(
            json.dumps({"status": "pass", "inputs": {"manifest": receipt}}), encoding="utf-8"
        )
        (self.work / "reports" / "asset-preflight.json").write_text(
            json.dumps({"status": "pass", "implementationAllowed": True, "inputs": {"manifest": receipt, "assets": asset_receipts}}), encoding="utf-8"
        )
        fv_ids = [row["id"] for row in manifest["elements"] if row.get("qaPriority") == "fv-critical"]
        (self.work / "reports" / "box-report.json").write_text(
            json.dumps({
                "items": [{"id": item_id, "pass": False} for item_id in fv_ids],
                "first_fix": {"id": fv_ids[0]},
            }),
            encoding="utf-8",
        )
        below = next(row for row in manifest["elements"] if row.get("qaPriority") == "section-critical")
        (self.work / "site" / "index.html").write_text(
            f'<section data-el="{below["el"]}"></section>', encoding="utf-8"
        )

        summary = self.run_phase("next", 1)

        step = summary["steps"][0]
        self.assertEqual(step["allowedAction"], "repair-first-failing-fv-element")
        self.assertEqual(step["completionCeiling"], "prototype")
        self.assertIn(below["id"], step["prematureBelowFvDomIds"])

    def test_next_rejects_asset_preflight_after_adopted_raster_changes(self):
        self.run_phase("init", 0)
        manifest = json.loads((self.work / "manifest.json").read_text(encoding="utf-8"))
        data = (self.work / "manifest.json").read_bytes()
        receipt = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        element = next(row for row in manifest["elements"] if row.get("assetStrategy") == "generated")
        relative = element["generatedAsset"]["workspacePath"]
        asset = self.work / relative
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"approved raster")
        asset_receipt = {
            "elementId": element["id"],
            "path": relative,
            "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            "size": asset.stat().st_size,
        }
        (self.work / "reports" / "contract-doctor.json").write_text(
            json.dumps({"status": "pass", "inputs": {"manifest": receipt}}), encoding="utf-8"
        )
        (self.work / "reports" / "asset-preflight.json").write_text(
            json.dumps({"status": "pass", "implementationAllowed": True, "inputs": {"manifest": receipt, "assets": [asset_receipt]}}), encoding="utf-8"
        )
        asset.write_bytes(b"changed after preflight")

        summary = self.run_phase("next", 1)

        self.assertEqual(summary["steps"][0]["allowedAction"], "run-pre-css")
        self.assertTrue(summary["steps"][0]["staleEvidence"]["assetFiles"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
