#!/usr/bin/env python3
"""Regression tests for the pre-completion artifact checklist."""
import json
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "test" / "work" / "artifact_check"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_rgba_png(path, width=32, height=24, color=(238, 232, 218, 255)):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))

    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def attach_passed_typography_report(root, manifest, target_id):
    target_element = next(row for row in manifest["elements"] if row.get("id") == target_id)
    target_element.setdefault("typeSpec", {})["expectedVisualLineCount"] = 1
    source_crop = root / "reports" / "crops" / "typography-source.png"
    run_crop = root / "reports" / "crops" / "typography-source-run.png"
    source_crop.write_bytes(b"source typography crop")
    run_crop.write_bytes(b"source typography run crop")
    states = []
    for state_id in ("base-320", "spacing-320", "resize-200-320"):
        screenshot = root / "reports" / "crops" / f"{state_id}.png"
        measurement = root / "reports" / f"{state_id}-measurement.json"
        screenshot.write_bytes(b"render screenshot")
        write_json(measurement, {"schemaVersion": "typography-measurement/v1", "stateId": state_id})
        states.append({
            "id": state_id,
            "browser": "Chrome 140",
            "screenshotPath": str(screenshot.relative_to(root)),
            "measurementArtifactPath": str(measurement.relative_to(root)),
            "measurementArtifactSha256": hashlib.sha256(measurement.read_bytes()).hexdigest(),
            "status": "pass",
        })
    report = {
        "schemaVersion": "typography-report/v1",
        "targets": [
            {
                "id": target_id,
                "expectedRunCount": 1,
                "sourceReference": {
                    "sourceImagePath": "mockups/section-01-hero.png",
                    "cropPath": str(source_crop.relative_to(root)),
                    "expectedVisualLineCount": 1,
                    "measurementMethod": "manual-crop",
                },
                "runs": [
                    {
                        "runId": f"{target_id}.ja",
                        "evidencePath": str(run_crop.relative_to(root)),
                    }
                ],
                "expectations": [{"stateId": "base-320", "expectedVisualLineCount": 1}],
            }
        ],
        "states": states,
        "gate": {
            "status": "pass",
            "requiredStateIds": ["base-320", "spacing-320", "resize-200-320"],
        },
        "independentReview": {
            "status": "passed",
            "relationToProducer": "independent",
        },
    }
    path = root / "reports" / "typography-report.json"
    write_json(path, report)
    manifest["specialistReports"] = {
        "typography": {
            "contract": "typography-report/v1",
            "path": "reports/typography-report.json",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    }


def base_artifacts(root):
    (root / "reports" / "crops").mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "mockups").mkdir(parents=True, exist_ok=True)
    (root / "reports" / "crops" / "hero-lockup-pair.png").write_bytes(b"pair")
    write_rgba_png(root / "assets" / "hero-bg.png")
    (root / "mockups" / "section-01-hero.png").write_bytes(b"comp")
    manifest = {
        "mode": "hybrid",
        "photoLed": True,
        "image": "mockups/section-01-hero.png",
        "elements": [
            {
                "id": "hero.title",
                "el": "hero-title",
                "bbox": {"x": 80, "y": 120, "w": 620, "h": 160},
                "bboxSource": "snap_bbox",
                "measurementRef": {
                    "sourceArtifact": "reports/measurements/hero-title-snap.json",
                    "roi": "64,100,680,190",
                    "command": "snap_bbox.py ...",
                },
                "priority": "critical",
                "qaPriority": "fv-critical",
            },
            {
                "id": "hero.photo",
                "el": "hero-photo",
                "bbox": {"x": 0, "y": 0, "w": 1440, "h": 810},
                "bboxSource": "normalized",
                "measurementRef": {
                    "sourceArtifact": "mockups/section-01-hero.png",
                    "roi": "0,0,1440,810",
                    "method": "full-frame",
                },
                "priority": "critical",
                "qaPriority": "fv-critical",
                "mediaClass": "photo",
                "sourceImage": "mockups/section-01-hero.png",
                "assetStrategy": "generated",
                "visualRole": "background-environment",
                "photoCompositionMode": "full-frame-plate",
                "assetUnit": {
                    "kind": "full_field_scene_plate",
                    "splitPolicy": "keep-together",
                    "members": ["hero subject", "environment", "contact shadows"],
                    "independentBehavior": {
                        "motion": False,
                        "responsiveRecompose": False,
                        "reuse": False,
                        "interaction": False,
                        "contentUpdate": False,
                        "layering": False,
                    },
                    "keepTogetherReason": "The subject and environment own one hero field.",
                    "sourceEvidencePath": "reports/crops/hero-lockup-pair.png",
                },
                "copySpace": [
                    {
                        "for": "hero.title",
                        "roi": {"x": 80, "y": 120, "w": 620, "h": 160},
                        "minClearance": 24,
                    }
                ],
                "sourceFrameHasForegroundOverlap": True,
                "sourceFrameOverlapKinds": ["structural-text", "nav", "cta"],
                "cleanLayeredSource": False,
                "generatedAsset": {
                    "prompt": "bright executive photo plate, no text, no UI",
                    "sourceImage": "mockups/section-01-hero.png",
                    "workspacePath": "assets/hero-bg.png",
                    "generator": "imagegen",
                    "contaminationCheck": {
                        "method": "200% visual sweep",
                        "verdict": "clean",
                    },
                    "reviewPath": "reports/photo-asset-review.md",
                    "pairPath": "reports/crops/hero-lockup-pair.png",
                },
                "assetSurfaceContract": {
                    "consumerIds": ["hero.photo"],
                    "consumerOwnsFrame": False,
                    "consumerOwnsBackground": False,
                    "assetMustBleedToEdges": True,
                    "assetMustNotContainPanel": True,
                    "assetMustNotContainPadding": True,
                    "reviewPath": "reports/photo-asset-review.md",
                },
                "surfaceIntegration": {
                    "mode": "opaque_full_bleed",
                    "sourceTopology": "section_field",
                    "sourceTopologyEvidencePath": "reports/crops/hero-lockup-pair.png",
                    "edgePolicy": {
                        "top": "bleed",
                        "right": "bleed",
                        "bottom": "bleed",
                        "left": "bleed",
                    },
                    "consumerSurfaceOwner": "asset",
                    "outerWhitespaceOwner": "none",
                    "cropInUsePath": "reports/crops/hero-lockup-pair.png",
                },
            },
        ],
    }
    box = {
        "summary": {"total": 2, "pass": 2, "fail": 0, "y_waived_recomposition": 0},
        "items": [
            {"id": "hero.title", "pass": True},
            {"id": "hero.photo", "pass": True},
        ],
    }
    scores = {
        "webQualityScore": 78,
        "compFidelityScore": 72,
        "sections": [
            {
                "id": "hero",
                "axes": {
                    "composition": 8,
                    "typography": 8,
                    "palette_photo": 8,
                    "detail_devices": 8,
                },
                "pairs": ["reports/crops/hero-lockup-pair.png"],
            }
        ],
        "page": {"score": 8},
        "dispositions": [
            {
                "device": "hero lockup",
                "verdict": "present",
                "pairPath": "reports/crops/hero-lockup-pair.png",
            }
        ],
    }
    pixel = {
        "verdict": "acceptable",
        "pixel_verdict": "acceptable",
        "diff_ratio": 0.08,
        "comparison_coverage": 0.42,
        "min_comparison_coverage": 0.20,
        "coverage_sufficient": True,
    }
    section_review = "## Final self-score\n- WEB品質: 78/100\n- カンプ再現度: 72/100\n"
    photo_review = "## hero.photo\nzero text/logo/UI: pass\n"
    return manifest, box, scores, pixel, section_review, photo_review


