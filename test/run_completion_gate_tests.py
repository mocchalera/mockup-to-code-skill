#!/usr/bin/env python3
"""Regression tests for the Phase 10 completion gate."""
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "test" / "work" / "completion_gate"


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
            struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def receipt(path):
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
        "mtimeNs": path.stat().st_mtime_ns,
    }


def base_artifacts():
    manifest = {
        "mode": "hybrid",
        "photoLed": False,
        "elements": [
            {"id": "hero.logo", "qaPriority": "fv-critical"},
            {"id": "hero.title", "qaPriority": "fv-critical"},
            {"id": "decision.cta", "qaPriority": "section-critical"},
        ],
    }
    box = {
        "summary": {"total": 3, "pass": 3, "fail": 0, "y_waived_recomposition": 0},
        "items": [
            {"id": "hero.logo", "pass": True},
            {"id": "hero.title", "pass": True},
            {"id": "decision.cta", "pass": True},
        ],
    }
    clean_check = {"viewports": [{"viewport": "1440x900", "pass": True}]}
    scores = {
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
        "page": {
            "axes": {
                "composition": 8,
                "typography": 8,
                "palette_photo": 8,
                "detail_devices": 8,
            }
        },
        "dispositions": [{"device": "hero lockup", "verdict": "present"}],
    }
    pixel = {"verdict": "acceptable", "diff_ratio": 0.02}
    impression = {
        "metrics": [
            {
                "metric": "lockup_scale_ratio",
                "comp": 0.22,
                "build": 0.21,
                "delta_pct": -4.5,
                "tolerance_pct": 15,
                "pass": True,
            }
        ]
    }
    return {
        "manifest": manifest,
        "box": box,
        "visual": clean_check,
        "widths": clean_check,
        "scores": scores,
        "artifact": {"status": "pass", "checks": []},
        "pixel": pixel,
        "impression": impression,
    }


