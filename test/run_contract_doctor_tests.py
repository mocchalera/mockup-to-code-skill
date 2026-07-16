#!/usr/bin/env python3
"""Regression tests for the pre-CSS/completion contract doctor."""
import json
import hashlib
import shutil
import struct
import subprocess
import sys
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "test" / "work" / "contract_doctor"
TEMPLATE = ROOT / "templates" / "manifest.hybrid-multiframe.min.json"
sys.path.insert(0, str(ROOT / "scripts"))
from contract_doctor import (
    validate_typography_composition,
    validate_typography_font_selection,
    validate_typography_impression,
)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_rgb_png(path, width=32, height=24, color=(238, 232, 218)):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class ContractDoctorTests(unittest.TestCase):
    def setUp(self):
        self.work = WORK_ROOT / self._testMethodName
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)

    def manifest(self):
        return read_json(TEMPLATE)

    def materialize_asset_evidence(self):
        files = (
            "mockups/section-01-hero.png",
            "mockups/section-02-value.png",
            "assets/hero-bg.png",
            "reports/photo-asset-review.md",
            "reports/crops/hero-photo-asset-pair.png",
            "reports/crops/hero-photo-source-2x.png",
            "reports/crops/hero-lockup-source-2x.png",
            "reports/crops/font-bakeoff-a.png",
            "reports/crops/font-bakeoff-b.png",
            "reports/crops/font-fallback-hero-heading.png",
            "reports/crops/font-fallback-cta-label.png",
        )
        for value in files:
            path = self.work / value
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"evidence")
        (self.work / "reports" / "hypotheses.md").write_text(
            "Measured ownership, type, asset, and detail inventory for this fixture.\n",
            encoding="utf-8",
        )
        manifest_path = self.work / "manifest.json"
        manifest = read_json(manifest_path)
        photo = next((row for row in manifest.get("elements", []) if row.get("id") == "hero.photo"), None)
        generated = (photo or {}).get("generatedAsset")
        if isinstance(generated, dict) and isinstance(generated.get("prompt"), str):
            prompt_path = self.work / "reports" / "prompts" / "hero-photo.txt"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(generated["prompt"], encoding="utf-8")
            generated["promptRef"] = {
                "path": "reports/prompts/hero-photo.txt",
                "sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
                "kind": "exact-prompt",
            }
            source_path = self.work / "mockups" / "section-01-hero.png"
            generated["inputRefs"] = [
                {
                    "path": "mockups/section-01-hero.png",
                    "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                    "role": "composition-reference",
                    "includedInGeneration": False,
                }
            ]
            write_json(manifest_path, manifest)
            # Prompt receipts predate the adopted generator output. This is the
            # only chronology that proves the prompt was fixed before generation.
            asset_path = self.work / "assets" / "hero-bg.png"
            write_rgb_png(asset_path)
            receipt_path = self.work / "reports" / "prompts" / "hero-photo.receipt.json"
            receipt = {
                "schemaVersion": "prompt-generation-receipt/v1",
                "status": "adopted",
                "generator": generated.get("generator"),
                "issuedAt": "2026-01-01T00:00:00Z",
                "adoptedAt": "2026-01-01T00:00:01Z",
                "prompt": {
                    "path": str(prompt_path),
                    "sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
                    "size": prompt_path.stat().st_size,
                },
                "asset": {
                    "path": str(asset_path),
                    "sha256": hashlib.sha256(asset_path.read_bytes()).hexdigest(),
                    "size": asset_path.stat().st_size,
                },
            }
            write_json(receipt_path, receipt)
            generated["generationReceipt"] = {
                "path": "reports/prompts/hero-photo.receipt.json",
                "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            }
            write_json(manifest_path, manifest)
        manifest = read_json(manifest_path)
        specialist_reports = manifest.setdefault("specialistReports", {})
        inventory_report = {
            "schemaVersion": "detail-inventory/v1",
            "status": {"state": "complete", "blockers": []},
            "devices": [
                {"id": row["id"]}
                for row in manifest.get("detailInventory", [])
                if isinstance(row, dict) and row.get("id")
            ],
        }
        inventory_path = self.work / "reports" / "detail-inventory.json"
        write_json(inventory_path, inventory_report)
        specialist_reports["deviceInventory"] = {
            "contract": "detail-inventory/v1",
            "path": "reports/detail-inventory.json",
            "sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        }
        photo_report = {
            "schemaVersion": "photo-art-direction/v1",
            "status": "adopted",
        }
        photo_path = self.work / "reports" / "photo-art-direction.json"
        write_json(photo_path, photo_report)
        specialist_reports["photoArtDirection"] = {
            "contract": "photo-art-direction/v1",
            "path": "reports/photo-art-direction.json",
            "sha256": hashlib.sha256(photo_path.read_bytes()).hexdigest(),
        }
        write_json(manifest_path, manifest)

    def run_doctor(self, expected_code, phase="pre-css"):
        out = self.work / "reports" / "contract-doctor.json"
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/contract_doctor.py",
                str(self.work),
                "--phase",
                phase,
                "--out",
                str(out),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
        self.assertTrue(out.is_file(), proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        return read_json(out), proc

    def write_manifest(self, manifest):
        write_json(self.work / "manifest.json", manifest)

    def enable_art_directed_seam(self, manifest):
        seam = manifest["pageComposition"]["seams"][0]
        seam["type"] = "motif-bridge"
        seam["bridgeElements"] = ["hero.heading", "hero.cta"]
        seam["continuity"] = {
            "required": True,
            "sourceRef": {
                "path": "reports/seam-source.txt",
                "quote": "シームレスにスクロールしたくなる",
            },
            "surfaceOwner": "to-section",
            "geometryPrimitive": "bezier",
            "layers": [
                "outgoing-environment",
                "target-surface",
                "connective-motif",
                "incoming-preview",
            ],
            "previewTargets": ["hero.heading"],
            "cueTarget": "hero.cta",
            "desktopEvidencePath": "reports/seams/hero-value.png",
            "mobileEvidencePath": "reports/seams/hero-value-mobile.png",
            "colorSampleReport": "reports/seams/hero-value-color.json",
        }
        return manifest

    def test_typography_impression_blocks_missing_or_timid_source_geometry(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row.get("role") == "heading")
        heading["typeSpec"].pop("sourceImpression")
        checks = []
        validate_typography_impression(manifest, checks)
        self.assertIn("typography-source-impression", {row["id"] for row in checks})

        fresh_heading = next(row for row in self.manifest()["elements"] if row.get("role") == "heading")
        heading["typeSpec"]["sourceImpression"] = fresh_heading["typeSpec"]["sourceImpression"]
        heading["typeSpec"]["sourceImpression"]["sourceBlockWidthRatio"] = 0.12
        checks = []
        validate_typography_impression(manifest, checks)
        issue = next(row for row in checks if row["id"] == "typography-source-impression")
        self.assertIn("disagrees", json.dumps(issue))

    def test_typography_impression_blocks_generic_spec_copied_across_three_frames(self):
        base = self.manifest()
        heading = next(row for row in base["elements"] if row.get("role") == "heading")
        manifest = {
            "mode": "hybrid",
            "referenceImages": [
                {"path": f"mockups/s0{index}.png", "use": "section-comp", "section": f"s0{index}"}
                for index in range(1, 4)
            ],
            "elements": [],
        }
        for index in range(1, 4):
            row = json.loads(json.dumps(heading))
            row["id"] = f"s0{index}.heading"
            row["el"] = f"s0{index}-heading"
            row["sourceImage"] = f"mockups/s0{index}.png"
            manifest["elements"].append(row)
        checks = []
        validate_typography_impression(manifest, checks)
        self.assertIn("typography-template-copy-risk", {row["id"] for row in checks})

    def test_typography_font_selection_blocks_system_only_or_unavailable_weight(self):
        manifest = self.manifest()
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        manifest = read_json(self.work / "manifest.json")
        heading = next(row for row in manifest["elements"] if row.get("id") == "hero.heading")
        selection = heading["typeSpec"]["fontSelection"]
        selection["selectedFamily"] = "Arial"
        selection["selectedSource"] = "system"
        selection["requestedWeight"] = 850
        selection["availableWeights"] = [400, 700]
        selection["delivery"]["strategy"] = "system"
        selection["candidates"] = [
            {"family": "Arial", "source": "system", "weight": 700, "evidencePath": "reports/crops/font-bakeoff-a.png"},
            {"family": "Helvetica", "source": "system", "weight": 700, "evidencePath": "reports/crops/font-bakeoff-b.png"},
        ]
        heading["text"]["fontFamily"] = "Arial"
        checks = []
        validate_typography_font_selection(manifest, self.work, checks)
        issue = next(row for row in checks if row["id"] == "typography-font-selection")
        serialized = json.dumps(issue)
        self.assertIn("non-system", serialized)
        self.assertIn("requestedWeight", serialized)
        self.assertIn("systemFontException", serialized)

    def test_typography_composition_blocks_flat_or_incomplete_role_graph(self):
        manifest = self.manifest()
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        manifest = read_json(self.work / "manifest.json")
        composition = manifest["typographyComposition"][0]
        composition["hierarchyEdges"] = []
        composition["whitespaceEdges"] = []
        composition["extremeScale"]["maxScaleLossRatio"] = 0.7
        checks = []
        validate_typography_composition(manifest, self.work, checks)
        issue = next(row for row in checks if row["id"] == "typography-composition")
        serialized = json.dumps(issue)
        self.assertIn("hierarchyEdges", serialized)
        self.assertIn("whitespaceEdges", serialized)
        self.assertIn("maxScaleLossRatio", serialized)

    def materialize_seam_continuity_report(self, status="ready"):
        source = self.work / "reports" / "seam-source.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("シームレスにスクロールしたくなる", encoding="utf-8")
        report_path = self.work / "reports" / "seam-continuity.json"
        write_json(report_path, {
            "schemaVersion": "seam-continuity/v1",
            "status": status,
            "sourceRef": {
                "path": "reports/seam-source.txt",
                "quote": "シームレスにスクロールしたくなる",
            },
            "seams": [{"from": "section-hero", "to": "section-value"}],
        })
        manifest = read_json(self.work / "manifest.json")
        manifest.setdefault("specialistReports", {})["seamContinuity"] = {
            "contract": "seam-continuity/v1",
            "path": "reports/seam-continuity.json",
            "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        }
        self.write_manifest(manifest)

    def test_hybrid_multiframe_template_passes_after_real_asset_files_exist(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=0)

        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["implementationAllowed"])

    def test_blocks_bbox_array_before_box_diff_can_crash(self):
        manifest = self.manifest()
        manifest["elements"][0]["bbox"] = [0, 0, 1440, 900]
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("manifest-bbox-object", {row["id"] for row in result["checks"]})
        self.assertFalse(result["implementationAllowed"])

    def test_blocks_generated_asset_path_only_contract(self):
        manifest = self.manifest()
        photo = next(row for row in manifest["elements"] if row["id"] == "hero.photo")
        photo["generatedAsset"] = {"workspacePath": "assets/hero-bg.png"}
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        ids = {row["id"] for row in result["checks"]}
        self.assertIn("asset:generated-asset-fields-missing", ids)

    def test_blocks_summarized_prompt_that_does_not_match_hash_bound_exact_prompt(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        manifest = read_json(self.work / "manifest.json")
        photo = next(row for row in manifest["elements"] if row["id"] == "hero.photo")
        photo["generatedAsset"]["prompt"] = "short summary only"
        self.write_manifest(manifest)

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("generated-prompt-provenance", {row["id"] for row in result["checks"]})

    def test_blocks_prompt_receipt_written_after_generated_asset(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        asset = self.work / "assets" / "hero-bg.png"
        prompt = self.work / "reports" / "prompts" / "hero-photo.txt"
        asset.touch()
        import time
        time.sleep(0.01)
        prompt.touch()

        result, _ = self.run_doctor(expected_code=2)

        check = next(row for row in result["checks"] if row["id"] == "generated-prompt-provenance")
        self.assertIn("newer than the adopted generated asset", json.dumps(check))

    def test_blocks_untouched_starter_evidence(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        shutil.copy2(ROOT / "templates" / "hypotheses.md", self.work / "reports" / "hypotheses.md")

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("starter-template-residue", {row["id"] for row in result["checks"]})

    def test_blocks_required_motion_without_bounded_plan(self):
        manifest = self.manifest()
        manifest["motion"] = {"required": True}
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("motion-contract", {row["id"] for row in result["checks"]})

    def test_art_directed_seam_requires_hash_bound_specialist_report(self):
        manifest = self.enable_art_directed_seam(self.manifest())
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        source = self.work / "reports" / "seam-source.txt"
        source.write_text("シームレスにスクロールしたくなる", encoding="utf-8")

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn(
            "specialist-report:seamContinuity",
            {row["id"] for row in result["checks"]},
        )

    def test_pre_css_accepts_ready_art_directed_seam_report(self):
        manifest = self.enable_art_directed_seam(self.manifest())
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        self.materialize_seam_continuity_report(status="ready")

        result, _ = self.run_doctor(expected_code=0)

        self.assertEqual(result["status"], "pass")
        self.assertFalse(
            any(row["id"] == "specialist-report:seamContinuity" for row in result["checks"])
        )

    def test_completion_requires_passed_art_directed_seam_report(self):
        manifest = self.enable_art_directed_seam(self.manifest())
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        self.materialize_seam_continuity_report(status="ready")
        write_json(
            self.work / "reports" / "section-scores.json",
            {"sections": [], "page": {"score": 8}, "dispositions": []},
        )
        (self.work / "reports" / "section-review.md").write_text(
            "Authored completion review.\n", encoding="utf-8"
        )

        result, _ = self.run_doctor(expected_code=2, phase="completion")

        check = next(
            row for row in result["checks"]
            if row["id"] == "specialist-report:seamContinuity"
        )
        self.assertIn("status must be 'pass'", json.dumps(check))

    def test_blocks_implementation_before_first_hash_bound_pre_css_pass(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        site = self.work / "site" / "styles.css"
        site.parent.mkdir(parents=True, exist_ok=True)
        site.write_text("body { color: black; }", encoding="utf-8")

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("implementation-before-pre-css", {row["id"] for row in result["checks"]})

    def test_allows_pre_css_reentry_after_prior_hash_bound_pass(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        first, _ = self.run_doctor(expected_code=0)
        self.assertEqual(first["status"], "pass")

        site = self.work / "site" / "styles.css"
        site.parent.mkdir(parents=True, exist_ok=True)
        site.write_text("body { color: black; }", encoding="utf-8")

        second, _ = self.run_doctor(expected_code=0)
        third, _ = self.run_doctor(expected_code=0)

        self.assertEqual(second["status"], "pass")
        self.assertEqual(third["status"], "pass")
        self.assertNotIn(
            "implementation-before-pre-css",
            {row["id"] for row in third["checks"]},
        )

    def test_blocks_global_sticky_without_viewport_ownership(self):
        manifest = self.manifest()
        nav = next(row for row in manifest["elements"] if row["id"] == "hero.nav")
        nav["placementScope"] = "container-content"
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("viewport-global-ownership", {row["id"] for row in result["checks"]})

    def test_blocks_fv_text_without_expected_visual_line_count(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row["id"] == "hero.heading")
        heading["typeSpec"].pop("expectedVisualLineCount")
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("fv-text-line-contract", {row["id"] for row in result["checks"]})

    def test_blocks_japanese_critical_text_without_typography_specialist_report(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row["id"] == "hero.heading")
        heading["text"]["content"] = "AI駆動型へ"
        heading["typeSpec"]["responsiveLineContracts"] = [{
            "minWidth": 320,
            "maxWidth": 1728,
            "expectedLines": ["AI駆動型へ"],
            "forbiddenOrphanFragments": ["へ"],
        }]
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("typography-specialist-report", {row["id"] for row in result["checks"]})

    def test_pre_css_accepts_hash_bound_pending_typography_report(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row["id"] == "hero.heading")
        heading["text"]["content"] = "AI駆動型へ"
        heading["typeSpec"]["responsiveLineContracts"] = [{
            "minWidth": 320,
            "maxWidth": 1728,
            "expectedLines": ["AI駆動型へ"],
            "forbiddenOrphanFragments": ["へ"],
        }]
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        for value in (
            "reports/typography/source-heading.png",
            "reports/typography/source-heading-run-1.png",
            "reports/typography/source-heading-run-2.png",
        ):
            path = self.work / value
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"typography evidence")
        report = {
            "schemaVersion": "typography-report/v1",
            "targets": [
                {
                    "id": "hero.heading",
                    "expectedRunCount": 2,
                    "sourceImpressionRef": "manifest:typeSpec.sourceImpression",
                    "impressionTolerances": {
                        "blockWidthRatio": 0.08,
                        "blockHeightRatio": 0.06,
                        "maxLineWidthRatio": 0.06,
                        "glyphHeightRatio": 0.03,
                        "trackingEm": 0.02,
                        "lineAdvanceRatio": 0.12,
                        "inkDensity": 0.08,
                        "jumpRatio": 0.25,
                    },
                    "sourceReference": {
                        "sourceImagePath": "mockups/section-01-hero.png",
                        "cropPath": "reports/typography/source-heading.png",
                        "expectedVisualLineCount": 2,
                        "measurementMethod": "manual-crop",
                    },
                    "runs": [
                        {"runId": "hero.heading.latin", "evidencePath": "reports/typography/source-heading-run-1.png"},
                        {"runId": "hero.heading.ja", "evidencePath": "reports/typography/source-heading-run-2.png"},
                    ],
                    "expectations": [
                        {"stateId": "base-320", "expectedVisualLineCount": 1}
                    ],
                }
            ],
            "gate": {"status": "pending_review"},
            "independentReview": {"status": "pending", "relationToProducer": "unknown"},
        }
        report_path = self.work / "reports" / "typography-report.json"
        write_json(report_path, report)
        manifest = read_json(self.work / "manifest.json")
        manifest.setdefault("specialistReports", {})["typography"] = {
            "contract": "typography-report/v1",
            "path": "reports/typography-report.json",
            "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        }
        self.write_manifest(manifest)

        result, _ = self.run_doctor(expected_code=0)

        self.assertEqual(result["status"], "pass")

    def test_blocks_hybrid_multiframe_without_device_inventory_report(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        manifest = read_json(self.work / "manifest.json")
        manifest["specialistReports"].pop("deviceInventory")
        self.write_manifest(manifest)

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("specialist-report:deviceInventory", {row["id"] for row in result["checks"]})

    def test_blocks_stale_photo_art_direction_receipt(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        manifest = read_json(self.work / "manifest.json")
        manifest["specialistReports"]["photoArtDirection"]["sha256"] = "0" * 64
        self.write_manifest(manifest)

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("specialist-report:photoArtDirection", {row["id"] for row in result["checks"]})

    def test_completion_requires_opted_in_production_specialists(self):
        manifest = self.manifest()
        manifest["productionReadiness"] = {
            "mediaDeliveryRequired": True,
            "interactionQaRequired": True,
        }
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        write_json(
            self.work / "reports" / "section-scores.json",
            {"sections": [], "page": {"score": 8}, "dispositions": []},
        )
        (self.work / "reports" / "section-review.md").write_text(
            "Authored completion review.\n", encoding="utf-8"
        )

        result, _ = self.run_doctor(expected_code=2, phase="completion")

        ids = {row["id"] for row in result["checks"]}
        self.assertIn("specialist-report:mediaDelivery", ids)
        self.assertIn("specialist-report:interaction", ids)

    def test_completion_accepts_hash_bound_production_specialists(self):
        manifest = self.manifest()
        manifest["productionReadiness"] = {
            "mediaDeliveryRequired": True,
            "interactionQaRequired": True,
        }
        self.write_manifest(manifest)
        self.materialize_asset_evidence()
        manifest = read_json(self.work / "manifest.json")
        media_path = self.work / "reports" / "media-delivery-report.json"
        write_json(
            media_path,
            {"schemaVersion": "media-delivery-report/v1", "status": "pass"},
        )
        manifest["specialistReports"]["mediaDelivery"] = {
            "contract": "media-delivery-report/v1",
            "path": "reports/media-delivery-report.json",
            "sha256": hashlib.sha256(media_path.read_bytes()).hexdigest(),
        }
        interaction_dir = self.work / "reports" / "interaction"
        interaction_manifest_path = interaction_dir / "interaction-manifest.json"
        write_json(interaction_manifest_path, {"schemaVersion": "interaction-manifest/v1"})
        interaction_manifest_sha = hashlib.sha256(interaction_manifest_path.read_bytes()).hexdigest()
        interaction_path = interaction_dir / "interaction-report.json"
        write_json(
            interaction_path,
            {
                "schemaVersion": "interaction-report/v1",
                "status": "pass",
                "manifest_sha256": interaction_manifest_sha,
            },
        )
        write_json(
            interaction_dir / "interaction-receipt.json",
            {
                "schemaVersion": "interaction-receipt/v1",
                "manifest": {"sha256": interaction_manifest_sha},
                "report": {"sha256": hashlib.sha256(interaction_path.read_bytes()).hexdigest()},
                "specialistReport": {
                    "contract": "interaction-report/v1",
                    "path": "reports/interaction/interaction-report.json",
                    "sha256": hashlib.sha256(interaction_path.read_bytes()).hexdigest(),
                },
            },
        )
        manifest["specialistReports"]["interaction"] = {
            "contract": "interaction-report/v1",
            "path": "reports/interaction/interaction-report.json",
            "sha256": hashlib.sha256(interaction_path.read_bytes()).hexdigest(),
        }
        self.write_manifest(manifest)
        write_json(
            self.work / "reports" / "section-scores.json",
            {"sections": [], "page": {"score": 8}, "dispositions": []},
        )
        (self.work / "reports" / "section-review.md").write_text(
            "Authored completion review.\n", encoding="utf-8"
        )

        result, _ = self.run_doctor(expected_code=0, phase="completion")

        self.assertFalse(
            any(row["id"].startswith("specialist-report:") for row in result["checks"]),
            result["checks"],
        )

    def test_blocks_script_runs_when_expected_run_count_is_conflated_with_lines(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row["id"] == "hero.heading")
        heading["typeSpec"]["scriptRuns"] = ["hero.heading.latin", "hero.heading.kanji"]
        heading["typeSpec"]["expectedRunCount"] = 1
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("fv-text-line-contract", {row["id"] for row in result["checks"]})

    def test_blocks_full_frame_generated_fv_without_foreground_carveout(self):
        manifest = self.manifest()
        cta = next(row for row in manifest["elements"] if row["id"] == "hero.cta")
        cta.pop("pixelDiffForeground")
        cta.pop("pixelDiffForegroundReason")
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("pixel-foreground-contract", {row["id"] for row in result["checks"]})

    def test_blocks_full_frame_generated_fv_without_measured_copy_space(self):
        manifest = self.manifest()
        photo = next(row for row in manifest["elements"] if row["id"] == "hero.photo")
        photo.pop("copySpace")
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("photo-geometry-contract", {row["id"] for row in result["checks"]})

    def test_blocks_multiple_source_photo_stories_collapsed_without_zones(self):
        manifest = self.manifest()
        manifest["detailInventory"].extend(
            [
                {
                    "id": "work-phone-story",
                    "section": "section-value",
                    "description": "phone call work scene",
                    "kind": "photo",
                    "sourceSpecific": True,
                    "priority": "high",
                    "manifestElementIds": ["hero.photo"],
                },
                {
                    "id": "work-recorder-story",
                    "section": "section-value",
                    "description": "field recorder work scene",
                    "kind": "photo",
                    "sourceSpecific": True,
                    "priority": "high",
                    "manifestElementIds": ["hero.photo"],
                },
            ]
        )
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("semantic-photo-separation", {row["id"] for row in result["checks"]})

    def test_blocks_multi_zone_crops_with_near_total_overlap(self):
        manifest = self.manifest()
        manifest["detailInventory"].extend(
            [
                {
                    "id": "work-phone-story",
                    "section": "section-value",
                    "description": "phone call work scene",
                    "kind": "photo",
                    "sourceSpecific": True,
                    "priority": "high",
                    "manifestElementIds": ["hero.photo"],
                },
                {
                    "id": "work-recorder-story",
                    "section": "section-value",
                    "description": "field recorder work scene",
                    "kind": "photo",
                    "sourceSpecific": True,
                    "priority": "high",
                    "manifestElementIds": ["hero.photo"],
                },
            ]
        )
        photo = next(row for row in manifest["elements"] if row["id"] == "hero.photo")
        photo["multiZoneAsset"] = {
            "assetWidth": 1000,
            "assetHeight": 500,
            "zones": [
                {
                    "inventoryId": "work-phone-story",
                    "cropRoi": {"x": 0, "y": 0, "w": 500, "h": 500},
                    "subjectSignature": "phone and mug",
                    "usedBy": "hero.heading",
                    "pairPath": "reports/crops/work-phone-integration.png",
                    "pairKind": "consumer-integration",
                },
                {
                    "inventoryId": "work-recorder-story",
                    "cropRoi": {"x": 1, "y": 0, "w": 500, "h": 500},
                    "subjectSignature": "recorder and notebook",
                    "usedBy": "hero.cta",
                    "pairPath": "reports/crops/work-recorder-integration.png",
                    "pairKind": "consumer-integration",
                },
            ],
        }
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        check = next(row for row in result["checks"] if row["id"] == "semantic-photo-separation")
        self.assertIn("overlap exceeds 25%", json.dumps(check))

    def test_blocks_card_photo_without_asset_surface_ownership_contract(self):
        manifest = self.manifest()
        photo = next(row for row in manifest["elements"] if row.get("id") == "hero.photo")
        photo["visualRole"] = "contained-photo"
        photo.pop("assetSurfaceContract", None)
        photo.pop("assetUnit", None)
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        ids = {row["id"] for row in result["checks"]}
        self.assertIn("asset-surface-contract-missing", ids)
        self.assertIn("asset-unit-missing", ids)

    def test_blocks_unevidenced_ellipse_decoration(self):
        manifest = self.manifest()
        decoration = next(row for row in manifest["elements"] if row.get("id") == "hero.heading")
        decoration["decorativeCraft"] = {
            "fieldType": "other",
            "complexityTarget": "large footer transition curve",
            "medium": "svg",
            "evidencePath": "reports/crops/font-bakeoff-a.png",
            "geometryPrimitive": "ellipse",
        }
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("unevidenced-large-ellipse", {row["id"] for row in result["checks"]})

    def test_requires_responsive_line_contract_for_critical_japanese_heading(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row.get("id") == "hero.heading")
        heading["text"]["content"] = "孤独を、ひとりで抱えなくていい社会へ。"
        heading["typeSpec"].pop("responsiveLineContracts", None)
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("japanese-responsive-line-contract-missing", {row["id"] for row in result["checks"]})

    def test_blocks_multiline_fv_heading_without_poster_geometry(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row.get("id") == "hero.heading")
        heading["typeSpec"].pop("posterGeometry", None)
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        check = next(row for row in result["checks"] if row["id"] == "fv-text-line-contract")
        self.assertIn("posterGeometry", json.dumps(check))

    def test_blocks_source_specific_inventory_without_rendering_craft(self):
        manifest = self.manifest()
        manifest["detailInventory"][0].pop("renderingCraft", None)
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        check = next(row for row in result["checks"] if row["id"] == "detail-inventory-contract")
        self.assertIn("sourceSpecific device requires renderingCraft", json.dumps(check))

    def test_allows_static_composite_as_one_card_artwork_plate(self):
        manifest = self.manifest()
        row = manifest["detailInventory"][1]
        row["renderingCraft"]["medium"] = "card-composite"
        row["renderingCraft"]["minimumAtomicParts"] = 3
        row["renderingCraft"]["atomicParts"] = ["laptop", "phone", "local shadows"]
        row["manifestElementIds"] = ["hero.photo"]
        artwork = next(item for item in manifest["elements"] if item.get("id") == "hero.photo")
        artwork["assetUnit"] = {
            "kind": "card_artwork_plate",
            "splitPolicy": "keep-together",
            "members": ["laptop", "phone", "local shadows"],
            "independentBehavior": {
                "motion": False,
                "responsiveRecompose": False,
                "reuse": False,
                "interaction": False,
                "contentUpdate": False,
                "layering": False,
            },
            "keepTogetherReason": "One static editorial composition inside a CSS-owned card shell.",
            "sourceEvidencePath": "reports/crops/value-primary-device-source-2x.png",
        }
        artwork["assetSurfaceContract"]["consumerOwnsFrame"] = True
        artwork["surfaceIntegration"].update({
            "sourceTopology": "contained_artwork",
            "sourceTopologyEvidencePath": "reports/crops/hero-photo-source-2x.png",
        })
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=0)

        self.assertNotIn("detail-inventory-contract", {item["id"] for item in result["checks"]})

    def test_flags_same_card_rasters_without_independent_split_evidence(self):
        manifest = self.manifest()
        photo = json.loads(json.dumps(next(
            item for item in manifest["elements"] if item.get("id") == "hero.photo"
        )))
        photo["id"] = "value.card.laptop"
        photo["el"] = "value-card-laptop"
        photo["sourceImage"] = "mockups/section-02-value.png"
        photo["visualRole"] = "contained-photo"
        photo["photoCompositionMode"] = "contained-photo"
        photo["clipOwner"] = "value.card"
        phone = json.loads(json.dumps(photo))
        phone["id"] = "value.card.phone"
        phone["el"] = "value-card-phone"
        manifest["elements"].append(photo)
        manifest["elements"].append(phone)
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        check = next(row for row in result["checks"] if row["id"] == "asset-overdecomposition-risk")
        self.assertEqual(check["status"], "needs_work")
        self.assertEqual(check["groups"][0]["clipOwner"], "value.card")

    def test_blocks_trapezoid_declared_as_triangle(self):
        manifest = self.manifest()
        manifest["elements"].append({
            "id": "flow.step-corner",
            "el": "flow-step-corner",
            "role": "decoration",
            "priority": "normal",
            "bbox": {"x": 40, "y": 40, "w": 160, "h": 120},
            "sourceImage": "mockups/section-02-value.png",
            "decorativeCraft": {
                "fieldType": "flat-geometry",
                "complexityTarget": "one measured three-vertex corner wedge",
                "medium": "svg",
                "evidencePath": "reports/crops/value-primary-device-source-2x.png",
                "microGeometry": {
                    "kind": "triangle",
                    "polygonVertexCount": 4,
                    "evidencePath": "reports/crops/value-primary-device-source-2x.png",
                },
            },
        })
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        check = next(row for row in result["checks"] if row["id"] == "micro-geometry-contract")
        self.assertIn("exactly 3", json.dumps(check))

    def test_blocks_background_removal_without_semantic_pixel_protection(self):
        manifest = self.manifest()
        photo = next(row for row in manifest["elements"] if row.get("id") == "hero.photo")
        photo["generatedAsset"]["backgroundRemovalUsed"] = True
        photo.pop("semanticPixelProtection", None)
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        self.assertIn("semantic-pixel-protection-missing", {row["id"] for row in result["checks"]})

    def test_blocks_multiline_fv_heading_with_wrong_line_box_count(self):
        manifest = self.manifest()
        heading = next(row for row in manifest["elements"] if row.get("id") == "hero.heading")
        heading["typeSpec"]["posterGeometry"]["sourceLineBBoxes"] = heading["typeSpec"]["posterGeometry"]["sourceLineBBoxes"][:1]
        self.write_manifest(manifest)
        self.materialize_asset_evidence()

        result, _ = self.run_doctor(expected_code=2)

        check = next(row for row in result["checks"] if row["id"] == "fv-text-line-contract")
        self.assertIn("must contain 2 measured lines", json.dumps(check))

    def test_completion_blocks_dict_shaped_sections_without_traceback(self):
        self.write_manifest(self.manifest())
        self.materialize_asset_evidence()
        write_json(
            self.work / "reports" / "section-scores.json",
            {
                "sections": {"section-hero": {"axes": {"composition": 8}}},
                "page": {"score": 8},
                "dispositions": [],
            },
        )
        (self.work / "reports" / "section-review.md").write_text(
            "Independent section review evidence.\n", encoding="utf-8"
        )

        result, _ = self.run_doctor(expected_code=2, phase="completion")

        self.assertIn("section-scores-sections-array", {row["id"] for row in result["checks"]})
        self.assertFalse(result["completionQaAllowed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
