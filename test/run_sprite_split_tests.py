#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]


class SpriteSplitTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="sprite-split-"))

    def tearDown(self):
        shutil.rmtree(self.temp)

    def test_measures_unequal_clusters_instead_of_equal_cells(self):
        image = Image.new("RGBA", (500, 140), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((15, 25, 135, 110), fill=(20, 120, 100, 255))
        draw.rectangle((190, 35, 260, 105), fill=(20, 120, 100, 255))
        draw.rectangle((330, 15, 480, 120), fill=(20, 120, 100, 255))
        source = self.temp / "sprite.png"
        report = self.temp / "report.json"
        image.save(source)

        proc = subprocess.run([
            sys.executable, "scripts/split_sprite.py", str(source),
            "--count", "3", "--names", "a,b,c", "--out-dir", str(self.temp / "out"),
            "--report", str(report), "--size", "128",
        ], cwd=ROOT, text=True, capture_output=True)

        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(report.read_text())
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["clusters"], [[15, 135], [190, 260], [330, 480]])
        for output in result["outputs"]:
            self.assertEqual(output["edgeAlphaPixels"], {"top": 0, "right": 0, "bottom": 0, "left": 0})


if __name__ == "__main__":
    unittest.main(verbosity=2)
