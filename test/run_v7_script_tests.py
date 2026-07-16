#!/usr/bin/env python3
"""Regression tests for v7 measurement/QA script behavior."""
import json
import hashlib
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / "test" / "work" / "v7"


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class V7ScriptTests(unittest.TestCase):
    def setUp(self):
        self.work = WORK_ROOT / self._testMethodName
        if self.work.exists():
            shutil.rmtree(self.work)
        self.work.mkdir(parents=True)

    def run_box_diff(self, manifest, rects):
        manifest_path = self.work / "manifest.json"
        rects_path = self.work / "rects.json"
        out_path = self.work / "box-report.json"
        write_json(manifest_path, manifest)
        write_json(rects_path, rects)
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/box_diff.py",
                str(manifest_path),
                str(rects_path),
                "--section-relative",
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return read_json(out_path), proc

    def run_visual_check(self, html, manifest, expect_code, widths="1728"):
        html_path = self.work / "fixture.html"
        manifest_path = self.work / "manifest.json"
        out_path = self.work / "visual-check.json"
        html_path.write_text(html, encoding="utf-8")
        write_json(manifest_path, manifest)
        proc = subprocess.run(
            [
                "node",
                "scripts/visual-check.mjs",
                "--html",
                str(html_path),
                "--manifest",
                str(manifest_path),
                "--widths",
                widths,
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=90,
        )
        self.assertEqual(proc.returncode, expect_code, proc.stdout + proc.stderr)
        return read_json(out_path), proc

    def test_box_diff_waives_non_fv_child_y_when_section_recomposes_taller(self):
        manifest = {
            "referenceImages": [
                {"path": "section-02.png", "use": "section-comp", "section": "section-2"}
            ],
            "elements": [
                {
                    "id": "section-2",
                    "el": "section-2",
                    "sourceImage": "section-02.png",
                    "priority": "critical",
                    "bbox": {"x": 0, "y": 0, "w": 1440, "h": 810},
                },
                {
                    "id": "regular-child",
                    "el": "regular-child",
                    "sourceImage": "section-02.png",
                    "priority": "critical",
                    "qaPriority": "section-critical",
                    "bbox": {"x": 120, "y": 120, "w": 320, "h": 80},
                },
                {
                    "id": "fv-child",
                    "el": "fv-child",
                    "sourceImage": "section-02.png",
                    "priority": "critical",
                    "qaPriority": "fv-critical",
                    "bbox": {"x": 620, "y": 120, "w": 320, "h": 80},
                },
            ],
        }
        rects = {
            "rects": [
                {"el": "section-2", "x": 0, "y": 500, "w": 1440, "h": 980},
                {"el": "regular-child", "x": 120, "y": 700, "w": 320, "h": 80},
                {"el": "fv-child", "x": 620, "y": 700, "w": 320, "h": 80},
            ]
        }
        report, _ = self.run_box_diff(manifest, rects)
        by_id = {item["id"]: item for item in report["items"]}

        self.assertTrue(by_id["regular-child"]["pass"])
        self.assertTrue(by_id["regular-child"]["y_waived_recomposition"])
        self.assertNotIn("y", by_id["regular-child"]["failed_axes"])
        self.assertFalse(by_id["fv-child"]["pass"])
        self.assertIn("y", by_id["fv-child"]["failed_axes"])
        self.assertEqual(report["summary"]["y_waived_recomposition"], 1)

    def test_box_diff_collapsed_section_root_reports_density_floor_fix(self):
        manifest = {
            "referenceImages": [
                {"path": "section-03.png", "use": "section-comp", "section": "section-3"}
            ],
            "elements": [
                {
                    "id": "section-3",
                    "el": "section-3",
                    "sourceImage": "section-03.png",
                    "priority": "critical",
                    "bbox": {"x": 0, "y": 0, "w": 1440, "h": 810},
                }
            ],
        }
        rects = {
            "rects": [
                {"el": "section-3", "x": 0, "y": 1200, "w": 1440, "h": 700}
            ]
        }
        report, _ = self.run_box_diff(manifest, rects)

        self.assertEqual(report["summary"]["fail"], 1)
        self.assertEqual(report["first_fix"]["id"], "section-3")
        instruction = report["first_fix"]["instruction"]
        self.assertIn("density-floor failure", instruction)
        self.assertIn("section collapsed below its comp frame's height", instruction)
        self.assertIn("Restore type scale", instruction)

    def test_box_diff_treats_viewport_global_header_outside_section_as_global(self):
        manifest = {
            "referenceImages": [
                {"path": "section-01.png", "use": "section-comp", "section": "hero"}
            ],
            "elements": [
                {
                    "id": "hero",
                    "el": "hero",
                    "sourceImage": "section-01.png",
                    "priority": "critical",
                    "bbox": {"x": 0, "y": 0, "w": 1440, "h": 810},
                },
                {
                    "id": "global-header",
                    "el": "global-header",
                    "sourceImage": "section-01.png",
                    "priority": "critical",
                    "qaPriority": "fv-critical",
                    "placementScope": "viewport-fixed",
                    "positioning": "sticky",
                    "bbox": {"x": 40, "y": 0, "w": 1360, "h": 72},
                },
            ],
        }
        rects = {
            "rects": [
                {"el": "global-header", "x": 40, "y": 0, "w": 1360, "h": 72},
                {"el": "hero", "x": 0, "y": 72, "w": 1440, "h": 810},
            ]
        }

        report, _ = self.run_box_diff(manifest, rects)
        header = next(row for row in report["items"] if row["id"] == "global-header")

        self.assertTrue(header["pass"])
        self.assertEqual(header["coordSpace"], "viewport-global")
        self.assertEqual(header["delta"]["y"], 0)

    def test_box_diff_blocks_array_bbox_with_json_report_not_traceback(self):
        manifest_path = self.work / "manifest.json"
        rects_path = self.work / "rects.json"
        out_path = self.work / "box-report.json"
        write_json(
            manifest_path,
            {
                "elements": [
                    {"id": "hero", "el": "hero", "priority": "critical", "bbox": [0, 0, 1440, 810]}
                ]
            },
        )
        write_json(rects_path, {"rects": [{"el": "hero", "x": 0, "y": 0, "w": 1440, "h": 810}]})
        proc = subprocess.run(
            [
                sys.executable,
                "scripts/box_diff.py",
                str(manifest_path),
                str(rects_path),
                "--section-relative",
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )

        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)
        report = read_json(out_path)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["invalidManifest"][0]["path"], "elements[0].bbox")

    def test_box_diff_reports_manifest_tolerance_override_provenance(self):
        manifest = {
            "referenceImages": [
                {"path": "section-01.png", "use": "section-comp", "section": "hero"}
            ],
            "elements": [
                {
                    "id": "hero",
                    "el": "hero",
                    "sourceImage": "section-01.png",
                    "priority": "critical",
                    "bbox": {"x": 0, "y": 0, "w": 1440, "h": 810},
                },
                {
                    "id": "hero-title",
                    "el": "hero-title",
                    "sourceImage": "section-01.png",
                    "priority": "critical",
                    "qaPriority": "fv-critical",
                    "bbox": {"x": 100, "y": 120, "w": 500, "h": 90},
                    "tolerance": {"x": 24, "w": 42},
                    "toleranceReason": "hand-measured glyph crop has soft horizontal edge",
                },
            ],
        }
        rects = {
            "rects": [
                {"el": "hero", "x": 0, "y": 0, "w": 1440, "h": 810},
                {"el": "hero-title", "x": 118, "y": 120, "w": 535, "h": 90},
            ]
        }
        report, _ = self.run_box_diff(manifest, rects)
        by_id = {item["id"]: item for item in report["items"]}

        self.assertTrue(by_id["hero-title"]["pass"])
        self.assertEqual(by_id["hero-title"]["toleranceSource"], "manifest")
        self.assertEqual(by_id["hero-title"]["toleranceOverride"], {"x": 24, "w": 42})
        self.assertEqual(by_id["hero-title"]["toleranceOverriddenAxes"], ["w", "x"])
        self.assertEqual(report["summary"]["tolerance_overrides"], 1)

    def test_visual_check_dead_gutter_and_layout_law_fail_left_pinned_canvas(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
section { position: relative; height: 520px; background: #f8f8f8; }
.canvas { position: absolute; left: 0; top: 0; width: 1440px; height: 520px; background: #e9e9e9; }
.content { width: 1100px; height: 220px; padding: 32px; background: #222; color: #fff; font-size: 48px; }
</style></head>
<body>
<section data-el="hero">
  <div class="canvas" data-el="canvas">
    <div class="content" data-el="headline">Pinned content</div>
  </div>
</section>
</body></html>
"""
        manifest = {
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {"id": "canvas", "el": "canvas", "role": "container"},
                {
                    "id": "headline",
                    "el": "headline",
                    "role": "heading",
                    "text": {"content": "Pinned content"},
                },
            ]
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertIn("dead-gutter", checks)
        self.assertIn("layout-law", checks)

    def test_visual_check_blocks_canonical_heading_line_count_drift(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif}
section{min-height:500px;display:grid;place-items:center}.wrap{width:260px}
h1{margin:0;font-size:52px;line-height:1.05}
</style></head><body><section><div class="wrap">
<h1 data-el="hero-heading">A heading that wraps unexpectedly</h1>
</div></section></body></html>"""
        manifest = {
            "viewport": {"width": 1440},
            "elements": [
                {
                    "id": "hero.heading",
                    "el": "hero-heading",
                    "role": "heading",
                    "qaPriority": "fv-critical",
                    "positioning": "flow",
                    "text": {"content": "A heading that wraps unexpectedly"},
                    "typeSpec": {"expectedVisualLineCount": 1},
                }
            ],
        }

        report, _ = self.run_visual_check(html, manifest, expect_code=1, widths="1440")
        violation = next(
            row for row in report["viewports"][0]["violations"]
            if row["check"] == "typography-line-count"
        )
        self.assertEqual(violation["detail"]["expected"], 1)
        self.assertGreater(violation["detail"]["actual"], 1)

    def test_visual_check_blocks_family_string_when_webfont_face_is_not_loaded(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:Arial,sans-serif}.hero{min-height:900px;padding:120px}
h1{font-family:'Missing Display Face',Arial,sans-serif;font-size:88px;font-weight:700}
</style></head><body><section class="hero"><h1 data-el="hero-heading">Listening care</h1></section></body></html>"""
        manifest = {
            "viewport": {"width": 1440},
            "elements": [{
                "id": "hero.heading",
                "el": "hero-heading",
                "role": "heading",
                "qaPriority": "fv-critical",
                "text": {"content": "Listening care", "fontFamily": "Missing Display Face"},
                "typeSpec": {
                    "fontSelection": {
                        "selectedFamily": "Missing Display Face",
                        "selectedSource": "google-fonts",
                        "requestedWeight": 700,
                        "availableWeights": [700],
                    }
                },
            }],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1, widths="1440")
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertIn("font-face-load", checks)
        self.assertNotIn("font-family", checks)

    def test_visual_check_blocks_flat_typography_hierarchy_whitespace_and_scale(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif}
.hero{height:900px;padding:140px}.title{margin:0;font-size:48px;line-height:1.1;font-weight:700}
.label{margin:20px 0 0;font-size:32px;line-height:1.2;font-weight:600}
</style></head><body><section class="hero">
<h1 class="title" data-el="hero-title">Listen deeply</h1>
<p class="label" data-el="hero-label">Apply free</p>
</section></body></html>"""
        manifest = {
            "viewport": {"width": 1440},
            "elements": [
                {"id": "hero.title", "el": "hero-title", "role": "heading", "text": {"content": "Listen deeply", "fontFamily": "Arial"}},
                {"id": "hero.label", "el": "hero-label", "role": "label", "text": {"content": "Apply free", "fontFamily": "Arial"}},
            ],
            "typographyComposition": [{
                "section": "hero",
                "dominantElementId": "hero.title",
                "hierarchyEdges": [{
                    "from": "hero.title", "to": "hero.label",
                    "sourceSizeRatio": 4.0, "sourceWeightDelta": 400,
                    "sizeTolerance": 0.1, "weightTolerance": 50,
                }],
                "whitespaceEdges": [{
                    "before": "hero.title", "after": "hero.label",
                    "sourceGapToDominantRatio": 0.8, "tolerance": 0.1,
                }],
                "extremeScale": {
                    "required": True,
                    "sourceDominantBlockHeightRatio": 0.2,
                    "maxScaleLossRatio": 0.1,
                },
            }],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1, widths="1440")
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertIn("typography-hierarchy", checks)
        self.assertIn("typography-whitespace", checks)
        self.assertIn("typography-extreme-scale", checks)

    def test_visual_check_blocks_emoji_as_source_specific_line_art(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0}.card{width:320px;padding:30px}.icon{font-size:64px}
</style></head><body><article class="card" data-el="benefit-card">
<i class="icon">🎁</i><h2>3,000pt付与</h2>
</article></body></html>"""
        manifest = {
            "elements": [
                {"id": "benefit.card", "el": "benefit-card", "role": "container"},
            ],
            "detailInventory": [
                {
                    "id": "benefit-gift-device",
                    "section": "benefit",
                    "description": "drawn gift box and point medallion composite",
                    "sourceSpecific": True,
                    "priority": "high",
                    "manifestElementIds": ["benefit.card"],
                    "renderingCraft": {
                        "medium": "line-art",
                        "signatureTraits": ["outlined gift box", "overlapping point medallion"],
                        "minimumAtomicParts": 2,
                        "genericStandInsForbidden": True,
                        "evidencePath": "reports/crops/benefit-gift-source.png",
                    },
                }
            ],
        }

        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        violations = report["viewports"][0]["violations"]
        check = next(row for row in violations if row["check"] == "generic-symbol-standin")
        self.assertEqual(check["id"], "benefit-gift-device")
        self.assertEqual(check["detail"]["standins"][0]["text"], "🎁")

    def test_visual_check_clusters_same_line_runs_with_different_rect_tops(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif}
section{min-height:500px;display:grid;place-items:center}h1{font-size:72px;line-height:1.05}
.small{font-size:.55em;position:relative;top:-8px}
</style></head><body><section>
<h1 data-el="hero-heading"><span>AI</span><span class="small">駆動型へ</span></h1>
</section></body></html>"""
        manifest = {
            "viewport": {"width": 1440},
            "elements": [{
                "id": "hero.heading",
                "el": "hero-heading",
                "role": "heading",
                "qaPriority": "fv-critical",
                "positioning": "flow",
                "text": {"content": "AI駆動型へ"},
                "typeSpec": {"expectedVisualLineCount": 1},
            }],
        }

        report, _ = self.run_visual_check(html, manifest, expect_code=0, widths="1440")
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertNotIn("typography-line-count", checks)

    def test_visual_check_blocks_japanese_orphan_fragment_and_wrong_line_strings(self):
        html = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
body{margin:0;font-family:serif}h1{width:620px;font-size:92px;line-height:1.2}
</style></head><body><h1 data-el="vision-title">孤独を、<br>ひとりで抱えなく<br>て<br>いい社会へ。</h1></body></html>"""
        manifest = {
            "elements": [{
                "id": "vision.title", "el": "vision-title", "role": "heading",
                "qaPriority": "section-critical", "positioning": "flow",
                "text": {"content": "孤独を、ひとりで抱えなくていい社会へ。"},
                "typeSpec": {"responsiveLineContracts": [{
                    "minWidth": 1000, "maxWidth": 1600,
                    "expectedLines": ["孤独を、", "ひとりで抱えなくて", "いい社会へ。"],
                    "forbiddenOrphanFragments": ["て"],
                }]},
            }],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1, widths="1440")
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertIn("typography-responsive-lines", checks)
        self.assertIn("typography-orphan-fragment", checks)

    def test_visual_check_blocks_large_unmanifested_decorative_text(self):
        html = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
body{margin:0}.section{position:relative;height:900px}.ghost{position:absolute;font-size:380px}
</style></head><body><section class="section" data-el="hero"><div class="ghost">聴</div></section></body></html>"""
        manifest = {
            "mode": "hybrid", "referenceImages": [
                {"path": "a.png", "use": "section-comp", "section": "hero"},
                {"path": "b.png", "use": "section-comp", "section": "value"},
            ],
            "elements": [{"id": "hero", "el": "hero", "role": "section", "positioning": "flow"}],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1, widths="1440")
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertIn("unmanifested-large-text-decoration", checks)
        self.assertIn("pipeline-pre-css-contract", checks)

    def test_visual_check_blocks_unevidenced_large_ellipse_pseudo(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0}.cta{position:relative;height:900px}.cta:after{content:"";position:absolute;width:80vw;height:320px;border-radius:50%;background:#cdf;bottom:0}
</style></head><body><section class="cta" data-el="cta"></section></body></html>"""
        manifest = {
            "mode": "hybrid", "referenceImages": [
                {"path": "a.png", "use": "section-comp", "section": "hero"},
                {"path": "b.png", "use": "section-comp", "section": "cta"},
            ],
            "elements": [{"id": "cta", "el": "cta", "role": "section", "positioning": "flow"}],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1, widths="1440")
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertIn("unevidenced-large-ellipse", checks)

    def test_visual_check_blocks_distorted_circle_trapezoid_and_padded_edge_art(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0}.stage{position:relative;min-height:520px}
.arrow{width:48px;height:72px;border:3px solid #29836d;border-radius:50%}
.corner{width:180px;height:120px;background:#52aa8e;clip-path:polygon(0 0,100% 0,72% 100%,0 100%)}
.card{position:relative;width:320px;height:220px;margin-top:30px;padding:24px;background:#fff;border:1px solid #ddd}
.art{width:100%;height:100%;background:#def}
</style></head><body><section class="stage">
<div class="arrow" data-el="flow-arrow"></div>
<div class="corner" data-el="step-corner"></div>
<article class="card" data-el="art-card"><div class="art" data-el="card-art"></div></article>
</section></body></html>"""
        manifest = {"elements": [
            {"id": "flow.arrow", "el": "flow-arrow", "role": "decoration",
             "decorativeCraft": {"microGeometry": {"kind": "circle", "maxAspectRatioError": 0.02, "evidencePath": "circle.png"}}},
            {"id": "step.corner", "el": "step-corner", "role": "decoration",
             "decorativeCraft": {"microGeometry": {"kind": "triangle", "polygonVertexCount": 3, "evidencePath": "triangle.png"}}},
            {"id": "art.card", "el": "art-card", "role": "container"},
            {"id": "card.art", "el": "card-art", "role": "image",
             "surfaceIntegration": {"edgeContact": {"ownerId": "art.card", "edges": ["left", "right", "bottom"], "maxGapPx": 1}}},
        ]}
        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertIn("micro-geometry-circle", checks)
        self.assertIn("micro-geometry-triangle", checks)
        self.assertIn("surface-edge-contact", checks)

    def test_visual_check_blocks_attention_rays_that_grow_from_inside_the_number(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0}.stage{position:relative;min-height:520px}
.number{position:absolute;left:200px;top:180px;width:90px;height:100px;background:#52aa8e}
.rays{position:absolute;left:230px;top:205px;width:48px;height:48px}
.ray{position:absolute;width:4px;height:28px;background:#ffc842;transform-origin:center}
.ray:nth-child(1){left:10px;top:4px;transform:rotate(45deg)}
.ray:nth-child(2){left:20px;top:6px;transform:rotate(55deg)}
.ray:nth-child(3){left:30px;top:10px;transform:rotate(65deg)}
</style></head><body><section class="stage">
<div class="number" data-el="step-number"></div>
<div class="rays" data-el="step-rays"><i class="ray"></i><i class="ray"></i><i class="ray"></i></div>
</section></body></html>"""
        manifest = {"elements": [
            {"id": "step.number", "el": "step-number", "role": "other", "positioning": "absolute"},
            {"id": "step.rays", "el": "step-rays", "role": "decoration", "positioning": "absolute", "layerRole": "decorative",
             "decorativeCraft": {"microGeometry": {
                 "kind": "radial-rays", "evidencePath": "rays.png", "targetId": "step.number",
                 "placementRegion": "upper-right", "directionMode": "radiate-away", "raySelector": ".ray",
                 "rayCount": 3, "sharedOrigin": False, "mustNotOverlapTarget": True,
                 "maxDirectionErrorDeg": 22, "minRayCenterSeparationPx": 8,
             }}},
        ]}
        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertIn("micro-geometry-radial-overlap", checks)

    def test_visual_check_allows_separated_upper_right_radial_attention_rays(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0}.stage{position:relative;min-height:520px}
.number{position:absolute;left:180px;top:210px;width:80px;height:90px;background:#52aa8e}
.rays{position:absolute;left:275px;top:130px;width:95px;height:80px}
.ray{position:absolute;width:4px;height:28px;background:#ffc842;transform-origin:center}
.ray:nth-child(1){left:8px;top:38px;transform:rotate(48deg)}
.ray:nth-child(2){left:38px;top:18px;transform:rotate(55deg)}
.ray:nth-child(3){left:70px;top:2px;transform:rotate(61deg)}
</style></head><body><section class="stage">
<div class="number" data-el="step-number"></div>
<div class="rays" data-el="step-rays"><i class="ray"></i><i class="ray"></i><i class="ray"></i></div>
</section></body></html>"""
        manifest = {"elements": [
            {"id": "step.number", "el": "step-number", "role": "other", "positioning": "absolute"},
            {"id": "step.rays", "el": "step-rays", "role": "decoration", "positioning": "absolute", "layerRole": "decorative",
             "decorativeCraft": {"microGeometry": {
                 "kind": "radial-rays", "evidencePath": "rays.png", "targetId": "step.number",
                 "placementRegion": "upper-right", "directionMode": "radiate-away", "raySelector": ".ray",
                 "rayCount": 3, "sharedOrigin": False, "mustNotOverlapTarget": True,
                 "maxDirectionErrorDeg": 25, "minRayCenterSeparationPx": 12,
             }}},
        ]}
        report, _ = self.run_visual_check(html, manifest, expect_code=0)
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertFalse(any(check.startswith("micro-geometry-radial") for check in checks))

    def test_visual_check_centered_flow_page_passes_dead_gutter_and_layout_law(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
section { min-height: 520px; background: #f8f8f8; }
.container { width: min(100%, 1440px); height: 520px; margin-inline: auto; display: flex; align-items: center; }
.content { width: min(1100px, 100%); height: 220px; padding: 32px; background: #222; color: #fff; font-size: 48px; }
</style></head>
<body>
<section data-el="hero">
  <div class="container" data-el="container">
    <div class="content" data-el="headline">Centered content</div>
  </div>
</section>
</body></html>
"""
        manifest = {
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {"id": "container", "el": "container", "role": "container"},
                {
                    "id": "headline",
                    "el": "headline",
                    "role": "heading",
                    "text": {"content": "Centered content"},
                },
            ]
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=0)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertNotIn("dead-gutter", checks)
        self.assertNotIn("layout-law", checks)

    def test_visual_check_listening_work_lab_tablet_clip_cannot_hide_fixed_grids(self):
        """Regression for the Listening Work Lab 768/1024px false pass.

        The real page placed 1320px/1313px grids behind html/body overflow-x:clip.
        documentElement.scrollWidth therefore looked safe even though the diagram
        and work list lost most of their right side.
        """
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:clip}body{margin:0;font-family:Arial,sans-serif}
section{width:100%;min-height:500px}.about__grid{display:grid;width:1320px;grid-template-columns:440px 787px;gap:0}
.about__copy{min-height:300px}.about__diagram{width:787px;min-height:420px;background:#eef8ff}
.work__grid{display:grid;width:1313px;grid-template-columns:360px 849px;gap:104px}
.work__copy{min-height:300px}.work__list{width:849px;min-height:420px;background:#eef8f1}
</style></head><body>
<main>
  <section data-el="about-lab"><div class="about__grid">
    <div class="about__copy"></div><div class="about__diagram" data-el="about-diagram">探究・実践・接続</div>
  </div></section>
  <section data-el="work-examples"><div class="work__grid">
    <div class="work__copy"></div><div class="work__list" data-el="work-photo">聴く仕事の一覧</div>
  </div></section>
</main>
</body></html>"""
        manifest = {
            "elements": [
                {"id": "section.about", "el": "about-lab", "role": "section", "positioning": "flow"},
                {"id": "about.diagram", "el": "about-diagram", "role": "other", "qaPriority": "section-critical", "positioning": "flow"},
                {"id": "section.work", "el": "work-examples", "role": "section", "positioning": "flow"},
                {"id": "work.photo", "el": "work-photo", "role": "image", "qaPriority": "section-critical", "positioning": "flow"},
            ]
        }
        report, _ = self.run_visual_check(
            html, manifest, expect_code=1, widths="768,1024"
        )
        self.assertEqual([row["viewport"] for row in report["viewports"]], ["768x900", "1024x900"])
        for viewport in report["viewports"]:
            violation = next(
                row for row in viewport["violations"]
                if row["check"] == "responsive-visible-ratio"
            )
            items = {row["id"]: row for row in violation["detail"]["items"]}
            self.assertIn("about.diagram", items)
            self.assertIn("work.photo", items)
            self.assertLess(items["about.diagram"]["visibleRatio"], 0.8)
            self.assertLess(items["work.photo"]["visibleRatio"], 0.7)
            self.assertTrue(
                viewport["responsiveMetrics"]["rootOverflowX"]["suppressesHorizontalOverflow"]
            )
            self.assertIn(
                viewport["responsiveMetrics"]["rootOverflowX"]["html"],
                {"hidden", "clip"},
            )
            self.assertIn("body", viewport["responsiveMetrics"]["scrollWidths"])

    def test_visual_check_allows_declared_full_bleed_decoration_at_320(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:clip}body{margin:0;font-family:Arial,sans-serif}
.hero{position:relative;width:100%;min-height:480px;overflow:hidden}.bleed{position:absolute;left:50%;top:0;width:900px;height:480px;transform:translateX(-50%);background:#dff4ef}
.content{position:relative;width:calc(100% - 40px);margin:auto;padding-top:120px}.content h1{margin:0;font-size:42px}.content a{display:inline-block;margin-top:24px}
</style></head><body>
<section class="hero" data-el="hero"><div class="bleed" data-el="hero-photo" aria-hidden="true"></div>
  <div class="content"><h1 data-el="hero-title">聴く仕事ラボ</h1><a href="#details">詳しく見る</a></div>
</section><section id="details">詳細</section>
</body></html>"""
        manifest = {
            "elements": [
                {"id": "hero", "el": "hero", "role": "section", "positioning": "flow"},
                {
                    "id": "hero.photo",
                    "el": "hero-photo",
                    "role": "decoration",
                    "positioning": "absolute",
                    "layerRole": "background-photo",
                    "backgroundBehavior": "full-bleed",
                },
                {"id": "hero.title", "el": "hero-title", "role": "heading", "positioning": "flow"},
            ]
        }
        report, _ = self.run_visual_check(
            html, manifest, expect_code=0, widths="320"
        )
        checks = {row["check"] for row in report["viewports"][0]["violations"]}
        self.assertNotIn("responsive-visible-ratio", checks)
        self.assertNotIn("no-h-scroll", checks)
        self.assertEqual(report["viewports"][0]["responsiveMetrics"]["clippedMeaningfulCount"], 0)

    def test_visual_check_blocks_missing_same_document_fragment(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:Arial,sans-serif}nav{padding:24px}
</style></head><body><nav><a href="#top">Top</a><a href="#about">About</a><a href="#journal">Journal</a></nav>
<main id="about">About content</main></body></html>"""
        report, _ = self.run_visual_check(
            html, {"elements": []}, expect_code=1, widths="320"
        )
        violation = next(
            row for row in report["viewports"][0]["violations"]
            if row["check"] == "same-document-fragment"
        )
        self.assertEqual(violation["detail"], [
            {"href": "#journal", "fragment": "#journal", "text": "Journal"}
        ])

    def test_visual_check_blocks_section_clip_without_page_composition_owner(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0}section{width:100%;min-height:600px;overflow:hidden;background:#fff}
</style></head><body><section data-el="hero"></section></body></html>"""
        manifest = {
            "referenceImages": [
                {"path": "hero.png", "use": "section-comp", "section": "hero"}
            ],
            "pageComposition": {
                "sections": [
                    {"section": "hero", "heightStrategy": "content-led", "density": "balanced", "overflowPolicy": "visible"}
                ]
            },
            "elements": [
                {"id": "hero", "el": "hero", "role": "section", "positioning": "flow"}
            ],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertIn("section-overflow-policy", checks)

    def test_visual_check_allows_evidenced_section_clip_owner(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0}section{width:100%;min-height:600px;overflow:hidden;background:#fff}
</style></head><body><section data-el="hero"></section></body></html>"""
        manifest = {
            "referenceImages": [
                {"path": "hero.png", "use": "section-comp", "section": "hero"}
            ],
            "pageComposition": {
                "sections": [
                    {"section": "hero", "heightStrategy": "viewport-chapter", "density": "balanced", "overflowPolicy": "clip", "clipReason": "Approved rounded chapter frame owns the crop."}
                ]
            },
            "elements": [
                {"id": "hero", "el": "hero", "role": "section", "positioning": "flow"}
            ],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=0)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertNotIn("section-overflow-policy", checks)

    def test_visual_check_declared_fixed_global_ui_passes_layout_law(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
.global-nav { position: fixed; right: 24px; top: 24px; z-index: 10; padding: 12px 18px; background: #fff; }
.vertical-logo { position: fixed; left: 20px; top: 80px; z-index: 10; writing-mode: vertical-rl; }
section { min-height: 520px; background: #f8f8f8; }
.container { width: min(100%, 1440px); height: 520px; margin-inline: auto; display: flex; align-items: center; }
.headline { font-size: 64px; }
</style></head>
<body>
<nav class="global-nav" data-el="global-nav">Nav</nav>
<div class="vertical-logo" data-el="vertical-logo">Listening Lab</div>
<section data-el="hero">
  <div class="container">
    <h1 class="headline" data-el="headline">Listen</h1>
  </div>
</section>
</body></html>
"""
        manifest = {
            "referenceImages": [
                {"path": "section-01.png", "use": "section-comp", "section": "hero"}
            ],
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {
                    "id": "global-nav",
                    "el": "global-nav",
                    "role": "nav",
                    "positioning": "fixed",
                    "placementScope": "viewport-fixed",
                    "layerRole": "header-nav",
                },
                {
                    "id": "vertical-logo",
                    "el": "vertical-logo",
                    "role": "label",
                    "positioning": "fixed",
                    "placementScope": "viewport-edge",
                    "layerRole": "vertical-label",
                },
                {"id": "headline", "el": "headline", "role": "heading"},
            ],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=0)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertNotIn("layout-law", checks)

    def test_visual_check_lettering_decal_does_not_require_dom_copy(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
section { min-height: 520px; background: #f8f8f8; position: relative; }
.bubble { width: 220px; height: 80px; margin: 120px; background: rgba(120, 180, 120, .18); }
</style></head>
<body>
<section data-el="hero">
  <div class="bubble" data-el="lettering-bubble" aria-hidden="true"></div>
</section>
</body></html>
"""
        manifest = {
            "referenceImages": [
                {"path": "section-01.png", "use": "section-comp", "section": "hero"}
            ],
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {
                    "id": "lettering-bubble",
                    "el": "lettering-bubble",
                    "role": "decoration",
                    "mediaClass": "lettering-decal",
                    "textRecreation": "lettering-decal",
                    "assetStrategy": "generated",
                    "text": {"content": "聴くから、つながる。"},
                },
            ],
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=0)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertNotIn("copy", checks)

    def test_visual_check_blocks_structural_text_scale_and_translate(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
section { min-height: 520px; display: grid; place-items: center; background: #f8f8f8; }
.headline { display: inline-block; font: 700 72px/1 Arial, sans-serif; transform: translateY(24px) scaleY(1.24); }
</style></head><body>
<section data-el="hero"><h1 class="headline" data-el="headline">Listen closely</h1></section>
</body></html>"""
        manifest = {
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {
                    "id": "headline",
                    "el": "headline",
                    "role": "heading",
                    "qaPriority": "fv-critical",
                    "textRecreation": True,
                    "text": {"content": "Listen closely", "fontFamily": "Arial"},
                },
            ]
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        rows = report["viewports"][0]["violations"]
        distortion = next(row for row in rows if row["check"] == "typography-transform")
        self.assertEqual(distortion["id"], "headline")
        self.assertGreater(distortion["detail"]["scaleY"], 1.2)
        self.assertEqual(distortion["detail"]["translateY"], 24)

    def test_visual_check_allows_evidenced_source_intent_transform_exception(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
section { min-height: 520px; display: grid; place-items: center; background: #f8f8f8; }
.display { display: inline-block; font: 700 72px/1 Arial, sans-serif; transform: scaleX(.94); }
</style></head><body>
<section data-el="hero"><div class="display" data-el="display">INTENTIONAL</div></section>
</body></html>"""
        manifest = {
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {
                    "id": "display",
                    "el": "display",
                    "role": "heading",
                    "qaPriority": "fv-critical",
                    "textRecreation": True,
                    "text": {"content": "INTENTIONAL", "fontFamily": "Arial"},
                    "typeSpec": {
                        "transformException": {
                            "allowed": True,
                            "scope": "source-intent-display",
                            "reason": "The authoritative comp visibly uses condensed display lettering as an intentional graphic device.",
                            "evidencePath": "reports/crops/display-transform-proof.png",
                        }
                    },
                },
            ]
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=0)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertNotIn("typography-transform", checks)

    def test_visual_check_blocks_undeclared_structural_text_overlap(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
section { min-height: 520px; padding: 100px; background: #f8f8f8; }
.title, .lead { width: 600px; margin: 0; font-family: Arial, sans-serif; }
.title { font-size: 72px; line-height: 1; }
.lead { margin-top: -58px; font-size: 30px; line-height: 1.2; }
</style></head><body>
<section data-el="hero">
  <h1 class="title" data-el="title">Listening work</h1>
  <p class="lead" data-el="lead">Learn, practice, connect.</p>
</section>
</body></html>"""
        manifest = {
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {"id": "title", "el": "title", "role": "heading", "text": {"content": "Listening work", "fontFamily": "Arial"}},
                {"id": "lead", "el": "lead", "role": "text", "text": {"content": "Learn, practice, connect.", "fontFamily": "Arial"}},
            ]
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertIn("text-overlap", checks)

    def test_visual_check_blocks_unclipped_frame_local_layer(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; overflow-x: hidden; }
.frame { position: relative; width: 900px; height: 420px; margin: 50px auto; border-radius: 48px; overflow: visible; }
.wash { position: absolute; inset: 0; background: linear-gradient(90deg, white, transparent); }
</style></head><body>
<section class="frame" data-el="cta-frame"><div class="wash" data-el="cta-wash"></div></section>
</body></html>"""
        manifest = {
            "elements": [
                {"id": "cta-frame", "el": "cta-frame", "role": "section"},
                {
                    "id": "cta-wash",
                    "el": "cta-wash",
                    "role": "decoration",
                    "positioning": "absolute",
                    "layerRole": "photo-overlay-gradient",
                    "clipOwner": "cta-frame",
                },
            ]
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertIn("clip-owner", checks)

    def test_visual_check_blocks_invisible_surface_measurement_proxy(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0}.hero{position:relative;min-height:520px;background:linear-gradient(#eee,#ddd)}
.proxy{position:absolute;inset:0;opacity:0}
</style></head><body><section class="hero">
<div class="proxy"><div data-el="hero-photo" style="width:100%;height:100%"></div></div>
</section></body></html>"""
        manifest = {
            "elements": [{
                "id": "hero.photo",
                "el": "hero-photo",
                "role": "background",
                "backgroundBehavior": "full-bleed",
                "surfaceIntegration": {
                    "mode": "opaque_full_bleed",
                    "sourceTopology": "section_field",
                },
            }]
        }

        report, _ = self.run_visual_check(html, manifest, expect_code=1)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertIn("surface-visible-owner", checks)

    def test_visual_check_rejects_stale_adopted_asset_bytes(self):
        html = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0}.section{min-height:220px}.art{width:100%;height:180px;background:#ddd}
</style></head><body>
<section class="section" data-el="section-1"><div class="art" data-el="hero-art"></div></section>
<section class="section" data-el="section-2"></section>
</body></html>"""
        asset = self.work / "assets" / "hero.png"
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(b"approved asset bytes")
        manifest = {
            "mode": "hybrid",
            "referenceImages": [
                {"path": "one.png", "use": "section-comp", "section": "section-1"},
                {"path": "two.png", "use": "section-comp", "section": "section-2"},
            ],
            "elements": [
                {"id": "section-1", "el": "section-1", "role": "section"},
                {"id": "section-2", "el": "section-2", "role": "section"},
                {
                    "id": "hero.art",
                    "el": "hero-art",
                    "role": "background",
                    "assetStrategy": "generated",
                    "generatedAsset": {"workspacePath": "assets/hero.png"},
                    "surfaceIntegration": {"mode": "opaque_full_bleed", "sourceTopology": "section_field"},
                },
            ],
        }
        manifest_path = self.work / "manifest.json"
        write_json(manifest_path, manifest)
        manifest_bytes = manifest_path.read_bytes()
        manifest_receipt = {
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "size": len(manifest_bytes),
        }
        asset_receipt = {
            "elementId": "hero.art",
            "path": "assets/hero.png",
            "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
            "size": asset.stat().st_size,
        }
        write_json(self.work / "reports" / "contract-doctor.json", {
            "status": "pass", "implementationAllowed": True,
            "inputs": {"manifest": manifest_receipt},
        })
        write_json(self.work / "reports" / "asset-preflight.json", {
            "status": "pass", "implementationAllowed": True,
            "inputs": {"manifest": manifest_receipt, "assets": [asset_receipt]},
        })
        asset.write_bytes(b"changed after preflight")

        report, _ = self.run_visual_check(html, manifest, expect_code=1)

        violation = next(
            row for row in report["viewports"][0]["violations"]
            if row["check"] == "pipeline-pre-css-contract"
        )
        self.assertFalse(violation["detail"]["assetPreflightAssetReceiptsMatch"])

    def test_visual_check_allows_parent_lockup_and_manifested_line_span(self):
        html = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: Arial, sans-serif; overflow-x: hidden; }
section { min-height: 520px; padding: 80px; }
h1 { margin: 0; font-size: 72px; line-height: 1.05; }
.line { display: block; }
</style></head><body>
<section data-el="hero"><h1 data-el="title"><span class="line" data-el="title-line-1">Listening work</span></h1></section>
</body></html>"""
        manifest = {
            "elements": [
                {"id": "hero", "el": "hero", "role": "section"},
                {"id": "title", "el": "title", "role": "heading", "text": {"content": "Listening work", "fontFamily": "Arial"}},
                {"id": "title.line1", "el": "title-line-1", "role": "text", "text": {"content": "Listening work", "fontFamily": "Arial"}},
            ]
        }
        report, _ = self.run_visual_check(html, manifest, expect_code=0)
        checks = {v["check"] for v in report["viewports"][0]["violations"]}
        self.assertNotIn("text-overlap", checks)

    def test_two_concurrent_render_invocations_succeed_with_launch_lock(self):
        paths = [self.work / "rects-1.json", self.work / "rects-2.json"]
        procs = []
        for path in paths:
            procs.append(subprocess.Popen(
                [
                    "node",
                    "scripts/render.mjs",
                    "--html",
                    "test/ground_truth.html",
                    "--viewport",
                    "390x844",
                    "--out-rects",
                    str(path),
                    "--wait",
                    "50",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ))
        outputs = [proc.communicate(timeout=90) for proc in procs]
        for proc, (stdout, stderr) in zip(procs, outputs):
            self.assertEqual(proc.returncode, 0, stdout + stderr)
        for path in paths:
            data = read_json(path)
            self.assertGreater(data["docHeight"], 0)
            self.assertIn("hero-title", {r["el"] for r in data["rects"]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
