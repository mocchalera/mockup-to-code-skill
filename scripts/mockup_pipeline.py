#!/usr/bin/env python3
"""One command for mockup-to-code initialization and policy gates.

This runner does not replace render, visual judgment, or repair loops. It
removes repeated command assembly and emits one machine-readable summary.

Usage:
  python3 mockup_pipeline.py WORK_ROOT --phase init
  python3 mockup_pipeline.py WORK_ROOT --phase next
  python3 mockup_pipeline.py WORK_ROOT --phase pre-css
  python3 mockup_pipeline.py WORK_ROOT --phase completion

Exit codes: 0 pass/complete, 1 needs_work/prototype, 2 blocked/error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import re
from datetime import datetime, timezone
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"
TEMPLATES = SKILL_DIR / "templates"


def load_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def sha256_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def report_matches_manifest(report: dict | None, manifest_path: Path) -> bool:
    receipt = ((report or {}).get("inputs") or {}).get("manifest")
    return (
        isinstance(receipt, dict)
        and receipt.get("sha256") == sha256_path(manifest_path)
        and receipt.get("size") == manifest_path.stat().st_size
    )


def adopted_asset_entries(manifest: dict) -> list[tuple[str, str]]:
    payload_names = {
        "generated": "generatedAsset",
        "replace": "replacedAsset",
        "crop-asset": "croppedAsset",
    }
    entries = []
    for element in manifest.get("elements", []):
        if not isinstance(element, dict):
            continue
        payload = element.get(payload_names.get(element.get("assetStrategy"), ""))
        path = payload.get("workspacePath") if isinstance(payload, dict) else None
        if isinstance(path, str) and path:
            entries.append((str(element.get("id") or "<missing-id>"), path))
    return entries


def resolve_input_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [root / path, Path.cwd() / path]
    candidates.extend(parent / path for parent in root.parents)
    return next((candidate for candidate in candidates if candidate.exists()), root / path)


def report_matches_asset_inputs(report: dict | None, manifest: dict, root: Path) -> bool:
    receipts = ((report or {}).get("inputs") or {}).get("assets")
    if not isinstance(receipts, list):
        return False
    expected = adopted_asset_entries(manifest)
    actual = [
        (row.get("elementId"), row.get("path"))
        for row in receipts if isinstance(row, dict)
    ]
    if actual != expected:
        return False
    for row in receipts:
        path = resolve_input_path(root, row["path"])
        if not path.is_file():
            return False
        if row.get("size") != path.stat().st_size or row.get("sha256") != sha256_path(path):
            return False
    return True


def implemented_data_els(root: Path) -> set[str]:
    found: set[str] = set()
    for path in (root / "site").rglob("*.html") if (root / "site").is_dir() else ():
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found.update(re.findall(r"data-el\s*=\s*['\"]([^'\"]+)['\"]", source))
    return found


def next_action(root: Path) -> tuple[str, list[dict], int]:
    manifest = load_json(root / "manifest.json")
    if manifest is None:
        return "needs_work", [{
            "name": "next",
            "status": "needs_work",
            "allowedAction": "init",
            "command": [sys.executable, str(SCRIPTS / "mockup_pipeline.py"), str(root), "--phase", "init"],
            "message": "initialize an isolated run before creating implementation files",
        }], 1

    doctor = load_json(root / "reports" / "contract-doctor.json")
    asset = load_json(root / "reports" / "asset-preflight.json")
    manifest_path = root / "manifest.json"
    asset_inputs_match = report_matches_asset_inputs(asset, manifest, root)
    if (
        doctor is None
        or doctor.get("status") != "pass"
        or not report_matches_manifest(doctor, manifest_path)
        or asset is None
        or asset.get("implementationAllowed") is not True
        or not report_matches_manifest(asset, manifest_path)
        or not asset_inputs_match
    ):
        return "needs_work", [{
            "name": "next",
            "status": "needs_work",
            "allowedAction": "run-pre-css",
            "command": [sys.executable, str(SCRIPTS / "mockup_pipeline.py"), str(root), "--phase", "pre-css"],
            "completionCeiling": "blocked",
            "message": "finish the manifest, prompt receipts, specialist inputs, and asset decisions before CSS",
            "staleEvidence": {
                "contractDoctor": doctor is not None and not report_matches_manifest(doctor, manifest_path),
                "assetPreflight": asset is not None and not report_matches_manifest(asset, manifest_path),
                "assetFiles": asset is not None and not asset_inputs_match,
            },
        }], 1

    fv_elements = [
        row for row in manifest.get("elements", [])
        if isinstance(row, dict) and row.get("qaPriority") == "fv-critical"
    ]
    below_elements = [
        row for row in manifest.get("elements", [])
        if isinstance(row, dict) and row.get("qaPriority") == "section-critical"
    ]
    implemented = implemented_data_els(root)
    premature = sorted(
        row.get("id") for row in below_elements
        if row.get("el") in implemented and isinstance(row.get("id"), str)
    )
    box = load_json(root / "reports" / "box-report.json")
    box_by_id = {
        row.get("id"): row for row in (box or {}).get("items", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    fv_missing = [row.get("id") for row in fv_elements if row.get("id") not in box_by_id]
    fv_failing = [
        row.get("id") for row in fv_elements
        if row.get("id") in box_by_id and box_by_id[row.get("id")].get("pass") is not True
    ]
    if fv_missing or fv_failing:
        step = {
            "name": "next",
            "status": "needs_work",
            "allowedAction": "render-and-diff-fv" if box is None else "repair-first-failing-fv-element",
            "allowedImplementationIds": [row.get("id") for row in fv_elements],
            "blockedImplementationIds": [row.get("id") for row in below_elements],
            "fvMissingFromBoxReport": fv_missing,
            "fvFailing": fv_failing,
            "completionCeiling": "prototype" if premature else "blocked",
            "message": "FV must converge before below-FV implementation",
        }
        if premature:
            step["prematureBelowFvDomIds"] = premature
            step["scopeViolation"] = "below-FV DOM exists while FV box evidence is incomplete"
        if isinstance((box or {}).get("first_fix"), dict):
            step["firstFix"] = box["first_fix"]
        return "needs_work", [step], 1

    tune_images = sorted((root / "reports" / "fv-tune").glob("*.png"))
    if len(tune_images) < 2:
        return "needs_work", [{
            "name": "next",
            "status": "needs_work",
            "allowedAction": "capture-fv-tune-desktop-and-mobile",
            "existingEvidence": [str(path) for path in tune_images],
            "completionCeiling": "blocked",
            "message": "FV box convergence needs readable desktop and mobile visual evidence before below-FV implementation",
        }], 1
    impression = load_json(root / "reports" / "impression-metrics.json")
    if impression is None or any(metric.get("pass") is not True for metric in impression.get("metrics", []) if isinstance(metric, dict)):
        return "needs_work", [{
            "name": "next",
            "status": "needs_work",
            "allowedAction": "measure-and-pass-fv-impression",
            "missingArtifact": str(root / "reports" / "impression-metrics.json"),
            "completionCeiling": "blocked",
            "message": "measure lockup scale, mixed-script ratio, photo tone, and repeated-device scale before opening below-FV scope",
        }], 1

    missing_below = [
        row.get("id") for row in below_elements
        if row.get("el") not in implemented and isinstance(row.get("id"), str)
    ]
    if missing_below:
        return "pass", [{
            "name": "next",
            "status": "pass",
            "allowedAction": "implement-next-below-fv-section",
            "nextMissingId": missing_below[0],
            "completionCeiling": "prototype",
            "message": "FV is converged; implement the next missing section-critical target only",
        }], 0

    required = [
        ("capture-fv-pixel", root / "reports" / "fv-pixel-report.json"),
        ("measure-impression", root / "reports" / "impression-metrics.json"),
        ("complete-independent-review", root / "reports" / "section-scores.json"),
        ("run-artifact-check", root / "reports" / "artifact-check.json"),
        ("run-completion", root / "reports" / "completion-verdict.json"),
    ]
    if (manifest.get("motion") or {}).get("required") is True:
        required.insert(2, ("run-motion-check", root / "reports" / "motion-check.json"))
    production = manifest.get("productionReadiness") or {}
    specialist_entries = manifest.get("specialistReports") or {}
    production_steps = []
    if production.get("mediaDeliveryRequired") is True:
        entry = specialist_entries.get("mediaDelivery") or {}
        production_steps.append((
            "run-responsive-image-delivery",
            root / (entry.get("path") or "reports/media-delivery-report.json"),
        ))
    if production.get("interactionQaRequired") is True:
        entry = specialist_entries.get("interaction") or {}
        production_steps.append((
            "run-lp-interaction-qa",
            root / (entry.get("path") or "reports/interaction-report.json"),
        ))
    required[2:2] = production_steps
    for action, path in required:
        payload = load_json(path)
        if payload is None:
            return "needs_work", [{
                "name": "next",
                "status": "needs_work",
                "allowedAction": action,
                "missingArtifact": str(path),
                "completionCeiling": "prototype",
            }], 1
        if action == "complete-independent-review":
            independent = (payload.get("reviewProvenance") or {}).get("independent") or {}
            if not independent.get("reviewedAt") or str(independent.get("reviewerId", "")).startswith("TODO"):
                return "needs_work", [{
                    "name": "next",
                    "status": "needs_work",
                    "allowedAction": action,
                    "missingArtifact": str(path),
                    "completionCeiling": "prototype",
                    "message": "a different reviewer must judge crop pairs before completion",
                }], 1
        specialist_key = {
            "run-responsive-image-delivery": "mediaDelivery",
            "run-lp-interaction-qa": "interaction",
        }.get(action)
        if specialist_key:
            entry = specialist_entries.get(specialist_key) or {}
            if entry.get("sha256") != sha256_path(path):
                return "needs_work", [{
                    "name": "next",
                    "status": "needs_work",
                    "allowedAction": "repair-" + action.removeprefix("run-"),
                    "artifact": str(path),
                    "completionCeiling": "prototype",
                    "message": "specialist report receipt is missing or stale",
                }], 1
        if action in (
            "run-motion-check",
            "run-responsive-image-delivery",
            "run-lp-interaction-qa",
            "run-artifact-check",
            "run-completion",
        ) and payload.get("status") not in ("pass", "complete"):
            return "needs_work", [{
                "name": "next",
                "status": "needs_work",
                "allowedAction": "repair-" + action.removeprefix("run-"),
                "artifact": str(path),
                "artifactStatus": payload.get("status"),
                "completionCeiling": "prototype",
            }], 1

    verdict = load_json(root / "reports" / "completion-verdict.json") or {}
    status = verdict.get("status") if verdict.get("status") in ("complete", "prototype", "blocked") else "needs_work"
    return status, [{
        "name": "next",
        "status": status,
        "allowedAction": "done" if status == "complete" else "repair-completion-gaps",
        "verdict": verdict,
    }], 0 if status == "complete" else (2 if status == "blocked" else 1)


def emit(root: Path, phase: str, status: str, steps: list[dict], exit_code: int) -> None:
    report = {
        "status": status,
        "phase": phase,
        "workRoot": str(root),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "steps": steps,
        "contract": "This summary orchestrates existing gates; each step artifact remains authoritative.",
    }
    out_path = root / "reports" / "pipeline-summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    history_path = root / "reports" / "pipeline-history.jsonl"
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(exit_code)


def run_step(name: str, command: list[str]) -> dict:
    completed = subprocess.run(command, text=True, capture_output=True)
    payload = None
    stdout = completed.stdout.strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = None
    return {
        "name": name,
        "command": command,
        "exitCode": completed.returncode,
        "status": payload.get("status") if isinstance(payload, dict) else ("pass" if completed.returncode == 0 else "error"),
        "artifact": payload,
        "stderr": completed.stderr.strip() or None,
    }


def init_work_root(root: Path) -> tuple[str, list[dict], int]:
    for directory in (
        "mockups",
        "assets",
        "site/css",
        "reports/crops",
        "reports/sections",
        "reports/measurements",
        "reports/prompts",
        "reports/fv-tune",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)
    mappings = {
        TEMPLATES / "manifest.hybrid-multiframe.min.json": root / "manifest.json",
        TEMPLATES / "section-scores.min.json": root / "reports" / "section-scores.json",
        TEMPLATES / "hypotheses.md": root / "reports" / "hypotheses.md",
        TEMPLATES / "section-review.md": root / "reports" / "section-review.md",
        TEMPLATES / "photo-asset-review.md": root / "reports" / "photo-asset-review.md",
    }
    existing = [str(dst) for dst in mappings.values() if dst.exists()]
    if existing:
        step = {
            "name": "init",
            "status": "blocked",
            "message": "refusing to overwrite an existing run",
            "existing": existing,
        }
        return "blocked", [step], 2
    copied = []
    for source, destination in mappings.items():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(str(destination))
    return "pass", [{"name": "init", "status": "pass", "copied": copied}], 0


def pre_css(root: Path) -> tuple[str, list[dict], int]:
    doctor = run_step(
        "contract-doctor-pre-css",
        [
            sys.executable,
            str(SCRIPTS / "contract_doctor.py"),
            str(root),
            "--phase",
            "pre-css",
            "--out",
            str(root / "reports" / "contract-doctor.json"),
        ],
    )
    asset = run_step(
        "asset-preflight",
        [
            sys.executable,
            str(SCRIPTS / "asset_preflight.py"),
            str(root / "manifest.json"),
            "--work-root",
            str(root),
            "--out",
            str(root / "reports" / "asset-preflight.json"),
        ],
    )
    steps = [doctor, asset]
    if any(step["exitCode"] == 2 for step in steps):
        return "blocked", steps, 2
    if any(step["exitCode"] != 0 for step in steps):
        return "needs_work", steps, 1
    return "pass", steps, 0


def completion(root: Path, no_pixel: str | None, no_impression: str | None) -> tuple[str, list[dict], int]:
    steps = []
    doctor = run_step(
        "contract-doctor-completion",
        [
            sys.executable,
            str(SCRIPTS / "contract_doctor.py"),
            str(root),
            "--phase",
            "completion",
            "--out",
            str(root / "reports" / "contract-doctor-completion.json"),
        ],
    )
    steps.append(doctor)
    if doctor["exitCode"] != 0:
        return ("blocked" if doctor["exitCode"] == 2 else "needs_work"), steps, doctor["exitCode"]

    page_flow = run_step(
        "page-flow",
        [
            sys.executable,
            str(SCRIPTS / "page_flow_check.py"),
            str(root / "manifest.json"),
            str(root / "reports" / "rects.json"),
            "--work-root",
            str(root),
            "--out",
            str(root / "reports" / "page-flow.json"),
        ],
    )
    steps.append(page_flow)

    artifact = run_step(
        "artifact-check",
        [
            sys.executable,
            str(SCRIPTS / "artifact_check.py"),
            str(root),
            "--page-flow",
            str(root / "reports" / "page-flow.json"),
            "--out",
            str(root / "reports" / "artifact-check.json"),
        ],
    )
    steps.append(artifact)

    gate_command = [
        sys.executable,
        str(SCRIPTS / "completion_gate.py"),
        str(root / "manifest.json"),
        str(root / "reports" / "box-report.json"),
        "--visual-check",
        str(root / "reports" / "visual-check.json"),
        "--widths-check",
        str(root / "reports" / "responsive-check.json"),
        "--scores",
        str(root / "reports" / "section-scores.json"),
        "--artifact-check",
        str(root / "reports" / "artifact-check.json"),
        "--fv-pixel",
        str(root / "reports" / "fv-pixel-report.json"),
        "--impression",
        str(root / "reports" / "impression-metrics.json"),
        "--page-flow",
        str(root / "reports" / "page-flow.json"),
        "--motion-check",
        str(root / "reports" / "motion-check.json"),
        "--out",
        str(root / "reports" / "completion-verdict.json"),
    ]
    if no_pixel:
        gate_command += ["--no-pixel-evidence", no_pixel]
    if no_impression:
        gate_command += ["--no-impression-evidence", no_impression]
    gate = run_step("completion-gate", gate_command)
    steps.append(gate)
    gate_status = gate.get("status")
    if gate_status == "complete":
        return "complete", steps, 0
    if gate_status == "blocked" or gate["exitCode"] == 2:
        return "blocked", steps, 2
    return "prototype", steps, 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_root")
    parser.add_argument("--phase", choices=("init", "next", "pre-css", "completion"), required=True)
    parser.add_argument("--no-pixel-evidence")
    parser.add_argument("--no-impression-evidence")
    args = parser.parse_args()
    root = Path(args.work_root)
    if args.phase == "init":
        status, steps, code = init_work_root(root)
    elif args.phase == "next":
        status, steps, code = next_action(root)
    elif args.phase == "pre-css":
        status, steps, code = pre_css(root)
    else:
        status, steps, code = completion(root, args.no_pixel_evidence, args.no_impression_evidence)
    emit(root, args.phase, status, steps, code)


if __name__ == "__main__":
    main()