class ArtifactCheckTests(unittest.TestCase):
    def setUp(self):
        self.work = WORK_ROOT / self._testMethodName
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)

    def write_artifacts(self, manifest, box, scores, pixel, section_review, photo_review):
        write_json(self.work / "manifest.json", manifest)
        write_json(self.work / "reports" / "box-report.json", box)
        write_json(self.work / "reports" / "section-scores.json", scores)
        write_json(self.work / "reports" / "fv-pixel-report.json", pixel)
        (self.work / "reports").mkdir(exist_ok=True)
        (self.work / "reports" / "section-review.md").write_text(section_review, encoding="utf-8")
        (self.work / "reports" / "photo-asset-review.md").write_text(photo_review, encoding="utf-8")

    def attach_multiframe_specialists(self, manifest):
        inventory_path = self.work / "reports" / "detail-inventory.json"
        write_json(
            inventory_path,
            {
                "schemaVersion": "detail-inventory/v1",
                "status": {"state": "complete", "blockers": []},
                "devices": [
                    {"id": row["id"]}
                    for row in manifest.get("detailInventory", [])
                    if isinstance(row, dict) and row.get("id")
                ],
            },
        )
        photo_path = self.work / "reports" / "photo-art-direction.json"
        write_json(
            photo_path,
            {"schemaVersion": "photo-art-direction/v1", "status": "adopted"},
        )
        reports = manifest.setdefault("specialistReports", {})
        reports["deviceInventory"] = {
            "contract": "detail-inventory/v1",
            "path": "reports/detail-inventory.json",
            "sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest(),
        }
        reports["photoArtDirection"] = {
            "contract": "photo-art-direction/v1",
            "path": "reports/photo-art-direction.json",
            "sha256": hashlib.sha256(photo_path.read_bytes()).hexdigest(),
        }

    def run_check(self, expected_code):
        out_path = self.work / "reports" / "artifact-check.json"
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/artifact_check.py",
                str(self.work),
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
        self.assertTrue(out_path.exists(), proc.stdout + proc.stderr)
        return read_json(out_path), proc

    def test_pass_when_required_artifacts_are_dense_and_linked(self):
        self.write_artifacts(*base_artifacts(self.work))
        result, _ = self.run_check(expected_code=0)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["summary"]["blocked"], 0)
        self.assertEqual(result["summary"]["needs_work"], 0)
        self.assertEqual(len(result["inputs"]["manifest"]["sha256"]), 64)
        self.assertGreater(result["inputs"]["boxReport"]["size"], 0)

    def test_contained_photo_requires_asset_surface_contract(self):
        artifacts = list(base_artifacts(self.work))
        manifest = artifacts[0]
        photo = next(row for row in manifest["elements"] if row.get("id") == "hero.photo")
        photo["visualRole"] = "contained-photo"
        photo.pop("assetSurfaceContract", None)
        self.write_artifacts(*artifacts)

        result, _ = self.run_check(expected_code=2)

        self.assertIn("asset-surface-contract-missing", {row["id"] for row in result["checks"]})

    def test_ellipse_decoration_requires_source_evidence(self):
        artifacts = list(base_artifacts(self.work))
        manifest = artifacts[0]
        title = next(row for row in manifest["elements"] if row.get("id") == "hero.title")
        title["decorativeCraft"] = {
            "fieldType": "other",
            "complexityTarget": "large seam arc",
            "medium": "svg",
            "evidencePath": "reports/crops/hero-lockup-pair.png",
            "geometryPrimitive": "ellipse",
        }
        self.write_artifacts(*artifacts)

        result, _ = self.run_check(expected_code=2)

        self.assertIn("unevidenced-large-ellipse", {row["id"] for row in result["checks"]})

    def test_review_and_scores_older_than_latest_box_are_stale(self):
        self.write_artifacts(*base_artifacts(self.work))
        reports = self.work / "reports"
        old = 1_700_000_000_000_000_000
        latest = old + 10_000_000_000
        os.utime(reports / "section-scores.json", ns=(old, old))
        os.utime(reports / "section-review.md", ns=(old, old))
        os.utime(reports / "box-report.json", ns=(latest, latest))

        result, _ = self.run_check(expected_code=1)

        ids = {row["id"] for row in result["checks"]}
        self.assertIn("stale-section-scores", ids)
        self.assertIn("stale-section-review", ids)

    def test_detail_inventory_and_independent_review_are_bound_to_crop_pairs(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["reviewPolicy"] = {
            "independentReviewRequired": True,
            "maxAdaptedSourceSpecificRatio": 0.2,
            "maxIndependentScoreDelta": 10,
        }
        manifest["detailInventory"] = [
            {
                "id": "hero-lockup-device",
                "section": "hero",
                "description": "source-specific hero lockup",
                "sourceSpecific": True,
                "priority": "high",
                "manifestElementIds": ["hero.title"],
            }
        ]
        scores["dispositions"][0]["inventoryId"] = "hero-lockup-device"
        scores["reviewProvenance"] = {
            "implementer": {"reviewerId": "impl-1", "reviewedAt": "2026-07-11T00:00:00Z"},
            "independent": {
                "reviewerKind": "separate-agent",
                "reviewerId": "review-2",
                "reviewedAt": "2026-07-11T00:10:00Z",
                "inputScope": "crop-pairs-only",
                "reviewedPairs": ["reports/crops/hero-lockup-pair.png"],
                "webQualityScore": 77,
                "compFidelityScore": 71,
                "sections": [
                    {"id": "hero", "score": 7.5, "pairs": ["reports/crops/hero-lockup-pair.png"]}
                ],
                "pageScore": 7.5,
                "topGaps": ["minor lockup scale delta"],
            },
        }
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=0)

        ids = {row["id"] for row in result["checks"]}
        self.assertIn("detail-inventory-coverage", ids)
        self.assertIn("independent-review", ids)
        self.assertIn("independent-score-delta", ids)

    def test_source_specific_adaptation_volume_and_review_delta_need_work(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["reviewPolicy"] = {
            "independentReviewRequired": True,
            "maxAdaptedSourceSpecificRatio": 0.2,
            "maxIndependentScoreDelta": 10,
        }
        manifest["detailInventory"] = [
            {
                "id": "hero-lockup-device",
                "section": "hero",
                "description": "source-specific hero lockup",
                "sourceSpecific": True,
                "priority": "high",
                "manifestElementIds": ["hero.title"],
            }
        ]
        scores["dispositions"][0].update({"inventoryId": "hero-lockup-device", "verdict": "adapted"})
        scores["reviewProvenance"] = {
            "implementer": {"reviewerId": "impl-1", "reviewedAt": "2026-07-11T00:00:00Z"},
            "independent": {
                "reviewerKind": "human",
                "reviewerId": "human-2",
                "reviewedAt": "2026-07-11T00:10:00Z",
                "inputScope": "crop-pairs-only",
                "reviewedPairs": ["reports/crops/hero-lockup-pair.png"],
                "webQualityScore": 75,
                "compFidelityScore": 60,
                "sections": [
                    {"id": "hero", "score": 6.5, "pairs": ["reports/crops/hero-lockup-pair.png"]}
                ],
                "pageScore": 6.5,
                "topGaps": ["source motif simplified"],
            },
        }
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=1)

        ids = {row["id"] for row in result["checks"]}
        self.assertIn("source-specific-adaptation-volume", ids)
        self.assertIn("independent-score-delta", ids)

    def test_dict_shaped_sections_are_blocked_without_traceback(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        scores["sections"] = {"hero": scores["sections"][0]}
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, proc = self.run_check(expected_code=2)

        self.assertIn("section-scores-sections-array", {row["id"] for row in result["checks"]})
        self.assertNotIn("Traceback", proc.stderr)

    def test_multiframe_requires_computed_page_flow_artifact(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["referenceImages"] = [
            {"path": f"mockups/{section}.png", "use": "section-comp", "section": section}
            for section in ("hero", "value", "cta")
        ]
        self.attach_multiframe_specialists(manifest)
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)
        result, _ = self.run_check(expected_code=1)
        self.assertIn("page-flow-missing", {row["id"] for row in result["checks"]})

    def test_multiframe_passes_with_green_page_flow_artifact(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["referenceImages"] = [
            {"path": f"mockups/{section}.png", "use": "section-comp", "section": section}
            for section in ("hero", "value", "cta")
        ]
        self.attach_multiframe_specialists(manifest)
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)
        write_json(
            self.work / "reports" / "page-flow.json",
            {"status": "pass", "checks": [], "metrics": {"stackedFrameLock": False}},
        )
        result, _ = self.run_check(expected_code=0)
        self.assertIn("page-flow", {row["id"] for row in result["checks"]})

    def test_needs_work_for_sparse_pairs_missing_ledger_and_fv_pixel_warning(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["elements"][0].pop("measurementRef")
        scores["sections"][0]["pairs"] = []
        scores["dispositions"][0].pop("pairPath")
        scores.pop("webQualityScore")
        scores.pop("compFidelityScore")
        section_review = "## Final self-score\n- overall: 75/100\n"
        pixel["verdict"] = "needs_work"
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=1)

        self.assertEqual(result["status"], "needs_work")
        ids = {row["id"] for row in result["checks"]}
        self.assertIn("crop-pair-count", ids)
        self.assertIn("disposition-pair-missing", ids)
        self.assertIn("bbox-ledger-missing", ids)
        self.assertIn("fv-pixel-warning", ids)
        self.assertIn("two-track-scoring", ids)

    def test_blocked_when_generated_asset_file_is_missing(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        (self.work / "assets" / "hero-bg.png").unlink()
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=2)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("generated-asset-file-missing", {row["id"] for row in result["checks"]})

    def test_blocked_when_clean_subcrop_escapes_fused_source_composition(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        photo = manifest["elements"][1]
        photo["assetStrategy"] = "crop-asset"
        photo["cropPreservesComposition"] = False
        photo.pop("generatedAsset")
        photo["croppedAsset"] = {
            "workspacePath": "assets/hero-bg.png",
            "sourcePath": "mockups/section-01-hero.png",
            "sourceRoi": "590,185,720,550",
            "contaminationCheck": {
                "method": "crop_asset.py + 200% sweep",
                "verdict": "clean",
            },
            "reviewPath": "reports/photo-asset-review.md",
            "pairPath": "reports/crops/hero-lockup-pair.png",
        }
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=2)

        self.assertEqual(result["status"], "blocked")
        ids = {row["id"] for row in result["checks"]}
        self.assertIn("asset-overlap-crop-forbidden", ids)
        self.assertIn("asset-crop-composition-unproven", ids)

    def test_waived_elements_are_removed_from_both_rate_operands(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["photoLed"] = False
        manifest["elements"] = [
            {"id": f"item-{index}", "priority": "normal", "qaPriority": "detail"}
            for index in range(5)
        ]
        box["summary"] = {
            "total": 5,
            "pass": 3,
            "fail": 2,
            "y_waived_recomposition": 2,
        }
        box["items"] = [
            {"id": "item-0", "pass": True, "y_waived_recomposition": True},
            {"id": "item-1", "pass": True, "y_waived_recomposition": True},
            {"id": "item-2", "pass": True},
            {"id": "item-3", "pass": False, "failed_axes": ["x"]},
            {"id": "item-4", "pass": False, "failed_axes": ["w"]},
        ]
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=1)

        rate = next(row for row in result["checks"] if row["id"] == "box-pass-rate")
        self.assertIn("1/3 = 0.33", rate["message"])

    def test_y_waiver_does_not_hide_non_y_critical_failure(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["photoLed"] = False
        manifest["elements"] = [
            {
                "id": "value.heading",
                "priority": "high",
                "qaPriority": "section-critical",
            }
        ]
        box["summary"] = {
            "total": 1,
            "pass": 0,
            "fail": 1,
            "y_waived_recomposition": 1,
        }
        box["items"] = [{
            "id": "value.heading",
            "pass": False,
            "failed_axes": ["w", "h"],
            "y_waived_recomposition": True,
        }]
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=1)

        critical = next(row for row in result["checks"] if row["id"] == "critical-boxes")
        self.assertEqual(critical["failing"], ["value.heading"])
        rate = next(row for row in result["checks"] if row["id"] == "box-pass-rate")
        self.assertIn("0/1 = 0.00", rate["message"])

    def test_old_pixel_report_without_coverage_is_needs_work(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        pixel.pop("comparison_coverage")
        pixel.pop("min_comparison_coverage")
        pixel.pop("coverage_sufficient")
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=1)

        self.assertIn(
            "fv-pixel-coverage-missing",
            {row["id"] for row in result["checks"]},
        )

    def test_full_frame_generated_hybrid_photo_can_make_pixel_identity_not_applicable(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["viewport"] = {"width": 1440, "height": 810}
        pixel = {
            "verdict": "not_applicable_generated_media",
            "pixel_verdict": "not_applicable",
            "diff_ratio": 0,
            "comparison_coverage": 0,
            "eligible_non_generated_media_px": 0,
            "eligible_comparison_coverage": None,
            "generated_media_masked_px": 1296000,
            "generated_media_coverage": 1.0,
            "auto_generated_media_masks": ["hero.photo"],
            "min_comparison_coverage": 0.20,
            "coverage_sufficient": False,
            "pixel_evidence_applicable": False,
        }
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=0)

        self.assertIn(
            "fv-pixel-generated-media-not-applicable",
            {row["id"] for row in result["checks"]},
        )

    def test_crop_pair_must_be_nonempty_regular_file(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        scores["sections"][0]["pairs"] = ["reports/crops"]
        scores["dispositions"][0]["pairPath"] = "reports/crops"
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=2)

        self.assertIn("crop-pair-files", {row["id"] for row in result["checks"]})

    def test_generated_lettering_requires_shipped_asset_and_exact_text_proof(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["elements"].append(
            {
                "id": "hero.lettering",
                "el": "hero-lettering",
                "bbox": {"x": 80, "y": 300, "w": 240, "h": 90},
                "priority": "high",
                "mediaClass": "lettering-decal",
                "assetStrategy": "generated",
                "text": {"content": "聴くから、つながる。"},
            }
        )
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=2)

        self.assertIn(
            "lettering-proof-fields-missing",
            {row["id"] for row in result["checks"]},
        )

    def test_critical_structural_text_requires_class_and_font_bakeoff(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["elements"][0]["text"] = {"content": "聴く仕事ラボ"}
        attach_passed_typography_report(self.work, manifest, "hero.title")
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=1)

        ids = {row["id"] for row in result["checks"]}
        self.assertIn("typography-letterform-class-missing", ids)
        self.assertIn("typography-font-bakeoff-missing", ids)

    def test_critical_structural_text_passes_with_readable_same_class_bakeoff(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        for name in ("font-a-pair.png", "font-b-pair.png"):
            (self.work / "reports" / "crops" / name).write_bytes(b"pair")
        manifest["elements"][0]["text"] = {"content": "聴く仕事ラボ"}
        manifest["elements"][0]["typeSpec"] = {
            "letterformClass": "gothic",
            "fontBakeoffEvidence": [
                "reports/crops/font-a-pair.png",
                "reports/crops/font-b-pair.png",
            ],
        }
        attach_passed_typography_report(self.work, manifest, "hero.title")
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=0)

        self.assertEqual(result["status"], "pass")

    def test_transform_exception_requires_readable_source_evidence(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        for name in ("font-a-pair.png", "font-b-pair.png"):
            (self.work / "reports" / "crops" / name).write_bytes(b"pair")
        manifest["elements"][0]["text"] = {"content": "聴く仕事ラボ"}
        manifest["elements"][0]["typeSpec"] = {
            "letterformClass": "display",
            "fontBakeoffEvidence": [
                "reports/crops/font-a-pair.png",
                "reports/crops/font-b-pair.png",
            ],
            "transformException": {
                "allowed": True,
                "scope": "source-intent-display",
                "reason": "source visibly compresses the decorative lockup",
                "evidencePath": "reports/crops/missing-transform-pair.png",
            },
        }
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=2)

        self.assertIn(
            "typography-transform-evidence-missing",
            {row["id"] for row in result["checks"]},
        )

    def test_critical_photo_requires_composition_mode(self):
        manifest, box, scores, pixel, section_review, photo_review = base_artifacts(self.work)
        manifest["elements"][1].pop("photoCompositionMode")
        self.write_artifacts(manifest, box, scores, pixel, section_review, photo_review)

        result, _ = self.run_check(expected_code=1)

        self.assertIn(
            "photo-composition-mode-missing",
            {row["id"] for row in result["checks"]},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
