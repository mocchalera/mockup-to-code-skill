#!/usr/bin/env python3
"""page_flow_check.py — verify multi-frame comps became one scrolling page.

Static section comps are often generated at one repeated aspect ratio.  That
ratio is a density floor, not a web section-height instruction.  This check
binds the Phase 4.5 page-composition plan to rendered section heights and seam
evidence so a stack of equal-height slides cannot pass on self-score alone.

Usage:
  python3 page_flow_check.py MANIFEST RECTS \
      [--work-root WORK_ROOT] [--out reports/page-flow.json]

Exit codes: 0 pass, 1 needs_work, 2 blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path


HEIGHT_EPSILON = 0.03
SEAM_BREATHING_MIN_PX = 64


def load_json(path: Path, label: str, checks: list[dict]) -> dict | None:
    if not path.is_file():
        checks.append(row("blocked", f"missing-{label}", f"missing {label}: {path}"))
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(row("blocked", f"unreadable-{label}", f"unreadable {label}: {path}: {exc}"))
        return None


def row(status: str, cid: str, message: str, **extra) -> dict:
    result = {"id": cid, "status": status, "message": message}
    result.update(extra)
    return result


def resolve_evidence(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    for candidate in (root / path, root.parent / path, Path.cwd() / path):
        if candidate.exists():
            return candidate
    return root / path


def readable(root: Path, value: str | None) -> bool:
    path = resolve_evidence(root, value)
    if not path or not path.is_file() or path.stat().st_size < 12:
        return False
    try:
        header = path.read_bytes()[:12]
    except OSError:
        return False
    return (
        header.startswith(b"\x89PNG\r\n\x1a\n")
        or header.startswith(b"\xff\xd8\xff")
        or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rendered_height(item: dict) -> float:
    try:
        return float(item.get("h", item.get("height", 0)))
    except (TypeError, ValueError):
        return 0.0


def has_human_intent(value: object) -> bool:
    return bool(
        isinstance(value, dict)
        and str(value.get("reason", "")).strip()
        and str(value.get("userQuote", "")).strip()
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest")
    ap.add_argument("rects")
    ap.add_argument("--work-root")
    ap.add_argument("--out")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    rects_path = Path(args.rects)
    root = Path(args.work_root) if args.work_root else manifest_path.resolve().parent
    out_path = Path(args.out) if args.out else None
    checks: list[dict] = []

    manifest = load_json(manifest_path, "manifest", checks)
    rect_data = load_json(rects_path, "rects", checks)
    if manifest is None or rect_data is None:
        emit(out_path, "blocked", checks, {}, root)
        return

    refs = [
        ref for ref in manifest.get("referenceImages", []) or []
        if ref.get("use") == "section-comp" and ref.get("section")
    ]
    sections = [ref["section"] for ref in refs]
    if len(sections) < 2:
        checks.append(row("pass", "page-flow-not-applicable", "single-frame/non-sectioned run"))
        emit(out_path, "pass", checks, {"sectionCount": len(sections)}, root)
        return

    contract = manifest.get("pageComposition")
    if not isinstance(contract, dict):
        checks.append(row(
            "needs_work",
            "page-composition-missing",
            "multi-frame hybrid requires manifest.pageComposition with section and seam contracts",
        ))
        contract = {}

    reference_height = contract.get("referenceFrameHeight")
    if not isinstance(reference_height, (int, float)) or reference_height <= 0:
        checks.append(row(
            "needs_work",
            "reference-frame-height-missing",
            "pageComposition.referenceFrameHeight is required for multi-frame page-flow checks",
        ))
        reference_height = None
    viewport_height = manifest.get("viewport", {}).get("height")
    comparison_reference_height = reference_height
    reference_height_source = "pageComposition"
    if comparison_reference_height is None and isinstance(viewport_height, (int, float)) and viewport_height > 0:
        # Old manifests often retain the normalized frame height in viewport.
        # Use it for diagnostic ratios only; the missing executable contract
        # remains a needs_work finding above.
        comparison_reference_height = viewport_height
        reference_height_source = "viewport-diagnostic-fallback"

    section_contracts = {
        item.get("section"): item
        for item in contract.get("sections", []) or []
        if isinstance(item, dict) and item.get("section")
    }
    missing_contracts = [section for section in sections if section not in section_contracts]
    if missing_contracts:
        checks.append(row(
            "needs_work",
            "section-composition-coverage",
            "pageComposition.sections does not cover every section-comp",
            missing=missing_contracts,
        ))
    else:
        checks.append(row("pass", "section-composition-coverage", f"{len(sections)} section strategies declared"))

    for section in sections:
        spec = section_contracts.get(section, {})
        missing = [key for key in ("heightStrategy", "density", "overflowPolicy") if not spec.get(key)]
        if missing:
            checks.append(row(
                "needs_work",
                "section-strategy-incomplete",
                f"section '{section}' lacks page-composition fields: {', '.join(missing)}",
            ))
        if spec.get("overflowPolicy") == "clip" and not str(spec.get("clipReason", "")).strip():
            checks.append(row(
                "needs_work",
                "section-clip-reason-missing",
                f"section '{section}' clips overflow without clipReason",
            ))

    rects = rect_data.get("rects") or rect_data.get("elements") or []
    by_el = {item.get("el"): item for item in rects if isinstance(item, dict) and item.get("el")}
    missing_rects = [section for section in sections if section not in by_el]
    if missing_rects:
        checks.append(row(
            "blocked",
            "section-rects-missing",
            "rendered rects lack section-comp roots",
            missing=missing_rects,
        ))

    heights = [rendered_height(by_el[section]) for section in sections if section in by_el]
    height_rows = []
    stacked = False
    reference_locked = False
    spread = None
    if len(heights) == len(sections) and heights and all(height > 0 for height in heights):
        median = statistics.median(heights)
        spread = (max(heights) - min(heights)) / median if median else 0
        ratios = [height / comparison_reference_height for height in heights] if comparison_reference_height else []
        reference_locked = bool(ratios) and all(abs(ratio - 1.0) <= HEIGHT_EPSILON for ratio in ratios)
        # Repeating any fixed section height across a multi-frame page is the
        # slideshow signature. Matching the normalized source frame makes the
        # cause especially clear, but changing one shared CSS height from 900
        # to 1080 does not make it content-led.
        stacked = spread <= HEIGHT_EPSILON
        height_rows = [
            {
                "section": section,
                "height": round(height, 2),
                "ratioToReference": round(height / comparison_reference_height, 4) if comparison_reference_height else None,
                "heightStrategy": section_contracts.get(section, {}).get("heightStrategy"),
                "density": section_contracts.get(section, {}).get("density"),
                "overflowPolicy": section_contracts.get(section, {}).get("overflowPolicy"),
                "plannedMinHeightRatio": section_contracts.get(section, {}).get("minHeightRatio", 1.0),
            }
            for section, height in zip(sections, heights)
        ]

        for item in height_rows:
            planned_min = item["plannedMinHeightRatio"]
            actual_ratio = item["ratioToReference"]
            if (
                isinstance(planned_min, (int, float))
                and actual_ratio is not None
                and actual_ratio + HEIGHT_EPSILON < planned_min
            ):
                checks.append(row(
                    "needs_work",
                    "section-height-below-plan",
                    f"section '{item['section']}' is shorter than its declared minHeightRatio",
                    actualRatio=actual_ratio,
                    plannedMinHeightRatio=planned_min,
                ))
        if stacked and not has_human_intent(contract.get("uniformHeightIntent")):
            checks.append(row(
                "needs_work",
                "stacked-frames",
                "all rendered sections remain locked to one repeated height; this reads as stacked slides",
                heightSpreadPct=round(spread * 100, 2),
                tolerancePct=HEIGHT_EPSILON * 100,
                referenceFrameLocked=reference_locked,
                sections=height_rows,
            ))
        elif stacked:
            checks.append(row(
                "pass",
                "uniform-height-human-intent",
                "uniform chapter heights are backed by a verbatim human-approved intent",
            ))
        else:
            checks.append(row(
                "pass",
                "section-height-rhythm",
                "rendered section heights are not a repeated-frame lock",
                heightSpreadPct=round((spread or 0) * 100, 2),
            ))
    elif len(heights) == len(sections):
        checks.append(row(
            "blocked",
            "section-height-invalid",
            "rendered section roots must have positive numeric heights",
            heights=heights,
        ))

    all_clipped = bool(sections) and all(
        section_contracts.get(section, {}).get("overflowPolicy") == "clip"
        for section in sections
    )
    if all_clipped and not has_human_intent(contract.get("allSectionsClipIntent")):
        checks.append(row(
            "needs_work",
            "all-sections-clipped",
            "every section clips overflow; declare cross-section handoffs or record the human-approved chapter-frame intent",
        ))

    expected_seams = list(zip(sections, sections[1:]))
    seam_contracts = {
        (item.get("from"), item.get("to")): item
        for item in contract.get("seams", []) or []
        if isinstance(item, dict)
    }
    missing_seams = [f"{a}->{b}" for a, b in expected_seams if (a, b) not in seam_contracts]
    if missing_seams:
        checks.append(row(
            "needs_work",
            "seam-contract-coverage",
            "pageComposition.seams does not cover every adjacent section boundary",
            missing=missing_seams,
        ))

    missing_evidence = []
    non_hard_seams = 0
    manifest_ids = {
        str(value)
        for element in manifest.get("elements", []) or []
        for value in (element.get("id"), element.get("el"))
        if value
    }
    unknown_bridges = []
    art_directed_failures = []
    seam_rows = []
    for a, b in expected_seams:
        seam = seam_contracts.get((a, b), {})
        seam_type = seam.get("type")
        transition_px = seam.get("transitionSpacePx", 0) or 0
        bridges = seam.get("bridgeElements", []) or []
        if seam_type and (
            seam_type != "hard-cut"
            or transition_px >= SEAM_BREATHING_MIN_PX
            or bridges
        ):
            non_hard_seams += 1
        evidence = seam.get("evidencePath")
        if seam and not readable(root, evidence):
            missing_evidence.append(f"{a}->{b}:{evidence or 'missing'}")
        for bridge in bridges:
            if bridge not in manifest_ids:
                unknown_bridges.append(f"{a}->{b}:{bridge}")
        continuity = seam.get("continuity") or {}
        continuity_required = isinstance(continuity, dict) and continuity.get("required") is True
        if continuity_required:
            pair = f"{a}->{b}"
            desktop_evidence_path = resolve_evidence(root, continuity.get("desktopEvidencePath"))
            for field in ("desktopEvidencePath", "mobileEvidencePath"):
                value = continuity.get(field)
                if not readable(root, value):
                    art_directed_failures.append(f"{pair}:{field}:{value or 'missing'}")

            report_value = continuity.get("colorSampleReport")
            report_path = resolve_evidence(root, report_value)
            pixel_report = None
            if report_path is None or not report_path.is_file():
                art_directed_failures.append(f"{pair}:colorSampleReport:{report_value or 'missing'}")
            else:
                try:
                    pixel_report = json.loads(report_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    art_directed_failures.append(f"{pair}:colorSampleReport:unreadable")
            if isinstance(pixel_report, dict):
                if pixel_report.get("schemaVersion") != "seam-pixel-check/v1":
                    art_directed_failures.append(f"{pair}:colorSampleReport:schema")
                if pixel_report.get("status") != "pass":
                    art_directed_failures.append(f"{pair}:colorSampleReport:status")
                if (pixel_report.get("from"), pixel_report.get("to")) != (a, b):
                    art_directed_failures.append(f"{pair}:colorSampleReport:pair")
                sample_roles = {
                    item.get("role")
                    for item in pixel_report.get("samples", [])
                    if isinstance(item, dict) and item.get("status") == "pass"
                }
                if not {"bridge-fill", "next-surface"}.issubset(sample_roles):
                    art_directed_failures.append(f"{pair}:colorSampleReport:sample-roles")
                image_path = resolve_evidence(root, pixel_report.get("imagePath"))
                if image_path is None or not image_path.is_file():
                    art_directed_failures.append(f"{pair}:colorSampleReport:image-missing")
                elif pixel_report.get("imageSha256") != sha256_file(image_path):
                    art_directed_failures.append(f"{pair}:colorSampleReport:image-hash")
                elif desktop_evidence_path is None or image_path.resolve() != desktop_evidence_path.resolve():
                    art_directed_failures.append(f"{pair}:colorSampleReport:image-not-desktop-evidence")
        seam_rows.append({
            "from": a,
            "to": b,
            "type": seam_type,
            "transitionSpacePx": transition_px,
            "bridgeElements": bridges,
            "evidencePath": evidence,
            "artDirectedContinuity": continuity_required,
            "desktopEvidencePath": continuity.get("desktopEvidencePath") if continuity_required else None,
            "mobileEvidencePath": continuity.get("mobileEvidencePath") if continuity_required else None,
            "colorSampleReport": continuity.get("colorSampleReport") if continuity_required else None,
        })

        if seam and not seam_type:
            checks.append(row(
                "needs_work",
                "seam-strategy-incomplete",
                f"seam '{a}->{b}' lacks a transition type",
            ))

    if not missing_seams and missing_evidence:
        checks.append(row(
            "needs_work",
            "seam-evidence-missing",
            "each seam needs a readable PNG/JPEG/WebP rendered crop/pair, not only a prose plan",
            missing=missing_evidence,
        ))
    elif not missing_seams:
        checks.append(row("pass", "seam-evidence-coverage", f"{len(expected_seams)} seam evidence file(s) readable"))

    if unknown_bridges:
        checks.append(row(
            "needs_work",
            "seam-bridge-elements-missing",
            "seam bridgeElements must reference manifested element id/el values",
            missing=unknown_bridges,
        ))

    if art_directed_failures:
        checks.append(row(
            "needs_work",
            "art-directed-seam-evidence",
            "explicit seamless-scroll seams need desktop/mobile crops and a passing image-bound destination-color report",
            failures=art_directed_failures,
        ))
    elif any(item.get("artDirectedContinuity") for item in seam_rows):
        count = sum(1 for item in seam_rows if item.get("artDirectedContinuity"))
        checks.append(row(
            "pass",
            "art-directed-seam-evidence",
            f"{count} art-directed seam(s) have desktop/mobile and destination-color proof",
        ))

    if expected_seams and non_hard_seams == 0 and not has_human_intent(contract.get("allHardCutIntent")):
        checks.append(row(
            "needs_work",
            "flat-seams",
            "all seams are hard cuts with no breathing space or bridge element",
        ))

    strategies = sorted({
        section_contracts.get(section, {}).get("heightStrategy")
        for section in sections
        if section_contracts.get(section, {}).get("heightStrategy")
    })
    densities = sorted({
        section_contracts.get(section, {}).get("density")
        for section in sections
        if section_contracts.get(section, {}).get("density")
    })
    metrics = {
        "sectionCount": len(sections),
        "referenceFrameHeight": comparison_reference_height,
        "referenceFrameHeightSource": reference_height_source if comparison_reference_height else None,
        "sectionHeights": height_rows,
        "heightSpreadPct": round(spread * 100, 2) if spread is not None else None,
        "stackedFrameLock": stacked,
        "referenceFrameLock": reference_locked,
        "heightStrategies": strategies,
        "densities": densities,
        "seams": seam_rows,
        "nonHardSeamCount": non_hard_seams,
        "allSectionsClipped": all_clipped,
    }
    status = "blocked" if any(item["status"] == "blocked" for item in checks) else (
        "needs_work" if any(item["status"] == "needs_work" for item in checks) else "pass"
    )
    emit(out_path, status, checks, metrics, root)


def emit(out_path: Path | None, status: str, checks: list[dict], metrics: dict, root: Path) -> None:
    result = {
        "status": status,
        "workRoot": str(root),
        "checks": checks,
        "metrics": metrics,
        "summary": {
            "pass": sum(1 for item in checks if item["status"] == "pass"),
            "needs_work": sum(1 for item in checks if item["status"] == "needs_work"),
            "blocked": sum(1 for item in checks if item["status"] == "blocked"),
        },
        "contract": (
            "For multi-frame hybrid, reference frames define section essence and a density floor, "
            "not repeated fixed-height slides. Every adjacent seam needs rendered evidence."
        ),
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if status == "pass" else 2 if status == "blocked" else 1)


if __name__ == "__main__":
    main()
