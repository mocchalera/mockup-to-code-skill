#!/usr/bin/env python3
"""Regression tests for conditional motion runtime QA."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MotionCheckTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="motion-check-"))
        self.html = self.work / "index.html"
        self.manifest = self.work / "manifest.json"
        self.out = self.work / "motion.json"
        self.html.write_text(
            '<!doctype html><style>h1{opacity:1}</style><h1 data-el="hero-heading">Title</h1><a data-el="hero-cta" href="#">CTA</a>',
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.work)

    def run_check(self, manifest, expected):
        self.manifest.write_text(json.dumps(manifest), encoding="utf-8")
        proc = subprocess.run(
            [
                "node", "scripts/motion-check.mjs", "--html", str(self.html),
                "--manifest", str(self.manifest), "--viewports", "390x844", "--out", str(self.out),
            ],
            cwd=ROOT, text=True, capture_output=True, timeout=90,
        )
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return json.loads(self.out.read_text(encoding="utf-8"))

    def test_static_project_skips_without_browser_gate(self):
        report = self.run_check({"motion": {"required": False}, "elements": []}, 0)
        self.assertEqual(report["status"], "not_required")

    def test_required_motion_without_runtime_animation_or_real_cta_needs_work(self):
        manifest = {
            "motion": {
                "required": True,
                "visualQaState": "settled",
                "motifs": [{"targets": ["hero.heading"], "durationMs": 500}],
            },
            "elements": [
                {"id": "hero.heading", "el": "hero-heading", "qaPriority": "fv-critical"},
                {"id": "hero.cta", "el": "hero-cta", "qaPriority": "fv-critical", "role": "button"},
            ],
        }
        report = self.run_check(manifest, 1)
        self.assertEqual(report["status"], "needs_work")
        normal = next(row for row in report["checks"] if row["id"] == "normal-390")
        self.assertTrue(normal["badLinks"])

    def test_required_motion_passes_with_runtime_event_and_settled_reduced_state(self):
        self.html.write_text(
            '''<!doctype html><style>
@keyframes reveal{from{opacity:.7;transform:translateY(4px)}to{opacity:1;transform:none}}
[data-el="hero-heading"]{animation:reveal 500ms cubic-bezier(.22,1,.36,1) both}
@media(prefers-reduced-motion:reduce){[data-el="hero-heading"]{animation:none;opacity:1;transform:none}}
</style><h1 data-el="hero-heading">Title</h1><a data-el="hero-cta" href="/apply">CTA</a>''',
            encoding="utf-8",
        )
        manifest = {
            "motion": {
                "required": True,
                "visualQaState": "settled",
                "motifs": [{"targets": ["hero.heading"], "durationMs": 500}],
            },
            "elements": [
                {"id": "hero.heading", "el": "hero-heading", "qaPriority": "fv-critical"},
                {"id": "hero.cta", "el": "hero-cta", "qaPriority": "fv-critical", "role": "button"},
            ],
        }

        report = self.run_check(manifest, 0)

        self.assertEqual(report["status"], "pass")


if __name__ == "__main__":
    unittest.main(verbosity=2)
