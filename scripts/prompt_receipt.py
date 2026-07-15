#!/usr/bin/env python3
"""Issue a pre-generation prompt receipt and bind the adopted output.

Usage:
  python3 prompt_receipt.py issue --prompt prompt.txt --asset assets/hero.png \
      --generator "cockpit gen-image" --out reports/prompts/hero.receipt.json
  python3 prompt_receipt.py adopt --receipt reports/prompts/hero.receipt.json

The issue command refuses to run after the output exists. The adopt command
refuses changed prompts, empty outputs, and output files older than the receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fail(message: str) -> None:
    print(json.dumps({"status": "blocked", "message": message}, ensure_ascii=False))
    raise SystemExit(2)


def issue(args: argparse.Namespace) -> None:
    prompt = Path(args.prompt).resolve()
    asset = Path(args.asset).resolve()
    out = Path(args.out).resolve()
    if not prompt.is_file() or prompt.stat().st_size == 0:
        fail(f"prompt is missing or empty: {prompt}")
    try:
        prompt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        fail(f"prompt must be readable UTF-8 text: {prompt}")
    if asset.exists():
        fail(f"asset already exists; issue the receipt before generation: {asset}")
    if out.exists():
        fail(f"receipt already exists: {out}")
    payload = {
        "schemaVersion": "prompt-generation-receipt/v1",
        "status": "issued",
        "generator": args.generator,
        "issuedAt": now(),
        "prompt": {"path": str(prompt), "sha256": sha256(prompt), "size": prompt.stat().st_size},
        "asset": {"path": str(asset)},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def adopt(args: argparse.Namespace) -> None:
    receipt = Path(args.receipt).resolve()
    try:
        payload = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read receipt {receipt}: {exc}")
    if payload.get("schemaVersion") != "prompt-generation-receipt/v1" or payload.get("status") != "issued":
        fail("receipt must be an issued prompt-generation-receipt/v1")
    prompt = Path((payload.get("prompt") or {}).get("path", ""))
    asset = Path((payload.get("asset") or {}).get("path", ""))
    if not prompt.is_file() or sha256(prompt) != (payload.get("prompt") or {}).get("sha256"):
        fail("prompt changed after receipt issuance")
    if not asset.is_file() or asset.stat().st_size == 0:
        fail(f"generated asset is missing or empty: {asset}")
    if asset.stat().st_mtime_ns < receipt.stat().st_mtime_ns:
        fail("generated asset predates the prompt receipt")
    payload["status"] = "adopted"
    payload["adoptedAt"] = now()
    payload["asset"].update({"sha256": sha256(asset), "size": asset.stat().st_size})
    receipt.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    issue_parser = sub.add_parser("issue")
    issue_parser.add_argument("--prompt", required=True)
    issue_parser.add_argument("--asset", required=True)
    issue_parser.add_argument("--generator", required=True)
    issue_parser.add_argument("--out", required=True)
    adopt_parser = sub.add_parser("adopt")
    adopt_parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    issue(args) if args.command == "issue" else adopt(args)


if __name__ == "__main__":
    main()
