#!/usr/bin/env python3
"""completion_gate.py — compute the run's completion verdict from artifacts.

The verdict is COMPUTED, never narrated. An agent may disagree with the
output in prose, but the completion report's headline status must be the
status this script prints. Stdlib-only; runs in every degraded mode.

Usage:
  python3 completion_gate.py MANIFEST BOX_REPORT \
      --visual-check reports/visual-check.json \
      --widths-check reports/responsive-check.json \
      --scores reports/section-scores.json \
      --artifact-check reports/artifact-check.json \
      [--page-flow reports/page-flow.json] \
      [--fv-pixel reports/fv-pixel-report.json] \
      [--impression reports/impression-metrics.json] \
      --out reports/completion-verdict.json

Statuses:
  complete  — every gate below passes.
  prototype — build is usable but at least one fidelity gate fails.
  blocked   — required evidence is missing/unreadable, or a hard check fails.

Gates (mode-aware; mode read from the manifest):
  G1 critical boxes: fv-critical, section-critical, and manifest priority
     critical/high must all pass. A Y-only recomposition waiver is allowed;
     an X/W/H failure on the same row is not waived.
  G2 overall box pass rate, Y-only waived rows excluded from both numerator
     and denominator: pixel-clone >= 0.90, production >= 0.70, hybrid >= 0.80.
  G3 FV masked pixel diff: verdict good/acceptable (pixel-clone + hybrid), or
     machine-issued not_applicable_generated_media for a manifest-bound
     full-frame generated/replaced hybrid plate while G6/G9 still pass.
     Absent report = blocked unless --no-pixel-evidence with a reason.
  G4 visual-check + widths sweep: pass at every viewport/width.
  G5 section scores: every section min-axis >= 7 and page >= 7.
  G6 impression metrics (hybrid FV): every metric within tolerance.
     Absent file = blocked for hybrid unless --no-impression-evidence.
  G7 detail dispositions: no 'missing' verdict.
  G8 photo-class asset reality (independent of self-scored axes):
     an fv/section-critical mediaClass photo/illustration element that ships no
     raster (generated/replace/crop-asset), and a section-review disposition
     that calls a photo/portrait device 'adapted'/'present' while the build
     ships no raster at all, are both prototype. Catches the reclassify-to-svg
     / drop-the-photo-then-call-it-adapted escape that self-scored G5/G7 miss.
  G9 asset-source preflight: source-frame overlap + crop reuse, missing clean
     plate evidence, or unearned fallbacks are blocked even when the adopted
     crop itself contains no visible text/UI.
  G10 Web-native page flow (multi-frame hybrid): computed section-height
      rhythm, seam crop evidence, and overflow ownership must pass. Repeated
      uniform section heights without a verbatim human intent are prototype.
  G11 artifact checklist handoff: artifact-check status must be pass. Missing,
      unreadable, blocked, or internally inconsistent evidence is blocked;
      needs_work makes the result a prototype.
  G12 independent review: when reviewPolicy requires it, a different reviewer
      judges crop pairs only; the lower fidelity/section/page score controls.
  G13 source-requested motion: runtime QA must pass in normal,
      reduced-motion, and JavaScript-disabled states and be bound to the
      current manifest. Static projects with motion.required=false skip it.

Warnings (never change the status, always recorded):
  W1 all section scores exactly equal to the pass bar (uniform-threshold
     scoring — the classic way to sneak past the gate; re-judge from pairs).
  W2 a section score entry without at least one crop-pair path.
  W3 hybrid-residual count > 40% of manifest elements.
  W4 repeated uniform section heights (stacked-slides signature).
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from _box_quality import evaluate_box_quality
from asset_preflight import evaluate_asset_policy

PASS_BAR = 7
BOX_RATE = {"pixel-clone": 0.90, "production": 0.70, "hybrid": 0.80}


def load(path, label, reasons):
    if not path or not os.path.exists(path):
        reasons.append(f"missing evidence: {label} ({path})")
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        reasons.append(f"unreadable evidence: {label} ({path}): {e}")
        return None


def file_receipt(path):
    """Return the content identity used to bind artifact-check to its inputs."""
    if not path or not os.path.isfile(path):
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = os.stat(path)
    return {
        "sha256": digest.hexdigest(),
        "size": stat.st_size,
        "mtimeNs": stat.st_mtime_ns,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("box_report")
    ap.add_argument("--visual-check")
    ap.add_argument("--widths-check")
    ap.add_argument("--scores")
    ap.add_argument("--artifact-check")
    ap.add_argument("--fv-pixel")
    ap.add_argument("--impression")
    ap.add_argument("--page-flow")
    ap.add_argument("--motion-check")
    ap.add_argument("--no-pixel-evidence", metavar="REASON",
                    help="recorded reason why the FV pixel diff is unavailable")
    ap.add_argument("--no-impression-evidence", metavar="REASON",
                    help="recorded reason why impression metrics are unavailable")
    ap.add_argument("--out")
    args = ap.parse_args()

    blocked, proto, warns = [], [], []
    metrics = {}

    manifest = load(args.manifest, "manifest", blocked)
    box = load(args.box_report, "box report", blocked)
    if manifest is not None and not isinstance(manifest, dict):
        blocked.append("invalid evidence shape: manifest root must be a JSON object")
        manifest = None
    if box is not None and not isinstance(box, dict):
        blocked.append("invalid evidence shape: box report root must be a JSON object")
        box = None
    if isinstance(box, dict) and not isinstance(box.get("items"), list):
        blocked.append("invalid evidence shape: box-report.items must be an array")
        box = None
    if manifest is None or box is None:
        emit(args, "blocked", blocked, proto, warns, metrics)
        return

    mode = manifest.get("mode", "hybrid")
    # G1 + G2 — box gates
    items = box.get("items", [])
    box_quality = evaluate_box_quality(items, manifest)
    fv_fail = box_quality["fvCriticalFailures"]
    if fv_fail:
        proto.append(f"G1 fv-critical box failures: {', '.join(fv_fail)}")
    other_critical_fail = box_quality["sectionOrPriorityFailures"]
    if other_critical_fail:
        proto.append(
            "G1 section/priority-critical box failures: "
            + ", ".join(other_critical_fail)
        )

    summary = box.get("summary", {})
    n_waived = box_quality["yOnlyWaived"]
    denom = box_quality["eligible"]
    passed = box_quality["passed"]
    rate = box_quality["rate"]
    need = BOX_RATE.get(mode, 0.80)
    metrics["box"] = {
        "reportedTotal": box_quality["total"],
        "eligibleTotal": denom,
        "effectivePassed": passed,
        "effectiveFailed": box_quality["failed"],
        "yWaiverRows": box_quality["yWaiverRows"],
        "yOnlyWaived": n_waived,
        "passRate": round(rate, 6),
        "threshold": need,
    }
    if rate < need:
        proto.append(
            f"G2 box pass rate {passed}/{denom} = {rate:.2f} < {need:.2f} "
            f"({mode}; {n_waived} Y-only waived excluded from both counts)")

    # G11 — bind the mandatory pre-completion checklist to this verdict. It
    # previously existed only as an instruction, so a stale/needs_work report
    # could be omitted while completion_gate still returned complete.
    artifact = load(args.artifact_check, "artifact-check report", blocked)
    if artifact is not None:
        artifact_status = artifact.get("status")
        inconsistent = [
            row.get("id")
            for row in artifact.get("checks", []) or []
            if row.get("status") != "pass"
        ]
        if artifact_status == "blocked":
            blocked.append("G11 artifact-check report is blocked")
        elif artifact_status == "needs_work":
            proto.append("G11 artifact-check report needs work")
        elif artifact_status != "pass":
            blocked.append(
                f"G11 artifact-check report has invalid status '{artifact_status}'"
            )
        elif inconsistent:
            blocked.append(
                "G11 artifact-check reports pass but contains non-pass checks: "
                + ", ".join(map(str, inconsistent))
            )
        receipts = artifact.get("inputs") or {}
        for label, current_path in (
            ("manifest", args.manifest),
            ("boxReport", args.box_report),
            ("sectionScores", args.scores),
            ("fvPixel", args.fv_pixel),
        ):
            audited = receipts.get(label)
            current = file_receipt(current_path)
            if not audited:
                blocked.append(
                    f"G11 artifact-check is missing the '{label}' input receipt"
                )
            elif current is None:
                blocked.append(
                    f"G11 current '{label}' input is missing or unreadable: "
                    f"{current_path}"
                )
            elif audited.get("sha256") != current["sha256"]:
                blocked.append(
                    f"G11 artifact-check '{label}' SHA-256 does not match the "
                    "current input; rerun artifact_check.py after the latest changes"
                )
            elif audited.get("size") != current["size"]:
                blocked.append(
                    f"G11 artifact-check '{label}' size does not match the current "
                    "input; rerun artifact_check.py"
                )

    # G3 — FV pixel diff
    if mode in ("pixel-clone", "hybrid"):
        if args.no_pixel_evidence:
            warns.append(f"G3 skipped, recorded reason: {args.no_pixel_evidence}")
        else:
            px = load(args.fv_pixel, "FV pixel report", blocked)
            if px is not None:
                manifest_generated_media = {
                    element.get("id") or element.get("el")
                    for element in manifest.get("elements", []) or []
                    if element.get("mediaClass") in ("photo", "illustration")
                    and element.get("assetStrategy") in ("generated", "replace")
                    and element.get("qaPriority") in ("fv-critical", "section-critical")
                    and (
                        not element.get("sourceImage")
                        or not manifest.get("image")
                        or element.get("sourceImage") == manifest.get("image")
                    )
                }
                viewport = manifest.get("viewport") or {}
                viewport_width = viewport.get("width")
                viewport_height = viewport.get("height")
                full_frame_generated_media = {
                    element.get("id") or element.get("el")
                    for element in manifest.get("elements", []) or []
                    if (element.get("id") or element.get("el")) in manifest_generated_media
                    and isinstance(element.get("bbox"), dict)
                    and isinstance(viewport_width, (int, float))
                    and isinstance(viewport_height, (int, float))
                    and element["bbox"].get("x", 1) <= 0
                    and element["bbox"].get("y", 1) <= 0
                    and element["bbox"].get("x", 0) + element["bbox"].get("w", 0) >= viewport_width
                    and element["bbox"].get("y", 0) + element["bbox"].get("h", 0) >= viewport_height
                }
                reported_generated_media = set(px.get("auto_generated_media_masks") or [])
                expected_foreground = {
                    element.get("id") or element.get("el")
                    for element in manifest.get("elements", []) or []
                    if element.get("qaPriority") == "fv-critical"
                    and element.get("pixelDiffForeground") is True
                    and (
                        not element.get("sourceImage")
                        or not manifest.get("image")
                        or element.get("sourceImage") == manifest.get("image")
                    )
                }
                reported_foreground = set(px.get("auto_foreground_carveouts") or [])
                region_rows = {
                    row.get("id"): row for row in px.get("foreground_regions", []) or []
                    if isinstance(row, dict) and row.get("id")
                }
                if reported_foreground != expected_foreground:
                    proto.append(
                        "G3 FV foreground carve-out ids do not match the current manifest"
                    )
                zero_foreground = sorted(
                    element_id for element_id in expected_foreground
                    if (region_rows.get(element_id) or {}).get("compared_px", 0) <= 0
                )
                if zero_foreground:
                    proto.append(
                        "G3 FV foreground regions have zero compared pixels: "
                        + ", ".join(zero_foreground)
                    )
                min_foreground = (manifest.get("reviewPolicy") or {}).get("minForegroundPixelCoverage", 0)
                if expected_foreground and px.get("foreground_union_coverage", 0) < min_foreground:
                    proto.append(
                        f"G3 FV foreground union coverage {px.get('foreground_union_coverage', 0):.4f} < {min_foreground:.4f}"
                    )
                generated_media_not_applicable = (
                    mode == "hybrid"
                    and manifest.get("photoLed") is True
                    and px.get("verdict") == "not_applicable_generated_media"
                    and px.get("pixel_evidence_applicable") is False
                    and bool(reported_generated_media)
                    and reported_generated_media <= full_frame_generated_media
                    and px.get("generated_media_coverage") == 1.0
                    and px.get("eligible_non_generated_media_px") == 0
                )
                if generated_media_not_applicable:
                    metrics["pixel"] = {
                        "verdict": px.get("verdict"),
                        "basis": "generated/replaced hybrid media owns the full FV; G6/G9 remain mandatory",
                        "generatedMedia": px.get("auto_generated_media_masks"),
                    }
                elif px.get("verdict") not in ("good", "acceptable"):
                    proto.append(
                        f"G3 FV pixel diff verdict '{px.get('verdict')}' "
                        f"(diff_ratio={px.get('diff_ratio')})")

    # G4 — visual-check + widths sweep
    for path, label in ((args.visual_check, "visual-check"),
                        (args.widths_check, "widths sweep")):
        vc = load(path, label, blocked)
        if vc is None:
            continue
        bad = [v["viewport"] for v in vc.get("viewports", []) if not v.get("pass")]
        if bad:
            proto.append(f"G4 {label} failing at: {', '.join(bad)}")

    # G5 + G7 + warnings — scores file
    scores = load(args.scores, "section scores", blocked)
    if scores is not None and not isinstance(scores, dict):
        blocked.append("invalid evidence shape: section-scores root must be a JSON object")
        scores = None
    if isinstance(scores, dict) and not isinstance(scores.get("sections"), list):
        blocked.append("invalid evidence shape: section-scores.sections must be an array, not an object/dict")
        scores = None
    if isinstance(scores, dict) and not isinstance(scores.get("dispositions"), list):
        blocked.append("invalid evidence shape: section-scores.dispositions must be an array of objects")
        scores = None
    if scores is not None:
        mins = []
        for s in scores.get("sections", []):
            axes = s.get("axes", {})
            if not axes:
                blocked.append(f"section '{s.get('id')}' has no axis scores")
                continue
            m = min(axes.values())
            mins.append(m)
            if m < PASS_BAR:
                proto.append(f"G5 section '{s.get('id')}' min-axis {m} < {PASS_BAR}")
            if not s.get("pairs"):
                warns.append(f"W2 section '{s.get('id')}' scored without a crop-pair path")
        page = scores.get("page", {})
        page_score = (min(page["axes"].values()) if page.get("axes")
                      else page.get("score"))
        if page_score is None:
            blocked.append("no page-as-a-page score")
        elif page_score < PASS_BAR:
            proto.append(f"G5 page score {page_score} < {PASS_BAR}")
        if mins and page_score is not None and \
                set(mins) | {page_score} == {PASS_BAR}:
            warns.append(
                "W1 every score is exactly the pass bar — uniform-threshold "
                "scoring pattern; re-judge from crop pairs (self-scores run ~3 high)")
        missing = [d.get("device") for d in scores.get("dispositions", [])
                   if d.get("verdict") == "missing"]
        if missing:
            proto.append(f"G7 missing devices: {', '.join(map(str, missing))}")

        # G12 — self-scoring cannot be the only visual judgment for the
        # high-risk multi-frame hybrid path. Artifact-check validates identity,
        # pair readability, and coverage; Phase 10 applies the lower score.
        review_policy = manifest.get("reviewPolicy") or {}
        if review_policy.get("independentReviewRequired") is True:
            provenance = scores.get("reviewProvenance") or {}
            independent = provenance.get("independent") or {}
            independent_sections = independent.get("sections")
            if not isinstance(independent_sections, list):
                proto.append("G12 independent crop-pair review is missing")
            else:
                for row in independent_sections:
                    score = row.get("score") if isinstance(row, dict) else None
                    if not isinstance(score, (int, float)) or isinstance(score, bool):
                        blocked.append("G12 independent section score has invalid shape")
                    elif score < PASS_BAR:
                        proto.append(
                            f"G12 independent section '{row.get('id')}' score {score} < {PASS_BAR}"
                        )
                independent_page = independent.get("pageScore")
                if not isinstance(independent_page, (int, float)) or isinstance(independent_page, bool):
                    blocked.append("G12 independent page score is missing or invalid")
                elif independent_page < PASS_BAR:
                    proto.append(f"G12 independent page score {independent_page} < {PASS_BAR}")

            self_fidelity = scores.get("compFidelityScore")
            independent_fidelity = independent.get("compFidelityScore")
            if all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                for value in (self_fidelity, independent_fidelity)
            ):
                effective_fidelity = min(self_fidelity, independent_fidelity)
                delta = abs(self_fidelity - independent_fidelity)
                metrics["review"] = {
                    "implementerCompFidelity": self_fidelity,
                    "independentCompFidelity": independent_fidelity,
                    "effectiveCompFidelity": effective_fidelity,
                    "scoreDelta": delta,
                }
                if effective_fidelity < 70:
                    proto.append(
                        f"G12 effective comp-fidelity score {effective_fidelity} < 70"
                    )
                maximum_delta = review_policy.get("maxIndependentScoreDelta", 10)
                if delta >= maximum_delta:
                    proto.append(
                        f"G12 implementer/independent score delta {delta:.1f} >= {maximum_delta:.1f}; lower score controls"
                    )

    # G8 — photo-class asset reality (independent of self-scored axes)
    elements = manifest.get("elements", [])
    RASTER_STRATEGIES = ("generated", "replace", "crop-asset")
    shipped_raster = any(
        e.get("mediaClass") in ("photo", "illustration")
        and e.get("assetStrategy") in RASTER_STRATEGIES
        for e in elements
    )
    for e in elements:
        if e.get("mediaClass") in ("photo", "illustration") and \
                e.get("qaPriority") in ("fv-critical", "section-critical"):
            strat = e.get("assetStrategy")
            if strat not in RASTER_STRATEGIES:
                if strat == "placeholder":
                    proto.append(
                        f"G8 photo region '{e.get('id')}' is a placeholder — "
                        "ship the real text-free raster (generate/replace) before "
                        "completion")
                else:
                    proto.append(
                        f"G8 photo region '{e.get('id')}' has mediaClass="
                        f"'{e.get('mediaClass')}' but assetStrategy='{strat}' is not "
                        "a shipped raster — a photographic subject may not be "
                        "reclassified to svg/css/ui-mock to bypass the asset policy")
    if scores is not None and not shipped_raster:
        photo_words = ("photo", "portrait", "headshot", "photograph")
        for d in scores.get("dispositions", []):
            device = str(d.get("device", ""))
            verdict = d.get("verdict")
            if verdict in ("adapted", "present") and \
                    any(w in device.lower() for w in photo_words):
                proto.append(
                    f"G8 disposition '{device}' claims a photo device "
                    f"('{verdict}') but the build ships no raster asset "
                    "(generated/replace/crop-asset) — a removed or reclassified "
                    "photographic subject is 'missing', not adapted/present")

    # G9 — enforce the same source/composition decision before and after the
    # build. A crop that escaped overlap by narrowing the frame is not a clean
    # background plate.
    asset_policy = evaluate_asset_policy(
        manifest, Path(args.manifest).resolve().parent
    )
    for row in asset_policy.get("checks", []):
        if row.get("status") == "blocked":
            blocked.append(
                f"G9 asset policy '{row.get('elementId', 'manifest')}': "
                f"{row.get('message')}"
            )
        elif row.get("status") == "needs_work":
            proto.append(
                f"G9 asset policy '{row.get('elementId', 'manifest')}': "
                f"{row.get('message')}"
            )

    # G6 — impression metrics (hybrid)
    if mode == "hybrid":
        if args.no_impression_evidence:
            warns.append(f"G6 skipped, recorded reason: {args.no_impression_evidence}")
        else:
            imp = load(args.impression, "impression metrics", blocked)
            if imp is not None:
                for m in imp.get("metrics", []):
                    if not m.get("pass"):
                        proto.append(
                            f"G6 impression metric '{m.get('metric')}' out of "
                            f"tolerance (comp={m.get('comp')} build={m.get('build')} "
                            f"delta={m.get('delta_pct')}% tol={m.get('tolerance_pct')}%)")

    # G10 — multi-frame page composition. Section comps define essence and a
    # density floor; they are not seven equal-height CSS section templates.
    section_comp_count = sum(
        1 for ref in manifest.get("referenceImages", []) or []
        if ref.get("use") == "section-comp" and ref.get("section")
    )
    if mode == "hybrid" and section_comp_count >= 2:
        flow = load(args.page_flow, "page-flow report", blocked)
        if flow is not None:
            flow_status = flow.get("status")
            failing = list(dict.fromkeys(
                item.get("id")
                for item in flow.get("checks", []) or []
                if item.get("status") != "pass"
            ))
            if flow_status == "blocked":
                blocked.append(
                    "G10 page-flow report is blocked: " + ", ".join(map(str, failing))
                )
            elif flow_status != "pass":
                proto.append(
                    "G10 page-flow needs work: " + ", ".join(map(str, failing))
                )
            if flow.get("metrics", {}).get("stackedFrameLock"):
                warns.append(
                    "W4 all rendered section heights remain locked to one repeated "
                    "height — stacked-slides signature"
                )

    # G13 — only projects with an explicit source-requested motion contract.
    if (manifest.get("motion") or {}).get("required") is True:
        if not args.motion_check or not os.path.isfile(args.motion_check):
            proto.append("G13 source-requested motion has no runtime motion-check report")
        else:
            motion_report = load(args.motion_check, "motion-check report", blocked)
            if motion_report is not None:
                if motion_report.get("status") != "pass":
                    proto.append(f"G13 motion-check status is {motion_report.get('status')}")
                current_manifest = file_receipt(args.manifest)
                audited_manifest = motion_report.get("manifest") or {}
                if (
                    current_manifest is None
                    or audited_manifest.get("sha256") != current_manifest.get("sha256")
                    or audited_manifest.get("size") != current_manifest.get("size")
                ):
                    blocked.append("G13 motion-check manifest receipt is stale or mismatched")

    # W3 — residual volume
    residuals = summary.get("fail", 0)
    n_elements = max(len(manifest.get("elements", [])), 1)
    if residuals / n_elements > 0.40:
        warns.append(
            f"W3 {residuals}/{n_elements} elements unresolved — 'hybrid residual' "
            "at this volume is a fidelity failure, not a disposition")

    status = "blocked" if blocked else ("prototype" if proto else "complete")
    emit(args, status, blocked, proto, warns, metrics)


def emit(args, status, blocked, proto, warns, metrics=None):
    result = {
        "status": status,
        "blocked_reasons": blocked,
        "prototype_reasons": proto,
        "warnings": warns,
        "metrics": metrics or {},
        "contract": ("The completion report's headline status MUST be this "
                     "status. Prose may explain, never override."),
    }
    out = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w") as f:
            f.write(out + "\n")
    print(out)
    sys.exit(0 if status == "complete" else 2 if status == "blocked" else 1)


if __name__ == "__main__":
    main()
