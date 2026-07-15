#!/usr/bin/env python3
"""Regression tests for the pre-CSS photo/illustration asset gate."""
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
WORK_ROOT = ROOT / "test" / "work" / "asset_preflight"


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_png(path, width=40, height=30, border=(242, 236, 224, 255), center=(40, 80, 180, 255)):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            pixel = center if width // 4 <= x < width * 3 // 4 and height // 4 <= y < height * 3 // 4 else border
            row.extend(pixel)
        rows.append(b"\x00" + bytes(row))
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + chunk(b"IEND", b"")
    )


class AssetPreflightTests(unittest.TestCase):
    def setUp(self):
        self.work = WORK_ROOT / self._testMethodName
        if self.work.exists():
            shutil.rmtree(self.work)
        (self.work / "assets").mkdir(parents=True)
        (self.work / "reports" / "crops").mkdir(parents=True)
        (self.work / "reports" / "photo-asset-review.md").write_text(
            "# Photo asset review\n", encoding="utf-8"
        )
        (self.work / "reports" / "crops" / "photo-pair.png").write_bytes(b"pair")

    def run_preflight(self, manifest, expected_code, infer_photo_led=True):
        source = self.work / "mockups" / "source-comp.png"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"comp")
        manifest.setdefault("image", str(source))
        if infer_photo_led:
            manifest.setdefault(
                "photoLed",
                any(
                    element.get("mediaClass") in {"photo", "illustration"}
                    for element in manifest.get("elements", [])
                ),
            )
        manifest_path = self.work / "manifest.json"
        out_path = self.work / "reports" / "asset-preflight.json"
        write_json(manifest_path, manifest)
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/asset_preflight.py",
                str(manifest_path),
                "--work-root",
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
        return json.loads(out_path.read_text(encoding="utf-8"))

    def crop_evidence(self, name):
        path = self.work / "assets" / f"{name}.png"
        source = self.work / "mockups" / f"{name}-source.png"
        source.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"png")
        source.write_bytes(b"source")
        return {
            "workspacePath": str(path),
            "sourcePath": str(source),
            "sourceRoi": "590,185,720,550",
            "contaminationCheck": {
                "method": "crop_asset.py + 200% sweep",
                "verdict": "clean",
            },
            "reviewPath": str(self.work / "reports" / "photo-asset-review.md"),
            "pairPath": str(self.work / "reports" / "crops" / "photo-pair.png"),
        }

    def generated_surface_element(self, mode, background=(242, 236, 224, 255)):
        asset = self.work / "assets" / "surface.png"
        write_png(asset, border=background)
        edge_value = {
            "alpha_floating": "alpha",
            "opaque_full_bleed": "bleed",
            "opaque_masked_merge": "mask",
            "opaque_tone_matched": "tone_match",
            "intentional_frame": "source_frame",
        }[mode]
        return {
            "id": "card.artwork",
            "mediaClass": "illustration",
            "qaPriority": "section-critical",
            "assetStrategy": "generated",
            "visualRole": "contained-photo",
            "sourceFrameHasForegroundOverlap": False,
            "cleanLayeredSource": False,
            "generatedAsset": {
                "prompt": "clean card artwork, no structural text",
                "sourceImage": str(self.work / "mockups" / "source-comp.png"),
                "workspacePath": str(asset),
                "generator": "imagegen",
                "contaminationCheck": {"method": "200% sweep", "verdict": "clean"},
                "reviewPath": str(self.work / "reports" / "photo-asset-review.md"),
                "pairPath": str(self.work / "reports" / "crops" / "photo-pair.png"),
            },
            "assetUnit": {
                "kind": "card_artwork_plate",
                "splitPolicy": "keep-together",
                "members": ["artwork", "local surface"],
                "independentBehavior": {
                    "motion": False,
                    "responsiveRecompose": False,
                    "reuse": False,
                    "interaction": False,
                    "contentUpdate": False,
                    "layering": False,
                },
                "keepTogetherReason": "The artwork and local surface move as one card interior.",
                "sourceEvidencePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
            },
            "assetSurfaceContract": {
                "consumerIds": ["card.artwork"],
                "consumerOwnsFrame": True,
                "consumerOwnsBackground": True,
                "assetMustBleedToEdges": False,
                "assetMustNotContainPanel": True,
                "assetMustNotContainPadding": True,
                "reviewPath": str(self.work / "reports" / "photo-asset-review.md"),
            },
            "surfaceIntegration": {
                "mode": mode,
                "sourceTopology": "contained_artwork",
                "sourceTopologyEvidencePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
                "edgePolicy": {
                    "top": edge_value,
                    "right": edge_value,
                    "bottom": edge_value,
                    "left": edge_value,
                },
                "consumerSurfaceOwner": "css",
                "outerWhitespaceOwner": "css",
                "cropInUsePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
            },
        }

    def test_blocks_listening_work_lab_clean_subcrops_from_fused_photo_fields(self):
        # Regression for the Listening Work Lab run: the adopted bitmaps were
        # called clean, but escaped foreground overlap by discarding parts of
        # the intended environment/framing and changing composition.
        cases = {
            "hero.photo": ["structural-text", "nav", "cta", "watermark"],
            "gap.photo": ["card", "other"],
            "vision.photo": ["structural-text", "watermark", "other"],
            "cta.photo": ["structural-text", "logo", "cta", "ui", "watermark"],
        }
        elements = []
        for element_id, overlap_kinds in cases.items():
            elements.append(
                {
                    "id": element_id,
                    "mediaClass": "photo",
                    "qaPriority": "fv-critical" if element_id == "hero.photo" else "section-critical",
                    "assetStrategy": "crop-asset",
                    "visualRole": "contained-photo" if element_id == "gap.photo" else "background-environment",
                    "sourceFrameHasForegroundOverlap": True,
                    "sourceFrameOverlapKinds": overlap_kinds,
                    "cleanLayeredSource": False,
                    "cropPreservesComposition": False,
                    "croppedAsset": self.crop_evidence(element_id.replace(".", "-")),
                }
            )
        result = self.run_preflight({"mode": "hybrid", "elements": elements}, 2)

        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["implementationAllowed"])
        blocked = {
            (row.get("elementId"), row["id"])
            for row in result["checks"]
            if row["status"] == "blocked"
        }
        for element_id in cases:
            self.assertIn((element_id, "asset-overlap-crop-forbidden"), blocked)
            self.assertIn((element_id, "asset-crop-composition-unproven"), blocked)

    def test_blocks_old_manifest_shape_before_css(self):
        manifest = {
            "mode": "hybrid",
            "elements": [
                {
                    "id": "hero.photo",
                    "mediaClass": "photo",
                    "qaPriority": "fv-critical",
                    "assetStrategy": "crop-asset",
                }
            ],
        }
        result = self.run_preflight(manifest, 2)
        ids = {row["id"] for row in result["checks"]}
        self.assertEqual(ids, {"asset-decision-fields-missing"})
        self.assertEqual(
            set(result["checks"][0]["missing"]),
            {"sourceFrameHasForegroundOverlap", "cleanLayeredSource", "visualRole"},
        )

    def test_blocks_manifest_without_explicit_photo_led_declaration(self):
        result = self.run_preflight(
            {"mode": "hybrid", "elements": []}, 2, infer_photo_led=False
        )
        self.assertIn(
            "photo-led-declaration-missing",
            {row["id"] for row in result["checks"]},
        )

    def test_blocks_photo_led_manifest_with_zero_photo_rows(self):
        result = self.run_preflight(
            {
                "mode": "hybrid",
                "photoLed": True,
                "elements": [
                    {
                        "id": "hero.lettering",
                        "mediaClass": "lettering-decal",
                        "assetStrategy": "generated",
                    }
                ],
            },
            2,
        )
        self.assertIn(
            "photo-led-assets-missing",
            {row["id"] for row in result["checks"]},
        )

    def test_blocks_lettering_decal_without_asset_and_exact_text_proof(self):
        result = self.run_preflight(
            {
                "mode": "hybrid",
                "photoLed": False,
                "elements": [
                    {
                        "id": "hero.lettering",
                        "mediaClass": "lettering-decal",
                        "assetStrategy": "generated",
                        "text": {"content": "聴くから、つながる。"},
                    }
                ],
            },
            2,
        )
        ids = {row["id"] for row in result["checks"]}
        self.assertIn("lettering-proof-fields-missing", ids)

    def test_allows_verified_generated_lettering_decal(self):
        asset = self.work / "assets" / "hero-lettering.png"
        asset.write_bytes(b"png")
        result = self.run_preflight(
            {
                "mode": "hybrid",
                "photoLed": False,
                "elements": [
                    {
                        "id": "hero.lettering",
                        "mediaClass": "lettering-decal",
                        "assetStrategy": "generated",
                        "text": {"content": "聴くから、つながる。"},
                        "letteringProof": {
                            "exactText": "聴くから、つながる。",
                            "method": "200% glyph-by-glyph crop comparison",
                            "pairPath": str(self.work / "reports" / "crops" / "photo-pair.png"),
                        },
                        "generatedAsset": {
                            "prompt": "exact Japanese lettering, transparent background",
                            "workspacePath": str(asset),
                            "generator": "imagegen",
                        },
                    }
                ],
            },
            0,
        )
        self.assertEqual(result["status"], "pass")

    def test_allows_clean_contained_crop_with_composition_evidence(self):
        manifest = {
            "mode": "hybrid",
            "elements": [
                {
                    "id": "gap.photo",
                    "mediaClass": "photo",
                    "qaPriority": "section-critical",
                    "assetStrategy": "crop-asset",
                    "visualRole": "contained-photo",
                    "sourceFrameHasForegroundOverlap": False,
                    "cleanLayeredSource": False,
                    "cropPreservesComposition": True,
                    "croppedAsset": self.crop_evidence("gap-photo"),
                }
            ],
        }
        result = self.run_preflight(manifest, 0)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["implementationAllowed"])

    def test_allows_verified_generated_clean_plate(self):
        element = self.generated_surface_element("opaque_full_bleed")
        element.update({
            "id": "hero.photo",
            "mediaClass": "photo",
            "qaPriority": "fv-critical",
            "visualRole": "background-environment",
            "sourceFrameHasForegroundOverlap": True,
            "sourceFrameOverlapKinds": ["structural-text", "nav", "cta"],
            "copySpace": [
                {"for": "hero.heading", "roi": {"x": 0, "y": 0, "w": 16, "h": 16}, "minClearance": 4}
            ],
            "assetUnit": {
                "kind": "full_field_scene_plate",
                "splitPolicy": "keep-together",
                "members": ["listening room", "people", "copy-space geometry"],
                "independentBehavior": {
                    "motion": False,
                    "responsiveRecompose": False,
                    "reuse": False,
                    "interaction": False,
                    "contentUpdate": False,
                    "layering": False,
                },
                "keepTogetherReason": "The room and people own one hero field.",
                "sourceEvidencePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
            },
        })
        element["assetSurfaceContract"].update({
            "consumerIds": ["hero.photo"],
            "consumerOwnsFrame": False,
            "consumerOwnsBackground": False,
            "assetMustBleedToEdges": True,
        })
        element["surfaceIntegration"].update({
            "sourceTopology": "section_field",
            "consumerSurfaceOwner": "asset",
            "outerWhitespaceOwner": "none",
        })
        manifest = {"mode": "hybrid", "elements": [element]}
        result = self.run_preflight(manifest, 0)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["completionAllowed"])

    def test_blocks_opaque_uniform_asset_band_when_css_owns_card_padding(self):
        element = self.generated_surface_element("alpha_floating")
        result = self.run_preflight({"mode": "hybrid", "elements": [element]}, 2)
        ids = {row["id"] for row in result["checks"]}
        self.assertIn("surface-alpha-required", ids)
        self.assertIn("surface-double-padding-risk", ids)
        surface = next(row for row in result["checks"] if row["id"] == "surface-double-padding-risk")
        self.assertGreaterEqual(surface["pixelMetrics"]["uniformOuterBandFraction"], 0.04)

    def test_blocks_tone_matched_asset_when_edge_color_differs_from_web_surface(self):
        element = self.generated_surface_element("opaque_tone_matched")
        element["surfaceIntegration"].update({
            "consumerBackgroundColor": "#ffffff",
            "edgeColorTolerance": 8,
        })
        result = self.run_preflight({"mode": "hybrid", "elements": [element]}, 2)
        self.assertIn("surface-edge-color-mismatch", {row["id"] for row in result["checks"]})

    def test_allows_transparent_floating_artwork_on_css_owned_surface(self):
        element = self.generated_surface_element("alpha_floating", background=(0, 0, 0, 0))
        result = self.run_preflight({"mode": "hybrid", "elements": [element]}, 0)
        surface = next(row for row in result["checks"] if row["id"] == "surface-integration-valid")
        self.assertGreater(surface["pixelMetrics"]["transparentPixelFraction"], 0.01)
        receipt = result["inputs"]["assets"][0]
        asset = Path(element["generatedAsset"]["workspacePath"])
        self.assertEqual(receipt["elementId"], element["id"])
        self.assertEqual(receipt["path"], str(asset))
        self.assertEqual(receipt["size"], asset.stat().st_size)
        self.assertEqual(receipt["sha256"], hashlib.sha256(asset.read_bytes()).hexdigest())

    def test_blocks_section_field_demoted_to_an_invented_image_frame(self):
        element = self.generated_surface_element("intentional_frame")
        element["visualRole"] = "background-environment"
        element["surfaceIntegration"].update({
            "sourceTopology": "section_field",
            "sourceFrameVisible": True,
            "sourceEvidencePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
        })
        result = self.run_preflight({"mode": "hybrid", "elements": [element]}, 2)
        ids = {row["id"] for row in result["checks"]}
        self.assertIn("surface-topology-mode-conflict", ids)
        self.assertIn("surface-section-field-invented-frame", ids)
        self.assertIn("surface-section-field-must-bleed", ids)

    def test_blocks_floating_scene_with_an_opaque_generated_background(self):
        element = self.generated_surface_element("alpha_floating")
        element["assetSurfaceContract"]["consumerOwnsFrame"] = False
        element["surfaceIntegration"]["sourceTopology"] = "floating_scene"
        element["assetUnit"] = {
            "kind": "transparent_scene",
            "splitPolicy": "keep-together",
            "members": ["exploded panels", "soft shadows"],
            "independentBehavior": {
                "motion": False,
                "responsiveRecompose": False,
                "reuse": False,
                "interaction": False,
                "contentUpdate": False,
                "layering": False,
            },
            "keepTogetherReason": "The diagram and its shadows move as one scene.",
            "sourceEvidencePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
        }
        result = self.run_preflight({"mode": "hybrid", "elements": [element]}, 2)
        self.assertIn("surface-alpha-required", {row["id"] for row in result["checks"]})

    def test_allows_transparent_scene_with_shadow_alpha_on_the_web_field(self):
        element = self.generated_surface_element("alpha_floating", background=(0, 0, 0, 0))
        element["assetSurfaceContract"]["consumerOwnsFrame"] = False
        element["surfaceIntegration"]["sourceTopology"] = "floating_scene"
        element["assetUnit"] = {
            "kind": "transparent_scene",
            "splitPolicy": "keep-together",
            "members": ["paper object", "soft shadow"],
            "independentBehavior": {
                "motion": False,
                "responsiveRecompose": False,
                "reuse": False,
                "interaction": False,
                "contentUpdate": False,
                "layering": False,
            },
            "keepTogetherReason": "The paper object and shadow form one floating scene.",
            "sourceEvidencePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
        }
        result = self.run_preflight({"mode": "hybrid", "elements": [element]}, 0)
        self.assertEqual(result["status"], "pass")

    def test_allows_full_field_scene_with_copy_space_and_asset_owned_bleed(self):
        element = self.generated_surface_element("opaque_full_bleed")
        element["visualRole"] = "background-environment"
        element["assetSurfaceContract"].update({
            "consumerOwnsFrame": False,
            "consumerOwnsBackground": False,
            "assetMustBleedToEdges": True,
        })
        element["surfaceIntegration"].update({
            "sourceTopology": "section_field",
            "consumerSurfaceOwner": "asset",
            "outerWhitespaceOwner": "none",
        })
        element["assetUnit"] = {
            "kind": "full_field_scene_plate",
            "splitPolicy": "keep-together",
            "members": ["device scene", "studio environment", "contact shadows"],
            "independentBehavior": {
                "motion": False,
                "responsiveRecompose": False,
                "reuse": False,
                "interaction": False,
                "contentUpdate": False,
                "layering": False,
            },
            "keepTogetherReason": "The scene owns the full hero field.",
            "sourceEvidencePath": str(self.work / "reports" / "crops" / "photo-pair.png"),
        }
        element["copySpace"] = [
            {"for": "hero.heading", "roi": {"x": 0, "y": 0, "w": 16, "h": 16}, "minClearance": 4}
        ]
        result = self.run_preflight({"mode": "hybrid", "elements": [element]}, 0)
        self.assertEqual(result["status"], "pass")

    def test_placeholder_requires_failed_generation_and_never_allows_completion(self):
        element = {
            "id": "hero.photo",
            "mediaClass": "photo",
            "qaPriority": "fv-critical",
            "assetStrategy": "placeholder",
            "visualRole": "background-environment",
            "sourceFrameHasForegroundOverlap": True,
            "sourceFrameOverlapKinds": ["structural-text"],
            "cleanLayeredSource": False,
        }
        blocked = self.run_preflight({"mode": "hybrid", "elements": [element]}, 2)
        self.assertEqual(blocked["status"], "blocked")

        element["generationAttempts"] = [
            {
                "generator": "imagegen",
                "prompt": "clean listening room, no text or UI",
                "status": "failed",
                "error": "generation service unavailable",
            }
        ]
        earned = self.run_preflight({"mode": "hybrid", "elements": [element]}, 1)
        self.assertEqual(earned["status"], "needs_work")
        self.assertTrue(earned["implementationAllowed"])
        self.assertFalse(earned["completionAllowed"])

    def test_clean_layered_source_claim_cannot_point_back_to_fused_comp(self):
        crop = self.crop_evidence("hero-layer-claim")
        fused = self.work / "mockups" / "source-comp.png"
        crop["sourcePath"] = str(fused)
        manifest = {
            "mode": "hybrid",
            "image": str(fused),
            "elements": [
                {
                    "id": "hero.photo",
                    "mediaClass": "photo",
                    "qaPriority": "fv-critical",
                    "assetStrategy": "crop-asset",
                    "visualRole": "background-environment",
                    "sourceFrameHasForegroundOverlap": True,
                    "sourceFrameOverlapKinds": ["structural-text", "cta"],
                    "cleanLayeredSource": True,
                    "cropPreservesComposition": True,
                    "croppedAsset": crop,
                }
            ],
        }
        result = self.run_preflight(manifest, 2)
        self.assertIn(
            "clean-layered-source-proof-invalid",
            {row["id"] for row in result["checks"]},
        )

    def test_crop_checker_never_self_approves_pixel_clean_crop(self):
        source = (ROOT / "scripts" / "crop_asset.py").read_text(encoding="utf-8")
        self.assertNotIn('"usable_as_is"', source)
        self.assertIn('"run_asset_preflight_before_adoption"', source)
        self.assertIn('"adoption_allowed": False', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
