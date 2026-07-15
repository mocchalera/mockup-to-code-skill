#!/usr/bin/env python3
"""artifact_check.py — preflight the evidence bundle before completion_gate.

This is the "did we actually gather enough proof?" check. completion_gate.py
computes the final status from the core QA artifacts; this script catches the
field failures that happen just before that point: sparse crop pairs, unchecked
generated assets, fused-source crops that changed the comp's photo composition,
bbox/tolerance edits without measurement provenance, and prototype-level FV
evidence being buried in prose. It also requires class-matched font bake-off
evidence for critical structural text and readable evidence for any exceptional
glyph transform.

Usage:
  python3 artifact_check.py WORK_ROOT \
      [--manifest WORK_ROOT/manifest.json] \
      [--box-report WORK_ROOT/reports/box-report.json] \
      [--scores WORK_ROOT/reports/section-scores.json] \
      [--section-review WORK_ROOT/reports/section-review.md] \
      [--photo-review WORK_ROOT/reports/photo-asset-review.md] \
      [--fv-pixel WORK_ROOT/reports/fv-pixel-report.json] \
      [--page-flow WORK_ROOT/reports/page-flow.json] \
      [--out WORK_ROOT/reports/artifact-check.json]

Exit codes:
  0 pass, 1 needs_work, 2 blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from _box_quality import evaluate_box_quality
from asset_preflight import evaluate_asset_policy
from contract_doctor import (
    validate_generation_provenance,
    validate_photo_geometry,
    validate_semantic_photo_separation,
    validate_specialist_reports,
    validate_typography_specialist_report,
)


BOX_RATE = {"pixel-clone": 0.90, "production": 0.70, "hybrid": 0.80}
PAIR_KEYS = ("pair", "pairPath", "pair_path", "cropPair", "crop_pair")


def read_json(path: Path, label: str, checks: list[dict]) -> dict | None:
    if not path.exists():
        checks.append(check("blocked", f"missing-{label}", f"missing required artifact: {path}"))
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(check("blocked", f"unreadable-{label}", f"unreadable {label}: {path}: {exc}"))
        return None


def read_text(path: Path, label: str, checks: list[dict], required: bool = True) -> str:
    if not path.exists():
        if required:
            checks.append(check("blocked", f"missing-{label}", f"missing required artifact: {path}"))
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(check("blocked", f"unreadable-{label}", f"unreadable {label}: {path}: {exc}"))
        return ""


def check(status: str, cid: str, message: str, **extra) -> dict:
    row = {"id": cid, "status": status, "message": message}
    row.update(extra)
    return row


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [root / path, root.parent / path, Path.cwd() / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return root / path


def path_exists(root: Path, value: str | None) -> bool:
    resolved = resolve_path(root, value)
    return bool(resolved and resolved.is_file() and resolved.stat().st_size > 0)


def file_receipt(path: Path) -> dict | None:
    """Return a stable receipt for a file used by the artifact audit."""
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "path": str(path),
        "sha256": digest.hexdigest(),
        "size": stat.st_size,
        "mtimeNs": stat.st_mtime_ns,
    }


def is_newer(source: Path, derived: Path) -> bool:
    """Whether a source changed after an artifact derived from it."""
    return source.is_file() and derived.is_file() and source.stat().st_mtime_ns > derived.stat().st_mtime_ns


def pair_value(row: dict) -> str | None:
    for key in PAIR_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def collect_pairs(scores: dict) -> set[str]:
    pairs: set[str] = set()
    for section in scores.get("sections", []):
        for value in section.get("pairs", []) or []:
            if isinstance(value, str) and value:
                pairs.add(value)
    for row in scores.get("dispositions", []) or []:
        value = pair_value(row)
        if value:
            pairs.add(value)
    return pairs


def has_waiver(row: dict) -> bool:
    return bool(row.get("waiverQuote") or row.get("waiver") or row.get("userWaiver"))


def score_has_two_track_review(scores: dict, review_text: str) -> bool:
    score_keys = set(scores.keys())
    has_json = (
        {"webQualityScore", "compFidelityScore"} <= score_keys
        or {"web_quality", "comp_fidelity"} <= score_keys
    )
    lowered = review_text.lower()
    has_md = (
        ("web品質" in review_text or "web quality" in lowered or "web-quality" in lowered)
        and (
            "カンプ再現" in review_text
            or "comp fidelity" in lowered
            or "mockup fidelity" in lowered
            or "comp-fidelity" in lowered
        )
    )
    return has_json or has_md


def finite_score(value, minimum=0, maximum=100) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and minimum <= value <= maximum


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("work_root")
    ap.add_argument("--manifest")
    ap.add_argument("--box-report")
    ap.add_argument("--scores")
    ap.add_argument("--section-review")
    ap.add_argument("--photo-review")
    ap.add_argument("--fv-pixel")
    ap.add_argument("--page-flow")
    ap.add_argument("--out")
    ap.add_argument("--min-crop-pairs", type=int, default=1)
    args = ap.parse_args()

    root = Path(args.work_root)
    manifest_path = Path(args.manifest) if args.manifest else root / "manifest.json"
    box_path = Path(args.box_report) if args.box_report else root / "reports" / "box-report.json"
    scores_path = Path(args.scores) if args.scores else root / "reports" / "section-scores.json"
    review_path = Path(args.section_review) if args.section_review else root / "reports" / "section-review.md"
    photo_review_path = (
        Path(args.photo_review) if args.photo_review else root / "reports" / "photo-asset-review.md"
    )
    pixel_path = Path(args.fv_pixel) if args.fv_pixel else root / "reports" / "fv-pixel-report.json"
    page_flow_path = Path(args.page_flow) if args.page_flow else root / "reports" / "page-flow.json"
    out_path = Path(args.out) if args.out else None

    checks: list[dict] = []
    manifest = read_json(manifest_path, "manifest", checks)
    box = read_json(box_path, "box-report", checks)
    scores = read_json(scores_path, "section-scores", checks)
    review_text = read_text(review_path, "section-review", checks)

    receipt_paths = {
        "manifest": manifest_path,
        "boxReport": box_path,
        "sectionScores": scores_path,
        "sectionReview": review_path,
        "photoReview": photo_review_path,
        "fvPixel": pixel_path,
        "pageFlow": page_flow_path,
    }
    receipts = {
        label: receipt
        for label, path in receipt_paths.items()
        if (receipt := file_receipt(path)) is not None
    }

    shape_errors = []
    if manifest is not None and not isinstance(manifest, dict):
        shape_errors.append(("manifest-object", "manifest root must be a JSON object"))
    if box is not None and not isinstance(box, dict):
        shape_errors.append(("box-report-object", "box-report root must be a JSON object"))
    if scores is not None and not isinstance(scores, dict):
        shape_errors.append(("section-scores-object", "section-scores root must be a JSON object"))
    if isinstance(manifest, dict) and not isinstance(manifest.get("elements"), list):
        shape_errors.append(("manifest-elements-array", "manifest.elements must be an array"))
    if isinstance(box, dict) and not isinstance(box.get("items"), list):
        shape_errors.append(("box-report-items-array", "box-report.items must be an array"))
    if isinstance(scores, dict):
        if not isinstance(scores.get("sections"), list):
            shape_errors.append(
                ("section-scores-sections-array", "section-scores.sections must be an array, not an object/dict")
            )
        elif any(not isinstance(row, dict) for row in scores.get("sections", [])):
            shape_errors.append(("section-score-rows", "every section-scores.sections row must be an object"))
        if not isinstance(scores.get("dispositions"), list):
            shape_errors.append(
                ("section-scores-dispositions-array", "section-scores.dispositions must be an array of objects")
            )
        elif any(not isinstance(row, dict) for row in scores.get("dispositions", [])):
            shape_errors.append(
                ("section-score-disposition-rows", "every section-scores.dispositions row must be an object")
            )
    for cid, message in shape_errors:
        checks.append(check("blocked", cid, message))

    if manifest is None or box is None or scores is None or shape_errors:
        emit(out_path, "blocked", checks, root, receipts)
        return

    mode = manifest.get("mode", "hybrid")

    # C1 — crop pair density and coverage.
    pairs = collect_pairs(scores)
    missing_pairs = sorted(p for p in pairs if not path_exists(root, p))
    section_count = len(scores.get("sections", []) or [])
    minimum_pairs = max(args.min_crop_pairs, section_count)
    if len(pairs) < minimum_pairs:
        checks.append(
            check(
                "needs_work",
                "crop-pair-count",
                f"only {len(pairs)} crop pair(s) declared; expected at least {minimum_pairs}",
                declaredPairs=sorted(pairs),
            )
        )
    elif missing_pairs:
        checks.append(
            check(
                "blocked",
                "crop-pair-files",
                f"{len(missing_pairs)} declared crop pair file(s) are missing",
                missing=missing_pairs,
            )
        )
    else:
        checks.append(check("pass", "crop-pair-coverage", f"{len(pairs)} crop pair(s) declared and readable"))

    for section in scores.get("sections", []) or []:
        if not section.get("pairs"):
            checks.append(
                check("needs_work", "section-pair-missing", f"section '{section.get('id')}' has no crop pair path")
            )

    for row in scores.get("dispositions", []) or []:
        verdict = row.get("verdict")
        if verdict == "waived":
            if not has_waiver(row):
                checks.append(
                    check(
                        "needs_work",
                        "waiver-quote-missing",
                        f"waived device '{row.get('device')}' lacks the user's verbatim waiver",
                    )
                )
        elif not pair_value(row):
            checks.append(
                check(
                    "needs_work",
                    "disposition-pair-missing",
                    f"device '{row.get('device')}' verdict '{verdict}' has no crop-pair path",
                )
            )

    # C1b — bind every Phase 1 source device to one scored disposition. A
    # section-level crop is not proof that its distinctive micro-devices were
    # preserved, and free-form device names cannot be reconciled reliably.
    inventory = manifest.get("detailInventory") or []
    if inventory:
        dispositions = scores.get("dispositions", []) or []
        by_inventory = {}
        duplicate_inventory_ids = []
        for row in dispositions:
            inventory_id = row.get("inventoryId")
            if not inventory_id:
                continue
            if inventory_id in by_inventory:
                duplicate_inventory_ids.append(inventory_id)
            by_inventory[inventory_id] = row
        if duplicate_inventory_ids:
            checks.append(
                check(
                    "blocked",
                    "detail-inventory-duplicate-disposition",
                    "an inventory item may have only one final disposition",
                    inventoryIds=sorted(set(duplicate_inventory_ids)),
                )
            )
        missing_inventory = [row.get("id") for row in inventory if row.get("id") not in by_inventory]
        if missing_inventory:
            checks.append(
                check(
                    "needs_work",
                    "detail-inventory-coverage",
                    "every detailInventory row needs a matching disposition.inventoryId",
                    missing=missing_inventory,
                )
            )
        else:
            checks.append(
                check(
                    "pass",
                    "detail-inventory-coverage",
                    f"all {len(inventory)} detail inventory row(s) are dispositioned",
                )
            )

        source_specific = [row for row in inventory if row.get("sourceSpecific") is True]
        adapted = [
            row for row in source_specific
            if (by_inventory.get(row.get("id")) or {}).get("verdict") == "adapted"
        ]
        ratio = len(adapted) / len(source_specific) if source_specific else 0.0
        maximum = (manifest.get("reviewPolicy") or {}).get("maxAdaptedSourceSpecificRatio", 0.2)
        if ratio > maximum:
            checks.append(
                check(
                    "needs_work",
                    "source-specific-adaptation-volume",
                    f"{len(adapted)}/{len(source_specific)} source-specific devices are adapted ({ratio:.2f}) above {maximum:.2f}",
                    adapted=[row.get("id") for row in adapted],
                )
            )
        else:
            checks.append(
                check(
                    "pass",
                    "source-specific-adaptation-volume",
                    f"source-specific adapted ratio {ratio:.2f} is within {maximum:.2f}",
                )
            )

    # C2 — box pass rate and FV-first guardrail.
    box_quality = evaluate_box_quality(box.get("items", []) or [], manifest)
    denom = box_quality["eligible"]
    effective_passed = box_quality["passed"]
    waived = box_quality["yOnlyWaived"]
    rate = box_quality["rate"]
    need = BOX_RATE.get(mode, 0.80)
    if rate < need:
        checks.append(
            check(
                "needs_work",
                "box-pass-rate",
                f"box pass rate {effective_passed}/{denom} = {rate:.2f} below {mode} threshold {need:.2f}",
            )
        )
    else:
        checks.append(check("pass", "box-pass-rate", f"box pass rate {effective_passed}/{denom} = {rate:.2f}"))

    fv_fail = box_quality["fvCriticalFailures"]
    if fv_fail:
        checks.append(
            check(
                "needs_work",
                "fv-first-boxes",
                "FV-only mode: do not build or polish below-FV while fv-critical boxes fail",
                failing=fv_fail,
                belowFvAllowed=False,
            )
        )

    other_critical_fail = box_quality["sectionOrPriorityFailures"]
    if other_critical_fail:
        checks.append(
            check(
                "needs_work",
                "critical-boxes",
                "section-critical or priority critical/high boxes still fail",
                failing=other_critical_fail,
            )
        )

    if pixel_path.exists():
        pixel = read_json(pixel_path, "fv-pixel", checks)
        if pixel:
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
            reported_generated_media = set(pixel.get("auto_generated_media_masks") or [])
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
            expected_exclusions = {
                element.get("id") or element.get("el")
                for element in manifest.get("elements", []) or []
                if element.get("qaPriority") == "fv-critical"
                and element.get("pixelDiffForegroundExclusion")
                and (
                    not element.get("sourceImage")
                    or not manifest.get("image")
                    or element.get("sourceImage") == manifest.get("image")
                )
            }
            reported_foreground = set(pixel.get("auto_foreground_carveouts") or [])
            reported_exclusions = set(pixel.get("auto_foreground_exclusions") or [])
            foreground_regions = {
                row.get("id"): row for row in pixel.get("foreground_regions", []) or []
                if isinstance(row, dict) and row.get("id")
            }
            foreground_failures = []
            if reported_foreground != expected_foreground:
                foreground_failures.append(
                    {"kind": "carveout-ids", "expected": sorted(expected_foreground), "actual": sorted(reported_foreground)}
                )
            if reported_exclusions != expected_exclusions:
                foreground_failures.append(
                    {"kind": "exclusion-ids", "expected": sorted(expected_exclusions), "actual": sorted(reported_exclusions)}
                )
            zero_regions = sorted(
                element_id for element_id in expected_foreground
                if (foreground_regions.get(element_id) or {}).get("compared_px", 0) <= 0
            )
            if zero_regions:
                foreground_failures.append({"kind": "zero-compared-pixels", "ids": zero_regions})
            minimum_foreground = (manifest.get("reviewPolicy") or {}).get("minForegroundPixelCoverage", 0)
            if expected_foreground and pixel.get("foreground_union_coverage", 0) < minimum_foreground:
                foreground_failures.append(
                    {
                        "kind": "foreground-union-coverage",
                        "actual": pixel.get("foreground_union_coverage"),
                        "minimum": minimum_foreground,
                    }
                )
            if foreground_failures:
                checks.append(
                    check(
                        "needs_work",
                        "fv-pixel-foreground-coverage",
                        "FV foreground pixel evidence is incomplete",
                        failures=foreground_failures,
                    )
                )
            elif expected_foreground or expected_exclusions:
                checks.append(
                    check(
                        "pass",
                        "fv-pixel-foreground-coverage",
                        f"{len(expected_foreground)} opaque foreground region(s) compared and {len(expected_exclusions)} explicitly excluded",
                    )
                )
            generated_media_not_applicable = (
                mode == "hybrid"
                and manifest.get("photoLed") is True
                and pixel.get("verdict") == "not_applicable_generated_media"
                and pixel.get("pixel_evidence_applicable") is False
                and bool(reported_generated_media)
                and reported_generated_media <= full_frame_generated_media
                and pixel.get("generated_media_coverage") == 1.0
                and pixel.get("eligible_non_generated_media_px") == 0
            )
            if generated_media_not_applicable:
                checks.append(
                    check(
                        "pass",
                        "fv-pixel-generated-media-not-applicable",
                        "FV is fully owned by declared generated/replaced hybrid media; pixel identity is not applicable and asset/impression evidence remains mandatory",
                        generatedMedia=pixel.get("auto_generated_media_masks"),
                    )
                )
            elif "comparison_coverage" not in pixel or "coverage_sufficient" not in pixel:
                checks.append(
                    check(
                        "needs_work",
                        "fv-pixel-coverage-missing",
                        "FV pixel report predates comparison-coverage accounting; rerun pixel_diff.py",
                    )
                )
            elif not pixel.get("coverage_sufficient"):
                checks.append(
                    check(
                        "needs_work",
                        "fv-pixel-coverage",
                        "FV pixel comparison masks too much of the frame to support a verdict",
                        comparisonCoverage=pixel.get("comparison_coverage"),
                        minimumCoverage=pixel.get("min_comparison_coverage"),
                    )
                )
            if not generated_media_not_applicable and pixel.get("verdict") not in ("good", "acceptable"):
                checks.append(
                    check(
                        "needs_work",
                        "fv-pixel-warning",
                        "FV pixel diff is not acceptable; final report must lead with prototype/needs_work",
                        verdict=pixel.get("verdict"),
                        diff_ratio=pixel.get("diff_ratio"),
                    )
                )
    elif mode in ("pixel-clone", "hybrid"):
        checks.append(check("blocked", "fv-pixel-missing", f"missing FV pixel report: {pixel_path}"))

    # C3 — bbox ledger and tolerance provenance.
    for element in manifest.get("elements", []) or []:
        qa = element.get("qaPriority")
        if qa not in ("fv-critical", "section-critical"):
            continue
        if element.get("bboxSource") == "implementation-derived":
            checks.append(
                check(
                    "blocked",
                    "bbox-implementation-derived",
                    f"critical element '{element.get('id')}' uses implementation-derived bbox",
                )
            )
        if element.get("bbox") and not element.get("measurementRef"):
            checks.append(
                check(
                    "needs_work",
                    "bbox-ledger-missing",
                    f"critical element '{element.get('id')}' has bbox but no measurementRef ledger",
                )
            )
        if element.get("tolerance") and not element.get("toleranceReason"):
            checks.append(
                check(
                    "needs_work",
                    "tolerance-reason-missing",
                    f"element '{element.get('id')}' overrides tolerance without toleranceReason",
                )
            )

        if (
            element.get("mediaClass") in ("photo", "illustration")
            and not element.get("photoCompositionMode")
        ):
            checks.append(
                check(
                    "needs_work",
                    "photo-composition-mode-missing",
                    f"critical visual '{element.get('id')}' lacks photoCompositionMode topology decision",
                )
            )

        integration = element.get("cardPhotoIntegration")
        if integration and not path_exists(root, integration.get("pairPath")):
            checks.append(
                check(
                    "blocked",
                    "card-photo-integration-evidence-missing",
                    f"critical visual '{element.get('id')}' lacks readable card/photo integration evidence",
                )
            )

        if (
            element.get("mediaClass") in ("photo", "illustration")
            and element.get("visualRole") in ("contained-photo", "object-detail")
        ):
            surface = element.get("assetSurfaceContract")
            if not isinstance(surface, dict):
                checks.append(
                    check(
                        "blocked",
                        "asset-surface-contract-missing",
                        f"critical visual '{element.get('id')}' lacks raster/CSS surface ownership contract",
                    )
                )
            elif not path_exists(root, surface.get("reviewPath")):
                checks.append(
                    check(
                        "blocked",
                        "asset-surface-review-missing",
                        f"critical visual '{element.get('id')}' lacks isolated-asset plus crop-in-use review",
                    )
                )

        multi_zone = element.get("multiZoneAsset")
        if multi_zone:
            missing_zone_pairs = [
                zone.get("pairPath")
                for zone in multi_zone.get("zones", [])
                if not path_exists(root, zone.get("pairPath"))
            ]
            if missing_zone_pairs:
                checks.append(
                    check(
                        "blocked",
                        "multi-zone-integration-evidence-missing",
                        f"critical visual '{element.get('id')}' lacks readable per-consumer crop-in-use evidence",
                        missing=missing_zone_pairs,
                    )
                )

        craft = element.get("decorativeCraft")
        if craft and not path_exists(root, craft.get("evidencePath")):
            checks.append(
                check(
                    "blocked",
                    "decorative-craft-evidence-missing",
                    f"critical visual '{element.get('id')}' lacks readable decorative-craft evidence",
                )
            )
        if isinstance(craft, dict) and craft.get("geometryPrimitive") == "ellipse":
            exception = craft.get("ellipseException")
            if not isinstance(exception, dict) or exception.get("sourceEvidenced") is not True:
                checks.append(
                    check(
                        "blocked",
                        "unevidenced-large-ellipse",
                        f"decorative visual '{element.get('id')}' uses an ellipse without source evidence",
                    )
                )

        # Critical structural text must prove the font-class decision before
        # bbox tuning. Lettering decals are assets, not structural typography.
        if element.get("text") and element.get("mediaClass") != "lettering-decal":
            type_spec = element.get("typeSpec") or {}
            if not type_spec.get("letterformClass"):
                checks.append(
                    check(
                        "needs_work",
                        "typography-letterform-class-missing",
                        f"critical text '{element.get('id')}' lacks source letterformClass",
                    )
                )

            bakeoff = type_spec.get("fontBakeoffEvidence") or []
            if len(bakeoff) < 2:
                checks.append(
                    check(
                        "needs_work",
                        "typography-font-bakeoff-missing",
                        f"critical text '{element.get('id')}' needs at least two same-class font bake-off pairs",
                    )
                )
            else:
                missing_bakeoff = [path for path in bakeoff if not path_exists(root, path)]
                if missing_bakeoff:
                    checks.append(
                        check(
                            "blocked",
                            "typography-font-bakeoff-files-missing",
                            f"critical text '{element.get('id')}' declares unreadable font bake-off evidence",
                            missing=missing_bakeoff,
                        )
                    )

            transform_exception = type_spec.get("transformException")
            if transform_exception and not path_exists(root, transform_exception.get("evidencePath")):
                checks.append(
                    check(
                        "blocked",
                        "typography-transform-evidence-missing",
                        f"critical text '{element.get('id')}' transform exception lacks readable source evidence",
                    )
                )

            punctuation = type_spec.get("lineStartPunctuation")
            if punctuation and not path_exists(root, punctuation.get("evidencePath")):
                checks.append(
                    check(
                        "blocked",
                        "typography-punctuation-evidence-missing",
                        f"critical text '{element.get('id')}' lacks readable line-start punctuation evidence",
                    )
                )

    # C4 — run the same asset-source policy used before CSS. This catches the
    # clean-subcrop escape: a crop can contain no text while still discarding
    # the overlapped environment the comp specified.
    asset_preflight = evaluate_asset_policy(manifest, root)
    if asset_preflight["status"] == "pass":
        checks.append(
            check(
                "pass",
                "asset-preflight",
                "photo/illustration asset decisions pass the pre-CSS source and evidence gate",
            )
        )
    else:
        for row in asset_preflight.get("checks", []):
            if row.get("status") == "pass":
                continue
            checks.append(
                check(
                    row.get("status", "blocked"),
                    row.get("id", "asset-preflight"),
                    row.get("message", "asset preflight failed"),
                    elementId=row.get("elementId"),
                )
            )

    # Re-run high-value pre-CSS contracts at completion. This prevents a run
    # that skipped contract_doctor.py from reaching G11 with summarized prompts,
    # collapsed semantic photos, or an unreviewed Japanese typography report.
    specialist_checks = []
    validate_generation_provenance(manifest, root, specialist_checks)
    validate_semantic_photo_separation(manifest, specialist_checks)
    validate_photo_geometry(manifest, specialist_checks)
    validate_typography_specialist_report(manifest, root, "completion", specialist_checks)
    validate_specialist_reports(manifest, root, "completion", specialist_checks)
    for row in specialist_checks:
        checks.append(
            check(
                row.get("status", "blocked"),
                f"contract:{row.get('id', 'specialist')}",
                row.get("message", "specialist contract failed"),
                details={key: value for key, value in row.items() if key not in ("status", "id", "message")},
            )
        )

    # C5 — two-track final reporting.
    if score_has_two_track_review(scores, review_text):
        checks.append(check("pass", "two-track-scoring", "WEB quality and comp fidelity are scored separately"))
    else:
        checks.append(
            check(
                "needs_work",
                "two-track-scoring",
                "final review must separate WEB品質/Web quality from カンプ再現度/comp fidelity",
            )
        )

    # C5b — independent crop-pair review. It is deliberately stored inside
    # section-scores so artifact receipts bind the self and independent
    # assessments together. The lower score remains visible to Phase 10.
    policy = manifest.get("reviewPolicy") or {}
    if policy.get("independentReviewRequired") is True:
        provenance = scores.get("reviewProvenance") or {}
        implementer = provenance.get("implementer") or {}
        independent = provenance.get("independent") or {}
        review_errors = []
        if not implementer.get("reviewerId"):
            review_errors.append("implementer.reviewerId missing")
        if independent.get("reviewerKind") not in ("separate-agent", "human"):
            review_errors.append("independent.reviewerKind must be separate-agent or human")
        if not independent.get("reviewerId"):
            review_errors.append("independent.reviewerId missing")
        elif independent.get("reviewerId") == implementer.get("reviewerId"):
            review_errors.append("independent reviewerId must differ from implementer reviewerId")
        if independent.get("inputScope") != "crop-pairs-only":
            review_errors.append("independent.inputScope must be crop-pairs-only")
        for key in ("webQualityScore", "compFidelityScore"):
            if not finite_score(independent.get(key)):
                review_errors.append(f"independent.{key} must be 0..100")
        if not finite_score(independent.get("pageScore"), 0, 10):
            review_errors.append("independent.pageScore must be 0..10")
        if not independent.get("reviewedAt"):
            review_errors.append("independent.reviewedAt missing")
        if not independent.get("topGaps"):
            review_errors.append("independent.topGaps must be non-empty")

        independent_sections = independent.get("sections")
        scored_ids = {row.get("id") for row in scores.get("sections", []) or []}
        if not isinstance(independent_sections, list):
            review_errors.append("independent.sections must be an array")
        else:
            independent_ids = {row.get("id") for row in independent_sections if isinstance(row, dict)}
            if independent_ids != scored_ids:
                review_errors.append("independent.sections must cover exactly the scored section ids")
            for row in independent_sections:
                if not isinstance(row, dict) or not finite_score(row.get("score"), 0, 10):
                    review_errors.append("every independent section needs score 0..10")
                    continue
                row_pairs = row.get("pairs") or []
                if not row_pairs or any(not path_exists(root, path) for path in row_pairs):
                    review_errors.append(f"independent section '{row.get('id')}' needs readable crop pairs")
        reviewed_pairs = independent.get("reviewedPairs") or []
        if not reviewed_pairs or any(not path_exists(root, path) for path in reviewed_pairs):
            review_errors.append("independent.reviewedPairs must be non-empty and readable")

        if review_errors:
            checks.append(
                check(
                    "needs_work",
                    "independent-review",
                    "independent blind crop review is incomplete or not independent",
                    errors=review_errors,
                )
            )
        else:
            checks.append(
                check(
                    "pass",
                    "independent-review",
                    "independent crop-pair review covers every scored section",
                    reviewerKind=independent.get("reviewerKind"),
                    reviewerId=independent.get("reviewerId"),
                )
            )
            self_fidelity = scores.get("compFidelityScore")
            independent_fidelity = independent.get("compFidelityScore")
            if finite_score(self_fidelity) and finite_score(independent_fidelity):
                delta = abs(self_fidelity - independent_fidelity)
                maximum_delta = policy.get("maxIndependentScoreDelta", 10)
                if delta >= maximum_delta:
                    checks.append(
                        check(
                            "needs_work",
                            "independent-score-delta",
                            f"implementer/independent comp-fidelity delta {delta:.1f} meets/exceeds {maximum_delta:.1f}; use the lower score and revisit the visible gaps",
                            implementer=self_fidelity,
                            independent=independent_fidelity,
                            effective=min(self_fidelity, independent_fidelity),
                        )
                    )
                else:
                    checks.append(
                        check(
                            "pass",
                            "independent-score-delta",
                            f"implementer/independent comp-fidelity delta {delta:.1f} is within {maximum_delta:.1f}",
                            effective=min(self_fidelity, independent_fidelity),
                        )
                    )

    # C6 — Web-native page composition for multi-frame hybrid. A prose seam
    # plan and self-authored page score are not evidence that repeated 16:9
    # section comps became one scrolling page.
    section_comp_count = sum(
        1 for ref in manifest.get("referenceImages", []) or []
        if ref.get("use") == "section-comp" and ref.get("section")
    )
    if mode == "hybrid" and section_comp_count >= 2:
        if not page_flow_path.exists():
            checks.append(
                check(
                    "needs_work",
                    "page-flow-missing",
                    f"multi-frame hybrid requires computed page-flow evidence: {page_flow_path}",
                )
            )
        else:
            page_flow = read_json(page_flow_path, "page-flow", checks)
            if page_flow:
                flow_status = page_flow.get("status")
                if flow_status == "pass":
                    checks.append(
                        check(
                            "pass",
                            "page-flow",
                            "section-height rhythm, seam evidence, and overflow ownership pass",
                        )
                    )
                else:
                    failing = list(dict.fromkeys(
                        item.get("id")
                        for item in page_flow.get("checks", []) or []
                        if item.get("status") != "pass"
                    ))
                    checks.append(
                        check(
                            "blocked" if flow_status == "blocked" else "needs_work",
                            "page-flow",
                            f"page-flow status is {flow_status}; the page may still read as stacked slides",
                            failing=failing,
                        )
                    )

    # C7 — evidence provenance and freshness. A review or score generated
    # before the latest geometry report is stale even if every required file
    # still exists. Hash receipts also let completion_gate verify that the
    # artifact audit still describes the files currently on disk.
    freshness_failures = []
    if is_newer(manifest_path, box_path):
        freshness_failures.append(
            ("stale-box-report", "manifest is newer than box-report; re-render and re-diff")
        )
    if is_newer(box_path, scores_path):
        freshness_failures.append(
            ("stale-section-scores", "section-scores predate the latest box-report")
        )
    if is_newer(box_path, review_path):
        freshness_failures.append(
            ("stale-section-review", "section-review predates the latest box-report")
        )
    if mode in ("pixel-clone", "hybrid") and is_newer(manifest_path, pixel_path):
        freshness_failures.append(
            ("stale-fv-pixel", "manifest is newer than FV pixel evidence")
        )

    if freshness_failures:
        for cid, message in freshness_failures:
            checks.append(check("needs_work", cid, message))
    else:
        checks.append(
            check(
                "pass",
                "evidence-freshness",
                "box, review, score, and pixel artifacts are ordered after their source inputs",
            )
        )

    status = "blocked" if any(c["status"] == "blocked" for c in checks) else (
        "needs_work" if any(c["status"] == "needs_work" for c in checks) else "pass"
    )
    emit(out_path, status, checks, root, receipts)


def emit(
    out_path: Path | None,
    status: str,
    checks: list[dict],
    root: Path,
    receipts: dict | None = None,
) -> None:
    result = {
        "status": status,
        "workRoot": str(root),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "inputs": receipts or {},
        "checks": checks,
        "summary": {
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "needs_work": sum(1 for c in checks if c["status"] == "needs_work"),
            "blocked": sum(1 for c in checks if c["status"] == "blocked"),
        },
        "contract": (
            "Run this before completion_gate.py. A needs_work result may still "
            "produce a prototype verdict, but it must be reported up front; "
            "a blocked result means evidence is missing or invalid."
        ),
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if status == "pass" else 2 if status == "blocked" else 1)


if __name__ == "__main__":
    main()
