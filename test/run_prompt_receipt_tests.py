#!/usr/bin/env python3
"""Regression tests for pre-generation prompt receipts."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PromptReceiptTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="prompt-receipt-"))
        self.prompt = self.work / "prompt.txt"
        self.asset = self.work / "asset.png"
        self.receipt = self.work / "receipt.json"
        self.prompt.write_text("exact prompt bytes", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.work)

    def run_cli(self, *args, expected=0):
        proc = subprocess.run(
            [sys.executable, "scripts/prompt_receipt.py", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return proc

    def issue(self):
        self.run_cli(
            "issue", "--prompt", str(self.prompt), "--asset", str(self.asset),
            "--generator", "test-generator", "--out", str(self.receipt),
        )

    def test_issue_then_adopt_binds_prompt_and_output(self):
        self.issue()
        self.asset.write_bytes(b"png-output")
        self.run_cli("adopt", "--receipt", str(self.receipt))
        payload = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "adopted")
        self.assertEqual(len(payload["prompt"]["sha256"]), 64)
        self.assertEqual(len(payload["asset"]["sha256"]), 64)

    def test_issue_refuses_existing_asset(self):
        self.asset.write_bytes(b"already-generated")
        proc = self.run_cli(
            "issue", "--prompt", str(self.prompt), "--asset", str(self.asset),
            "--generator", "test-generator", "--out", str(self.receipt), expected=2,
        )
        self.assertIn("before generation", proc.stdout)

    def test_adopt_refuses_changed_prompt(self):
        self.issue()
        self.prompt.write_text("retrospective summary", encoding="utf-8")
        self.asset.write_bytes(b"png-output")
        proc = self.run_cli("adopt", "--receipt", str(self.receipt), expected=2)
        self.assertIn("prompt changed", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