class CompletionGateTests(unittest.TestCase):
    def setUp(self):
        self.work = WORK_ROOT / self._testMethodName
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)

    def valid_generated_photo(self, element_id="hero.photo"):
        asset = self.work / "assets" / "hero-generated.png"
        source = self.work / "mockups" / "section-01-hero.png"
        review = self.work / "reports" / "photo-asset-review.md"
        pair = self.work / "reports" / "crops" / "hero-photo-pair.png"
        asset.parent.mkdir(parents=True, exist_ok=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        pair.parent.mkdir(parents=True, exist_ok=True)
        write_rgba_png(asset)
        source.write_bytes(b"comp")
        review.write_text(f"# {element_id}\nclean generated plate\n", encoding="utf-8")
        pair.write_bytes(b"pair")
        return {
            "id": element_id,
            "mediaClass": "photo",
            "qaPriority": "fv-critical",
            "sourceImage": str(source),
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
                "sourceEvidencePath": str(pair),
            },
            "copySpace": [
                {"for": "hero.title", "roi": {"x": 0, "y": 0, "w": 16, "h": 16}, "minClearance": 4}
            ],
            "sourceFrameHasForegroundOverlap": True,
            "sourceFrameOverlapKinds": ["structural-text", "nav", "cta"],
            "cleanLayeredSource": False,
            "generatedAsset": {
                "prompt": "bright listening room, no text, no logo, no UI",
                "sourceImage": str(source),
                "workspacePath": str(asset),
                "generator": "imagegen",
                "contaminationCheck": {
                    "method": "200% visual sweep",
                    "verdict": "clean",
                },
                "reviewPath": str(review),
                "pairPath": str(pair),
            },
            "assetSurfaceContract": {
                "consumerIds": [element_id],
                "consumerOwnsFrame": False,
                "consumerOwnsBackground": False,
                "assetMustBleedToEdges": True,
                "assetMustNotContainPanel": True,
                "assetMustNotContainPadding": True,
                "reviewPath": str(review),
            },
            "surfaceIntegration": {
                "mode": "opaque_full_bleed",
                "sourceTopology": "section_field",
                "sourceTopologyEvidencePath": str(pair),
                "edgePolicy": {
                    "top": "bleed",
                    "right": "bleed",
                    "bottom": "bleed",
                    "left": "bleed",
                },
                "consumerSurfaceOwner": "asset",
                "outerWhitespaceOwner": "none",
                "cropInUsePath": str(pair),
            },
        }

    def run_gate(self, artifacts, expect_code):
        paths = {}
        artifact_payload = artifacts.get("artifact")
        for name, payload in artifacts.items():
            if name == "artifact":
                continue
            path = self.work / f"{name}.json"
            write_json(path, payload)
            paths[name] = path
        if artifact_payload is not None:
            artifact_path = self.work / "artifact.json"
            if "inputs" not in artifact_payload:
                artifact_payload = {**artifact_payload, "inputs": {
                    "manifest": receipt(paths["manifest"]),
                    "boxReport": receipt(paths["box"]),
                    "sectionScores": receipt(paths["scores"]),
                    "fvPixel": receipt(paths["pixel"]),
                }}
            write_json(artifact_path, artifact_payload)
            paths["artifact"] = artifact_path
        out_path = self.work / "completion-verdict.json"
        command = [
                sys.executable,
                "scripts/completion_gate.py",
                str(paths["manifest"]),
                str(paths["box"]),
                "--visual-check",
                str(paths["visual"]),
                "--widths-check",
                str(paths["widths"]),
                "--scores",
                str(paths["scores"]),
                "--artifact-check",
                str(paths["artifact"]),
                "--fv-pixel",
                str(paths["pixel"]),
                "--impression",
                str(paths["impression"]),
        ]
        if "page_flow" in paths:
            command.extend(["--page-flow", str(paths["page_flow"])])
        command.extend(["--out", str(out_path)])
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, expect_code, proc.stdout + proc.stderr)
        self.assertTrue(out_path.exists(), proc.stdout + proc.stderr)
        return read_json(out_path), proc

    def test_complete_when_all_gates_pass(self):
        result, _ = self.run_gate(base_artifacts(), expect_code=0)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["blocked_reasons"], [])
        self.assertEqual(result["prototype_reasons"], [])

    def test_requested_motion_without_runtime_report_is_prototype(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["motion"] = {"required": True}

        result, _ = self.run_gate(artifacts, expect_code=1)

        self.assertEqual(result["status"], "prototype")
        self.assertTrue(any("G13" in reason for reason in result["prototype_reasons"]))

    def test_independent_review_lower_score_controls_completion(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["reviewPolicy"] = {
            "independentReviewRequired": True,
            "maxAdaptedSourceSpecificRatio": 0.2,
            "maxIndependentScoreDelta": 10,
        }
        artifacts["scores"].update(
            {
                "webQualityScore": 86,
                "compFidelityScore": 84,
                "reviewProvenance": {
                    "implementer": {"reviewerId": "impl-1"},
                    "independent": {
                        "reviewerKind": "separate-agent",
                        "reviewerId": "review-2",
                        "compFidelityScore": 74,
                        "sections": [{"id": "hero", "score": 6.5}],
                        "pageScore": 7.5,
                    },
                },
            }
        )

        result, _ = self.run_gate(artifacts, expect_code=1)

        self.assertEqual(result["status"], "prototype")
        self.assertEqual(result["metrics"]["review"]["effectiveCompFidelity"], 74)
        self.assertTrue(any("G12 independent section" in reason for reason in result["prototype_reasons"]))
        self.assertTrue(any("G12 implementer/independent score delta" in reason for reason in result["prototype_reasons"]))

    def test_declared_foreground_with_zero_compared_pixels_is_prototype(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["reviewPolicy"] = {"minForegroundPixelCoverage": 0.01}
        artifacts["manifest"]["elements"][0]["pixelDiffForeground"] = True
        artifacts["pixel"].update(
            {
                "auto_foreground_carveouts": ["hero.logo"],
                "foreground_regions": [
                    {"id": "hero.logo", "area_px": 2000, "compared_px": 0, "comparison_coverage": 0}
                ],
                "foreground_union_coverage": 0,
            }
        )

        result, _ = self.run_gate(artifacts, expect_code=1)

        reasons = "\n".join(result["prototype_reasons"])
        self.assertIn("G3 FV foreground regions have zero compared pixels", reasons)
        self.assertIn("G3 FV foreground union coverage", reasons)

    def test_dict_shaped_sections_are_blocked_without_traceback(self):
        artifacts = base_artifacts()
        artifacts["scores"]["sections"] = {
            "hero": artifacts["scores"]["sections"][0]
        }

        result, proc = self.run_gate(artifacts, expect_code=2)

        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "section-scores.sections must be an array",
            "\n".join(result["blocked_reasons"]),
        )
        self.assertNotIn("Traceback", proc.stderr)

    def test_multiframe_stacked_page_flow_is_prototype(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["referenceImages"] = [
            {"path": f"section-{n}.png", "use": "section-comp", "section": section}
            for n, section in enumerate(("hero", "value", "cta"), start=1)
        ]
        artifacts["page_flow"] = {
            "status": "needs_work",
            "checks": [
                {"id": "stacked-frames", "status": "needs_work"},
                {"id": "flat-seams", "status": "needs_work"},
            ],
            "metrics": {"stackedFrameLock": True},
        }
        result, _ = self.run_gate(artifacts, expect_code=1)
        self.assertEqual(result["status"], "prototype")
        self.assertTrue(any("G10 page-flow" in reason for reason in result["prototype_reasons"]))
        self.assertTrue(any(warning.startswith("W4") for warning in result["warnings"]))

    def test_multiframe_computed_page_flow_can_complete(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["referenceImages"] = [
            {"path": f"section-{n}.png", "use": "section-comp", "section": section}
            for n, section in enumerate(("hero", "value", "cta"), start=1)
        ]
        artifacts["page_flow"] = {
            "status": "pass",
            "checks": [{"id": "section-height-rhythm", "status": "pass"}],
            "metrics": {"stackedFrameLock": False},
        }
        result, _ = self.run_gate(artifacts, expect_code=0)
        self.assertEqual(result["status"], "complete")

    def test_prototype_when_fidelity_gates_fail(self):
        artifacts = base_artifacts()
        artifacts["box"]["summary"] = {
            "total": 3,
            "pass": 1,
            "fail": 2,
            "y_waived_recomposition": 0,
        }
        artifacts["box"]["items"][0]["pass"] = False
        artifacts["box"]["items"][1]["pass"] = False
        artifacts["pixel"]["verdict"] = "needs_work"
        artifacts["impression"]["metrics"][0]["pass"] = False

        result, _ = self.run_gate(artifacts, expect_code=1)

        self.assertEqual(result["status"], "prototype")
        reasons = "\n".join(result["prototype_reasons"])
        self.assertIn("G1 fv-critical box failures: hero.logo, hero.title", reasons)
        self.assertIn("G2 box pass rate 1/3 = 0.33 < 0.80", reasons)
        self.assertIn("G3 FV pixel diff verdict 'needs_work'", reasons)
        self.assertIn("G6 impression metric 'lockup_scale_ratio'", reasons)

    def test_listening_lab_24_of_30_with_9_y_waivers_is_not_over_one(self):
        """Regression: the old calculation produced 24/(30-9) = 1.14."""
        artifacts = base_artifacts()
        artifacts["manifest"]["elements"] = [
            {"id": f"section.item-{index}", "priority": "normal", "qaPriority": "detail"}
            for index in range(30)
        ]
        artifacts["box"] = {
            "summary": {
                "total": 30,
                "pass": 24,
                "fail": 6,
                "y_waived_recomposition": 9,
            },
            "items": [
                {
                    "id": f"section.item-{index}",
                    "pass": index < 24,
                    **({"y_waived_recomposition": True}
                       if index < 5 or 24 <= index < 28 else {}),
                    **({"failed_axes": ["x"] if index < 28 else ["w"]}
                       if index >= 24 else {"failed_axes": []}),
                }
                for index in range(30)
            ],
        }

        result, _ = self.run_gate(artifacts, expect_code=1)

        box_metrics = result["metrics"]["box"]
        self.assertEqual(box_metrics["effectivePassed"], 19)
        self.assertEqual(box_metrics["eligibleTotal"], 25)
        self.assertEqual(box_metrics["yWaiverRows"], 9)
        self.assertEqual(box_metrics["yOnlyWaived"], 5)
        self.assertGreaterEqual(box_metrics["passRate"], 0.0)
        self.assertLessEqual(box_metrics["passRate"], 1.0)
        self.assertIn(
            "G2 box pass rate 19/25 = 0.76 < 0.80",
            "\n".join(result["prototype_reasons"]),
        )

    def test_y_waiver_does_not_hide_x_failure_on_high_priority_row(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["elements"] = [
            {
                "id": f"section.item-{index}",
                "priority": "high" if index == 4 else "normal",
                "qaPriority": "detail",
            }
            for index in range(5)
        ]
        artifacts["box"] = {
            "summary": {
                "total": 5,
                "pass": 4,
                "fail": 1,
                "y_waived_recomposition": 1,
            },
            "items": [
                {"id": f"section.item-{index}", "pass": True}
                for index in range(4)
            ] + [{
                "id": "section.item-4",
                "pass": False,
                "failed_axes": ["x"],
                "y_waived_recomposition": True,
            }],
        }

        result, _ = self.run_gate(artifacts, expect_code=1)

        reasons = "\n".join(result["prototype_reasons"])
        self.assertIn(
            "G1 section/priority-critical box failures: section.item-4",
            reasons,
        )
        self.assertNotIn("G2 box pass rate", reasons)
        self.assertEqual(result["metrics"]["box"]["eligibleTotal"], 5)

    def test_section_critical_failure_prevents_complete_at_passing_rate(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["elements"] = [
            {
                "id": f"section.item-{index}",
                "priority": "normal",
                "qaPriority": "section-critical" if index == 4 else "detail",
            }
            for index in range(5)
        ]
        artifacts["box"] = {
            "summary": {"total": 5, "pass": 4, "fail": 1},
            "items": [
                {"id": f"section.item-{index}", "pass": index < 4,
                 **({"failed_axes": ["w"]} if index == 4 else {})}
                for index in range(5)
            ],
        }

        result, _ = self.run_gate(artifacts, expect_code=1)

        reasons = "\n".join(result["prototype_reasons"])
        self.assertIn(
            "G1 section/priority-critical box failures: section.item-4",
            reasons,
        )
        self.assertNotIn("G2 box pass rate", reasons)

    def test_artifact_check_needs_work_prevents_complete(self):
        artifacts = base_artifacts()
        artifacts["artifact"] = {
            "status": "needs_work",
            "checks": [{"id": "crop-pairs", "status": "needs_work"}],
        }

        result, _ = self.run_gate(artifacts, expect_code=1)

        self.assertEqual(result["status"], "prototype")
        self.assertIn(
            "G11 artifact-check report needs work",
            "\n".join(result["prototype_reasons"]),
        )

    def test_artifact_check_input_receipt_mismatch_is_blocked(self):
        artifacts = base_artifacts()
        artifacts["artifact"] = {
            "status": "pass",
            "checks": [],
            "inputs": {
                label: {"sha256": "0" * 64, "size": 0, "mtimeNs": 0}
                for label in ("manifest", "boxReport", "sectionScores", "fvPixel")
            },
        }

        result, _ = self.run_gate(artifacts, expect_code=2)

        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "G11 artifact-check 'manifest' SHA-256 does not match",
            "\n".join(result["blocked_reasons"]),
        )

    def test_blocked_when_required_evidence_is_missing(self):
        artifacts = base_artifacts()
        scores_path = self.work / "scores.json"
        paths = {}
        for name, payload in artifacts.items():
            if name == "scores":
                continue
            path = self.work / f"{name}.json"
            write_json(path, payload)
            paths[name] = path
        out_path = self.work / "completion-verdict.json"
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/completion_gate.py",
                str(paths["manifest"]),
                str(paths["box"]),
                "--visual-check",
                str(paths["visual"]),
                "--widths-check",
                str(paths["widths"]),
                "--scores",
                str(scores_path),
                "--artifact-check",
                str(paths["artifact"]),
                "--fv-pixel",
                str(paths["pixel"]),
                "--impression",
                str(paths["impression"]),
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )

        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        result = read_json(out_path)
        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "missing evidence: section scores",
            "\n".join(result["blocked_reasons"]),
        )

    def test_uniform_threshold_scores_emit_warning(self):
        artifacts = base_artifacts()
        artifacts["scores"]["sections"][0]["axes"] = {
            "composition": 7,
            "typography": 7,
            "palette_photo": 7,
            "detail_devices": 7,
        }
        artifacts["scores"]["page"] = {"score": 7}

        result, _ = self.run_gate(artifacts, expect_code=0)

        self.assertEqual(result["status"], "complete")
        self.assertIn("W1 every score is exactly the pass bar", "\n".join(result["warnings"]))

    def test_blocked_when_photo_led_manifest_omits_photo_even_with_generated_decal(self):
        # A non-photo generated decal must not satisfy G8, and the explicit
        # photo-led declaration must close the zero-photo-row escape even when
        # disposition copy is Japanese and avoids the English keyword heuristic.
        artifacts = base_artifacts()
        artifacts["manifest"]["photoLed"] = True
        artifacts["manifest"]["elements"].append(
            {
                "id": "hero.lettering",
                "mediaClass": "lettering-decal",
                "assetStrategy": "generated",
            }
        )
        artifacts["scores"]["dispositions"] = [
            {"device": "メインビジュアル人物写真", "verdict": "adapted",
             "note": "translated to abstract decision UI"},
        ]
        result, _ = self.run_gate(artifacts, expect_code=2)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("photoLed=true but no fv/section-critical photo",
                      "\n".join(result["blocked_reasons"]))

    def test_generated_lettering_does_not_count_as_shipped_photo(self):
        artifacts = base_artifacts()
        asset = self.work / "assets" / "lettering.png"
        pair = self.work / "reports" / "crops" / "lettering-pair.png"
        asset.parent.mkdir(parents=True, exist_ok=True)
        pair.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"png")
        pair.write_bytes(b"pair")
        artifacts["manifest"]["elements"].append(
            {
                "id": "hero.lettering",
                "mediaClass": "lettering-decal",
                "assetStrategy": "generated",
                "text": {"content": "Listen"},
                "letteringProof": {
                    "exactText": "Listen",
                    "method": "200% crop comparison",
                    "pairPath": str(pair),
                },
                "generatedAsset": {
                    "prompt": "handwritten Listen, transparent background",
                    "workspacePath": str(asset),
                    "generator": "imagegen",
                },
            }
        )
        artifacts["scores"]["dispositions"] = [
            {"device": "hero executive photo", "verdict": "present"}
        ]

        result, _ = self.run_gate(artifacts, expect_code=1)

        self.assertIn(
            "G8 disposition 'hero executive photo'",
            "\n".join(result["prototype_reasons"]),
        )

    def test_blocked_when_declared_photo_region_uses_invalid_medium(self):
        # A photo element honestly declared but reclassified to svg/placeholder.
        artifacts = base_artifacts()
        artifacts["manifest"]["photoLed"] = True
        artifacts["manifest"]["elements"].append(
            {"id": "hero.photo", "mediaClass": "photo",
             "qaPriority": "fv-critical", "assetStrategy": "svg"})
        result, _ = self.run_gate(artifacts, expect_code=2)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("G8 photo region 'hero.photo'",
                      "\n".join(result["prototype_reasons"]))
        self.assertIn("G9 asset policy 'hero.photo'",
                      "\n".join(result["blocked_reasons"]))

    def test_complete_when_photo_region_ships_generated_raster(self):
        # Positive control: a real shipped raster clears G8 even though a
        # portrait disposition is present.
        artifacts = base_artifacts()
        artifacts["manifest"]["photoLed"] = True
        artifacts["manifest"]["elements"].append(self.valid_generated_photo())
        artifacts["scores"]["dispositions"] = [
            {"device": "hero executive portrait", "verdict": "present"},
        ]
        result, _ = self.run_gate(artifacts, expect_code=0)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["prototype_reasons"], [])

    def test_full_frame_generated_hybrid_photo_uses_asset_and_impression_gates(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["photoLed"] = True
        artifacts["manifest"]["viewport"] = {"width": 1440, "height": 900}
        photo = self.valid_generated_photo()
        photo["bbox"] = {"x": 0, "y": 0, "w": 1440, "h": 900}
        artifacts["manifest"]["image"] = photo["sourceImage"]
        artifacts["manifest"]["elements"].append(photo)
        artifacts["pixel"] = {
            "verdict": "not_applicable_generated_media",
            "pixel_verdict": "not_applicable",
            "diff_ratio": 0,
            "comparison_coverage": 0,
            "eligible_non_generated_media_px": 0,
            "generated_media_coverage": 1.0,
            "auto_generated_media_masks": ["hero.photo"],
            "pixel_evidence_applicable": False,
        }

        result, _ = self.run_gate(artifacts, expect_code=0)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(
            result["metrics"]["pixel"]["verdict"],
            "not_applicable_generated_media",
        )

    def test_fabricated_generated_media_not_applicable_verdict_cannot_bypass_g3(self):
        artifacts = base_artifacts()
        artifacts["pixel"] = {
            "verdict": "not_applicable_generated_media",
            "pixel_verdict": "not_applicable",
            "diff_ratio": 0,
            "comparison_coverage": 0,
            "eligible_non_generated_media_px": 0,
            "generated_media_coverage": 1.0,
            "auto_generated_media_masks": ["fake.photo"],
            "pixel_evidence_applicable": False,
        }

        result, _ = self.run_gate(artifacts, expect_code=1)

        self.assertIn(
            "G3 FV pixel diff verdict 'not_applicable_generated_media'",
            "\n".join(result["prototype_reasons"]),
        )

    def test_blocked_when_fused_background_is_reused_as_clean_subcrop(self):
        artifacts = base_artifacts()
        artifacts["manifest"]["photoLed"] = True
        crop = self.work / "assets" / "hero-crop.png"
        source = self.work / "mockups" / "section-01-hero.png"
        review = self.work / "reports" / "photo-asset-review.md"
        pair = self.work / "reports" / "crops" / "hero-photo-pair.png"
        crop.parent.mkdir(parents=True, exist_ok=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        pair.parent.mkdir(parents=True, exist_ok=True)
        crop.write_bytes(b"png")
        source.write_bytes(b"comp")
        review.write_text("# hero.photo\nclean pixels, changed composition\n", encoding="utf-8")
        pair.write_bytes(b"pair")
        artifacts["manifest"]["elements"].append(
            {
                "id": "hero.photo",
                "mediaClass": "photo",
                "qaPriority": "fv-critical",
                "sourceImage": str(source),
                "assetStrategy": "crop-asset",
                "visualRole": "background-environment",
                "sourceFrameHasForegroundOverlap": True,
                "sourceFrameOverlapKinds": ["structural-text", "cta"],
                "cleanLayeredSource": False,
                "cropPreservesComposition": False,
                "croppedAsset": {
                    "workspacePath": str(crop),
                    "sourcePath": str(source),
                    "sourceRoi": "590,185,720,550",
                    "contaminationCheck": {
                        "method": "crop_asset.py + 200% sweep",
                        "verdict": "clean",
                    },
                    "reviewPath": str(review),
                    "pairPath": str(pair),
                },
            }
        )

        result, _ = self.run_gate(artifacts, expect_code=2)

        self.assertEqual(result["status"], "blocked")
        reasons = "\n".join(result["blocked_reasons"])
        self.assertIn("G9 asset policy 'hero.photo'", reasons)
        self.assertIn("clean-looking subcrop", reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
