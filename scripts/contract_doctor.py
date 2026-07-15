#!/usr/bin/env python3
"""Validate the mockup-to-code contract before CSS or completion QA.

This is intentionally stdlib-only. It catches the small shape mistakes that
otherwise surface much later as tracebacks in box_diff/artifact_check, then
reuses asset_preflight's real photo policy instead of creating a weaker copy.

Usage:
  python3 contract_doctor.py WORK_ROOT [--phase pre-css|completion]
      [--manifest WORK_ROOT/manifest.json]
      [--scores WORK_ROOT/reports/section-scores.json]
      [--out WORK_ROOT/reports/contract-doctor.json]

Exit codes: 0 pass, 1 needs_work, 2 blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asset_preflight import evaluate_asset_policy


VALID_MODES = {"pixel-clone", "production", "hybrid"}
VALID_PRIORITIES = {"critical", "high", "normal", "low"}
COMP_BBOX_SOURCES = {"snap_bbox", "profile", "normalized", "user"}
GLOBAL_SCOPES = {"viewport-fixed", "viewport-edge"}
DETAIL_PRIORITIES = {"critical", "high", "normal", "low"}
TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
MOTION_PROPERTIES = {"opacity", "transform", "stroke-dashoffset"}
ASSET_INDEPENDENT_BEHAVIORS = {
    "motion", "responsiveRecompose", "reuse", "interaction", "contentUpdate", "layering"
}


def finding(status: str, cid: str, message: str, **extra: Any) -> dict:
    row = {"id": cid, "status": status, "message": message}
    row.update(extra)
    return row


def read_json(path: Path, label: str, checks: list[dict]) -> Any | None:
    if not path.is_file():
        checks.append(finding("blocked", f"missing-{label}", f"missing required file: {path}"))
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(finding("blocked", f"unreadable-{label}", f"unreadable {label}: {path}: {exc}"))
        return None


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_bbox(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(("x", "y", "w", "h")) <= set(value)
        and all(finite_number(value[key]) for key in ("x", "y", "w", "h"))
        and value["w"] > 0
        and value["h"] > 0
    )


def validate_manifest_shape(manifest: Any, checks: list[dict]) -> bool:
    if not isinstance(manifest, dict):
        checks.append(finding("blocked", "manifest-object", "manifest root must be a JSON object"))
        return False

    missing = [key for key in ("viewport", "image", "photoLed", "elements") if key not in manifest]
    if missing:
        checks.append(
            finding("blocked", "manifest-required-fields", f"manifest missing required fields: {', '.join(missing)}")
        )

    mode = manifest.get("mode", "hybrid")
    if mode not in VALID_MODES:
        checks.append(finding("blocked", "manifest-mode", f"invalid mode: {mode!r}"))

    viewport = manifest.get("viewport")
    if not isinstance(viewport, dict) or not finite_number(viewport.get("width")) or viewport["width"] <= 0:
        checks.append(finding("blocked", "manifest-viewport", "viewport must be an object with positive numeric width"))

    if not nonempty_string(manifest.get("image")):
        checks.append(finding("blocked", "manifest-image", "image must be a non-empty normalized mockup path"))
    if not isinstance(manifest.get("photoLed"), bool):
        checks.append(finding("blocked", "manifest-photo-led", "photoLed must be explicitly true or false"))

    elements = manifest.get("elements")
    if not isinstance(elements, list):
        checks.append(finding("blocked", "manifest-elements-array", "elements must be a JSON array"))
        return False

    malformed_rows = [index for index, row in enumerate(elements) if not isinstance(row, dict)]
    if malformed_rows:
        checks.append(
            finding("blocked", "manifest-element-objects", "every elements row must be an object", indexes=malformed_rows)
        )
        return False

    invalid_identity = [
        row.get("id") or f"index:{index}"
        for index, row in enumerate(elements)
        if not nonempty_string(row.get("id")) or not nonempty_string(row.get("el"))
    ]
    if invalid_identity:
        checks.append(
            finding("blocked", "manifest-element-identity", "every element needs non-empty id and el strings", elements=invalid_identity)
        )

    ids = [row.get("id") for row in elements if nonempty_string(row.get("id"))]
    els = [row.get("el") for row in elements if nonempty_string(row.get("el"))]
    duplicate_ids = sorted({value for value in ids if ids.count(value) > 1})
    duplicate_els = sorted({value for value in els if els.count(value) > 1})
    if duplicate_ids or duplicate_els:
        checks.append(
            finding(
                "blocked",
                "manifest-element-duplicates",
                "element id and el values must be unique",
                duplicateIds=duplicate_ids,
                duplicateEls=duplicate_els,
            )
        )

    invalid_bboxes = [
        {
            "id": row.get("id") or f"index:{index}",
            "actualType": type(row.get("bbox")).__name__,
            "value": row.get("bbox"),
        }
        for index, row in enumerate(elements)
        if not valid_bbox(row.get("bbox"))
    ]
    if invalid_bboxes:
        checks.append(
            finding(
                "blocked",
                "manifest-bbox-object",
                "bbox must be an object {x,y,w,h} with finite numbers and positive w/h; arrays are invalid",
                elements=invalid_bboxes,
            )
        )

    invalid_priorities = [
        row.get("id") or f"index:{index}"
        for index, row in enumerate(elements)
        if row.get("priority") not in VALID_PRIORITIES
    ]
    if invalid_priorities:
        checks.append(
            finding("blocked", "manifest-priority", "every element needs a valid priority", elements=invalid_priorities)
        )

    return not any(row["status"] == "blocked" for row in checks)


def validate_measurement_contract(manifest: dict, checks: list[dict]) -> None:
    bad = []
    for element in manifest.get("elements", []):
        if element.get("qaPriority") not in ("fv-critical", "section-critical"):
            continue
        if element.get("bboxSource") not in COMP_BBOX_SOURCES:
            bad.append({"id": element.get("id"), "field": "bboxSource", "value": element.get("bboxSource")})
        if not isinstance(element.get("measurementRef"), dict) or not element["measurementRef"]:
            bad.append({"id": element.get("id"), "field": "measurementRef", "value": element.get("measurementRef")})
    if bad:
        checks.append(
            finding(
                "blocked",
                "critical-measurement-contract",
                "FV/section-critical elements need comp-side bboxSource and measurementRef before CSS",
                elements=bad,
            )
        )


def validate_global_ownership(manifest: dict, checks: list[dict]) -> None:
    invalid = []
    for element in manifest.get("elements", []):
        positioning = element.get("positioning", "flow")
        scope = element.get("placementScope")
        is_global_position = positioning in ("fixed", "sticky")
        is_global_scope = scope in GLOBAL_SCOPES
        reasons = []
        if is_global_position and not is_global_scope:
            reasons.append("fixed/sticky requires placementScope viewport-fixed or viewport-edge")
        if is_global_scope and positioning not in ("fixed", "sticky"):
            reasons.append("viewport-global scope requires positioning fixed or sticky")
        if is_global_scope or is_global_position:
            if not nonempty_string(element.get("anchorTarget")):
                reasons.append("anchorTarget missing")
            if not nonempty_string(element.get("responsiveBehavior")):
                reasons.append("responsiveBehavior missing")
        if reasons:
            invalid.append({"id": element.get("id"), "reasons": reasons})
    if invalid:
        checks.append(
            finding(
                "blocked",
                "viewport-global-ownership",
                "global chrome must be contracted as viewport-owned before section-relative box diff",
                elements=invalid,
            )
        )


def validate_fv_text_lines(manifest: dict, checks: list[dict]) -> None:
    invalid = []
    for element in manifest.get("elements", []):
        text = element.get("text") or {}
        structural = nonempty_string(text.get("content")) and element.get("mediaClass") != "lettering-decal"
        if element.get("qaPriority") != "fv-critical" or not structural:
            continue
        type_spec = element.get("typeSpec") or {}
        expected = type_spec.get("expectedVisualLineCount")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            invalid.append({"id": element.get("id"), "field": "expectedVisualLineCount"})
        elif expected >= 2 and element.get("role") == "heading":
            geometry = type_spec.get("posterGeometry")
            reasons = []
            if not isinstance(geometry, dict):
                reasons.append("posterGeometry missing")
            else:
                line_boxes = geometry.get("sourceLineBBoxes")
                if not isinstance(line_boxes, list) or len(line_boxes) != expected:
                    reasons.append(f"sourceLineBBoxes must contain {expected} measured lines")
                elif not all(
                    isinstance(row, dict)
                    and nonempty_string(row.get("lineId"))
                    and isinstance(row.get("bbox"), dict)
                    and all(isinstance(row["bbox"].get(key), (int, float)) for key in ("x", "y", "w", "h"))
                    and row["bbox"].get("w", 0) > 0
                    and row["bbox"].get("h", 0) > 0
                    for row in line_boxes
                ):
                    reasons.append("sourceLineBBoxes need lineId and positive measured bbox objects")
                for field in ("sourceBlockHeightRatio", "sourceLineAdvanceRatio"):
                    value = geometry.get(field)
                    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                        reasons.append(f"{field} must be a positive source measurement")
                if not isinstance(geometry.get("sourceInterlineGapPx"), (int, float)):
                    reasons.append("sourceInterlineGapPx must be measured")
                if not nonempty_string(geometry.get("evidencePath")):
                    reasons.append("posterGeometry evidencePath missing")
            if reasons:
                invalid.append({"id": element.get("id"), "field": "posterGeometry", "reasons": reasons})
        script_runs = type_spec.get("scriptRuns")
        expected_runs = type_spec.get("expectedRunCount")
        if script_runs is not None:
            if not isinstance(script_runs, list) or not all(nonempty_string(row) for row in script_runs):
                invalid.append({"id": element.get("id"), "field": "scriptRuns"})
            elif not isinstance(expected_runs, int) or expected_runs != len(script_runs):
                invalid.append(
                    {
                        "id": element.get("id"),
                        "field": "expectedRunCount",
                        "expected": len(script_runs),
                        "actual": expected_runs,
                    }
                )
    if invalid:
        checks.append(
            finding(
                "blocked",
                "fv-text-line-contract",
                "FV structural text needs line/run counts; multi-line poster headings also need measured posterGeometry so compressed line advance cannot pass",
                elements=invalid,
            )
        )


def validate_typography_impression(manifest: dict, checks: list[dict]) -> None:
    """Freeze the source's scale and air, not merely a font category name."""
    section_frames = {
        row.get("path")
        for row in manifest.get("referenceImages", [])
        if isinstance(row, dict) and row.get("use") == "section-comp"
    }
    if manifest.get("mode", "hybrid") != "hybrid" or len(section_frames) < 2:
        return
    headings = [
        row
        for row in manifest.get("elements", [])
        if row.get("role") == "heading"
        and row.get("qaPriority") in ("fv-critical", "section-critical")
        and nonempty_string((row.get("text") or {}).get("content"))
    ]
    invalid = []
    ratio_fields = (
        "sourceBlockWidthRatio",
        "sourceBlockHeightRatio",
        "sourceMaxLineWidthRatio",
        "sourceGlyphHeightRatio",
        "sourceLineAdvanceRatio",
        "sourceInkDensity",
        "viewportMaxSizeRatio",
    )
    for row in headings:
        profile = (row.get("typeSpec") or {}).get("sourceImpression")
        reasons = []
        if not isinstance(profile, dict):
            reasons.append("typeSpec.sourceImpression missing")
        else:
            for field in ("sourceFrameWidth", "sourceFrameHeight"):
                if not finite_number(profile.get(field)) or profile[field] <= 0:
                    reasons.append(f"{field} must be a positive source measurement")
            for field in ratio_fields:
                value = profile.get(field)
                if not finite_number(value) or value <= 0:
                    reasons.append(f"{field} must be a positive source ratio")
            tracking = profile.get("sourceTrackingEm")
            if not finite_number(tracking):
                reasons.append("sourceTrackingEm must be measured, including zero")
            bounds = profile.get("implementationScaleBounds")
            if not isinstance(bounds, dict) or not all(
                finite_number(bounds.get(field)) and bounds[field] > 0
                for field in ("desktopMaxSizePx", "mobileMinSizePx")
            ):
                reasons.append("implementationScaleBounds needs desktopMaxSizePx and mobileMinSizePx")
            jump = profile.get("jumpRatios")
            if not isinstance(jump, dict) or not all(
                finite_number(jump.get(field)) and jump[field] > 0
                for field in ("toLead", "toBody", "toLabel")
            ):
                reasons.append("jumpRatios must measure heading-to-lead/body/label")
            if not nonempty_string(profile.get("evidencePath")):
                reasons.append("sourceImpression evidencePath missing")
            frame_width = profile.get("sourceFrameWidth")
            frame_height = profile.get("sourceFrameHeight")
            bbox = row.get("bbox") or {}
            if finite_number(frame_width) and frame_width > 0 and valid_bbox(bbox):
                observed = bbox["w"] / frame_width
                declared = profile.get("sourceBlockWidthRatio")
                if finite_number(declared) and abs(observed - declared) > 0.08:
                    reasons.append("sourceBlockWidthRatio disagrees with the measured bbox")
            if finite_number(frame_height) and frame_height > 0 and valid_bbox(bbox):
                observed = bbox["h"] / frame_height
                declared = profile.get("sourceBlockHeightRatio")
                if finite_number(declared) and abs(observed - declared) > 0.08:
                    reasons.append("sourceBlockHeightRatio disagrees with the measured bbox")
        if reasons:
            invalid.append({"id": row.get("id"), "reasons": reasons})
    if invalid:
        checks.append(
            finding(
                "blocked",
                "typography-source-impression",
                (
                    "every section-critical heading needs measured source scale, tracking, "
                    "line advance, ink density, jump ratios, and responsive scale bounds"
                ),
                elements=invalid,
            )
        )

    signatures: dict[str, list[dict]] = {}
    for row in headings:
        spec = row.get("typeSpec") or {}
        profile = spec.get("sourceImpression") or {}
        bbox = row.get("bbox") or {}
        signature_payload = {
            "bbox": [bbox.get(key) for key in ("x", "y", "w", "h")],
            "weightClass": spec.get("weightClass"),
            "tracking": spec.get("tracking"),
            "leading": spec.get("leading"),
            "profile": {key: profile.get(key) for key in ratio_fields + ("sourceTrackingEm",)},
        }
        signature = json.dumps(signature_payload, sort_keys=True, ensure_ascii=False)
        signatures.setdefault(signature, []).append(row)
    repeated = []
    for rows in signatures.values():
        sources = {row.get("sourceImage") for row in rows if nonempty_string(row.get("sourceImage"))}
        if len(rows) >= 3 and len(sources) >= 3 and not all(
            nonempty_string(((row.get("typeSpec") or {}).get("sharedSystemEvidence")))
            for row in rows
        ):
            repeated.append(
                {
                    "elementIds": [row.get("id") for row in rows],
                    "sourceImages": sorted(sources),
                }
            )
    if repeated:
        checks.append(
            finding(
                "blocked",
                "typography-template-copy-risk",
                (
                    "three or more distinct source frames reuse one identical heading geometry/spec; "
                    "measure each comp or bind explicit sharedSystemEvidence"
                ),
                groups=repeated,
            )
        )


def validate_detail_inventory(manifest: dict, checks: list[dict]) -> None:
    references = manifest.get("referenceImages", [])
    section_comps = [
        row.get("section") for row in references
        if isinstance(row, dict) and row.get("use") == "section-comp" and nonempty_string(row.get("section"))
    ]
    if manifest.get("mode", "hybrid") != "hybrid" or len(section_comps) < 2:
        return

    inventory = manifest.get("detailInventory")
    if not isinstance(inventory, list) or not inventory:
        checks.append(
            finding(
                "blocked",
                "detail-inventory-required",
                "hybrid multi-frame work requires a non-empty detailInventory before CSS",
            )
        )
        return
    if any(not isinstance(row, dict) for row in inventory):
        checks.append(finding("blocked", "detail-inventory-rows", "detailInventory rows must be objects"))
        return

    element_rows = [row for row in manifest.get("elements", []) if isinstance(row, dict)]
    elements_by_id = {row.get("id"): row for row in element_rows if nonempty_string(row.get("id"))}
    element_ids = set(elements_by_id)
    seen: set[str] = set()
    invalid = []
    for index, row in enumerate(inventory):
        reasons = []
        inventory_id = row.get("id")
        if not nonempty_string(inventory_id):
            reasons.append("id missing")
        elif inventory_id in seen:
            reasons.append("duplicate id")
        else:
            seen.add(inventory_id)
        if row.get("section") not in section_comps:
            reasons.append("section is not a registered section-comp")
        if not nonempty_string(row.get("description")):
            reasons.append("description missing")
        if not isinstance(row.get("sourceSpecific"), bool):
            reasons.append("sourceSpecific must be boolean")
        if row.get("sourceSpecific") is True:
            craft = row.get("renderingCraft")
            if not isinstance(craft, dict):
                reasons.append("sourceSpecific device requires renderingCraft")
            else:
                if not nonempty_string(craft.get("medium")):
                    reasons.append("renderingCraft.medium missing")
                traits = craft.get("signatureTraits")
                if (
                    not isinstance(traits, list)
                    or len(traits) < 2
                    or any(not nonempty_string(value) for value in traits)
                ):
                    reasons.append("renderingCraft.signatureTraits needs at least two source-observed traits")
                atomic_parts = craft.get("minimumAtomicParts")
                if (
                    not isinstance(atomic_parts, int)
                    or isinstance(atomic_parts, bool)
                    or atomic_parts < 1
                ):
                    reasons.append("renderingCraft.minimumAtomicParts must be a positive integer")
                observed_parts = craft.get("atomicParts")
                if (
                    not isinstance(observed_parts, list)
                    or not observed_parts
                    or any(not nonempty_string(value) for value in observed_parts)
                ):
                    reasons.append("renderingCraft.atomicParts must name the observed internal craft")
                if craft.get("genericStandInsForbidden") is not True:
                    reasons.append("renderingCraft.genericStandInsForbidden must be true")
                if not nonempty_string(craft.get("evidencePath")):
                    reasons.append("renderingCraft.evidencePath missing")
        if row.get("priority") not in DETAIL_PRIORITIES:
            reasons.append("invalid priority")
        bound = row.get("manifestElementIds")
        evidence_mode = row.get("evidenceMode")
        if not isinstance(bound, list) or any(not nonempty_string(value) for value in bound):
            reasons.append("manifestElementIds must be a string array")
        elif bound:
            unknown = sorted(set(bound) - element_ids)
            if unknown:
                reasons.append(f"unknown manifestElementIds: {', '.join(unknown)}")
        elif evidence_mode != "crop-only":
            reasons.append("empty manifestElementIds requires evidenceMode=crop-only")
        craft = row.get("renderingCraft")
        grouped_artwork_plate = False
        if isinstance(bound, list):
            grouped_artwork_plate = any(
                isinstance(elements_by_id.get(element_id, {}).get("assetUnit"), dict)
                and elements_by_id[element_id]["assetUnit"].get("kind") == "card_artwork_plate"
                and elements_by_id[element_id]["assetUnit"].get("splitPolicy") == "keep-together"
                for element_id in bound
                if element_id in elements_by_id
            )
        observed_parts = craft.get("atomicParts") if isinstance(craft, dict) else None
        grouped_plate_preserves_parts = (
            grouped_artwork_plate
            and isinstance(observed_parts, list)
            and len(observed_parts) >= craft.get("minimumAtomicParts", 0)
        )
        if (
            row.get("sourceSpecific") is True
            and isinstance(craft, dict)
            and isinstance(bound, list)
            and evidence_mode != "crop-only"
            and isinstance(craft.get("minimumAtomicParts"), int)
            and not isinstance(craft.get("minimumAtomicParts"), bool)
            and len(bound) < craft["minimumAtomicParts"]
            and not grouped_plate_preserves_parts
        ):
            reasons.append(
                f"manifestElementIds has {len(bound)} rows but renderingCraft.minimumAtomicParts requires {craft['minimumAtomicParts']}; use separate rows only for independent behavior, or bind one card_artwork_plate with enough atomicParts"
            )
        if reasons:
            invalid.append({"index": index, "id": inventory_id, "reasons": reasons})

    missing_sections = sorted(set(section_comps) - {row.get("section") for row in inventory})
    if missing_sections:
        invalid.append({"id": None, "reasons": ["sections without inventory: " + ", ".join(missing_sections)]})
    if invalid:
        checks.append(
            finding(
                "blocked",
                "detail-inventory-contract",
                "detailInventory must cover every section, bind each source device, and freeze source-specific rendering craft before CSS",
                rows=invalid,
            )
        )


def validate_asset_units(manifest: dict, checks: list[dict]) -> None:
    """Require semantic evidence for splitting a coherent card artwork into rasters."""
    elements = [row for row in manifest.get("elements", []) if isinstance(row, dict)]
    malformed = []

    def behavior_state(unit: dict) -> tuple[bool, bool]:
        behavior = unit.get("independentBehavior")
        valid = (
            isinstance(behavior, dict)
            and set(behavior) == ASSET_INDEPENDENT_BEHAVIORS
            and all(isinstance(behavior.get(key), bool) for key in ASSET_INDEPENDENT_BEHAVIORS)
        )
        return valid, bool(valid and any(behavior.values()))

    for row in elements:
        unit = row.get("assetUnit")
        if unit is None:
            continue
        reasons = []
        if not isinstance(unit, dict):
            malformed.append({"id": row.get("id"), "reasons": ["assetUnit must be an object"]})
            continue
        kind = unit.get("kind")
        split_policy = unit.get("splitPolicy")
        members = unit.get("members")
        valid_behavior, has_independent_behavior = behavior_state(unit)
        if kind not in {
            "full_field_scene_plate", "clean_background_plate", "transparent_foreground",
            "transparent_scene", "card_artwork_plate", "atomic_raster", "code_native",
        }:
            reasons.append("assetUnit.kind invalid")
        if split_policy not in {"keep-together", "separate"}:
            reasons.append("assetUnit.splitPolicy invalid")
        if not isinstance(members, list) or not members or any(not nonempty_string(value) for value in members):
            reasons.append("assetUnit.members must be a non-empty string array")
        if not valid_behavior:
            reasons.append("assetUnit.independentBehavior must declare all six boolean behaviors")
        if not nonempty_string(unit.get("sourceEvidencePath")):
            reasons.append("assetUnit.sourceEvidencePath missing")
        if split_policy == "separate":
            split_evidence = unit.get("splitEvidence")
            if not has_independent_behavior:
                reasons.append("separate asset requires at least one true independent behavior")
            if not isinstance(split_evidence, list) or not split_evidence or any(
                not nonempty_string(value) for value in split_evidence
            ):
                reasons.append("separate asset requires concrete splitEvidence")
        if split_policy == "keep-together" and not nonempty_string(unit.get("keepTogetherReason")):
            reasons.append("keep-together asset requires keepTogetherReason")
        if kind == "card_artwork_plate":
            if split_policy != "keep-together":
                reasons.append("card_artwork_plate must use splitPolicy=keep-together")
            if isinstance(members, list) and len(members) < 2:
                reasons.append("card_artwork_plate must name at least two coupled members")
            if has_independent_behavior:
                reasons.append("card_artwork_plate cannot claim independently behaving members")
        if kind == "transparent_scene":
            if split_policy != "keep-together":
                reasons.append("transparent_scene must use splitPolicy=keep-together")
            if isinstance(members, list) and len(members) < 2:
                reasons.append("transparent_scene must name at least two coupled members")
            if has_independent_behavior:
                reasons.append("transparent_scene cannot claim independently behaving members")
        if kind == "full_field_scene_plate":
            if split_policy != "keep-together":
                reasons.append("full_field_scene_plate must use splitPolicy=keep-together")
            if has_independent_behavior:
                reasons.append("full_field_scene_plate cannot claim independently behaving members")
            if not (row.get("copySpace") or nonempty_string(row.get("copySpaceNotRequiredReason"))):
                reasons.append("full_field_scene_plate requires copySpace or copySpaceNotRequiredReason")
        if (
            row.get("qaPriority") in ("fv-critical", "section-critical")
            and row.get("mediaClass") in ("photo", "illustration")
        ):
            if not isinstance(row.get("assetSurfaceContract"), dict):
                reasons.append("critical raster assetUnit requires assetSurfaceContract")
            if not isinstance(row.get("surfaceIntegration"), dict):
                reasons.append("critical raster assetUnit requires surfaceIntegration")
        if reasons:
            malformed.append({"id": row.get("id"), "reasons": reasons})

    if malformed:
        checks.append(finding(
            "blocked",
            "asset-unit-contract",
            "assetUnit must describe one valid semantic generation boundary",
            rows=malformed,
        ))

    groups: dict[str, list[dict]] = {}
    for row in elements:
        if (
            row.get("qaPriority") in ("fv-critical", "section-critical")
            and row.get("mediaClass") in ("photo", "illustration")
            and row.get("visualRole") in ("contained-photo", "object-detail")
            and nonempty_string(row.get("clipOwner"))
        ):
            groups.setdefault(row["clipOwner"], []).append(row)

    risks = []
    for clip_owner, rows in groups.items():
        if len(rows) < 2:
            continue
        unexplained = []
        for row in rows:
            unit = row.get("assetUnit")
            if not isinstance(unit, dict):
                unexplained.append(row.get("id"))
                continue
            valid_behavior, has_independent_behavior = behavior_state(unit)
            split_evidence = unit.get("splitEvidence")
            if not (
                unit.get("splitPolicy") == "separate"
                and valid_behavior
                and has_independent_behavior
                and isinstance(split_evidence, list)
                and split_evidence
                and all(nonempty_string(value) for value in split_evidence)
            ):
                unexplained.append(row.get("id"))
        if unexplained:
            risks.append({
                "clipOwner": clip_owner,
                "rasterElementIds": [row.get("id") for row in rows],
                "unexplained": unexplained,
            })
    if risks:
        checks.append(finding(
            "needs_work",
            "asset-overdecomposition-risk",
            "same-card critical rasters were split without independent-behavior evidence; prefer one card_artwork_plate",
            groups=risks,
        ))


def validate_review_policy(manifest: dict, checks: list[dict]) -> None:
    references = manifest.get("referenceImages", [])
    section_count = sum(
        1 for row in references
        if isinstance(row, dict) and row.get("use") == "section-comp" and row.get("section")
    )
    if manifest.get("mode", "hybrid") != "hybrid" or section_count < 2:
        return
    policy = manifest.get("reviewPolicy")
    if not isinstance(policy, dict):
        checks.append(finding("blocked", "review-policy-required", "hybrid multi-frame work requires reviewPolicy"))
        return
    reasons = []
    if policy.get("independentReviewRequired") is not True:
        reasons.append("independentReviewRequired must be true")
    max_ratio = policy.get("maxAdaptedSourceSpecificRatio")
    if not finite_number(max_ratio) or not 0 <= max_ratio <= 1:
        reasons.append("maxAdaptedSourceSpecificRatio must be between 0 and 1")
    max_delta = policy.get("maxIndependentScoreDelta")
    if not finite_number(max_delta) or max_delta < 0:
        reasons.append("maxIndependentScoreDelta must be non-negative")
    min_foreground = policy.get("minForegroundPixelCoverage")
    if not finite_number(min_foreground) or not 0 <= min_foreground <= 1:
        reasons.append("minForegroundPixelCoverage must be between 0 and 1")
    if policy.get("exactPromptProvenanceRequired") is not True:
        reasons.append("exactPromptProvenanceRequired must be true")
    if policy.get("photoGeometryRequired") is not True:
        reasons.append("photoGeometryRequired must be true")
    if reasons:
        checks.append(finding("blocked", "review-policy-contract", "invalid reviewPolicy", reasons=reasons))


def validate_motion_contract(manifest: dict, root: Path, checks: list[dict]) -> None:
    motion = manifest.get("motion")
    if motion is None:
        return
    if not isinstance(motion, dict) or not isinstance(motion.get("required"), bool):
        checks.append(finding("blocked", "motion-contract", "motion.required must be boolean"))
        return
    if motion.get("required") is not True:
        return
    reasons = []
    source = motion.get("sourceRef") or {}
    if not nonempty_string(source.get("path")) or not nonempty_string(source.get("quote")):
        reasons.append("sourceRef.path and verbatim sourceRef.quote are required")
    else:
        source_path = resolve_evidence_path(root, source.get("path"))
        if source_path is None or not source_path.is_file():
            reasons.append("motion sourceRef.path evidence is missing")
        else:
            try:
                source_text = source_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                reasons.append("motion sourceRef.path must be readable UTF-8 text")
            else:
                if source.get("quote") not in source_text:
                    reasons.append("motion sourceRef.quote is not verbatim text from sourceRef.path")
    if motion.get("visualQaState") != "settled":
        reasons.append("visualQaState must be settled so motion cannot hide static fidelity gaps")
    motifs = motion.get("motifs")
    element_ids = {row.get("id") for row in manifest.get("elements", []) if nonempty_string(row.get("id"))}
    if not isinstance(motifs, list) or not 1 <= len(motifs) <= 2:
        reasons.append("motifs must contain one or two reusable motion motifs")
    else:
        all_targets = []
        for motif in motifs:
            if not isinstance(motif, dict):
                reasons.append("every motion motif must be an object")
                continue
            targets = motif.get("targets")
            if not isinstance(targets, list) or not targets or any(target not in element_ids for target in targets):
                reasons.append(f"motif {motif.get('id')} targets must reference manifest element ids")
                continue
            all_targets.extend(targets)
            props = motif.get("properties")
            if not isinstance(props, list) or not props or any(prop not in MOTION_PROPERTIES for prop in props):
                reasons.append(f"motif {motif.get('id')} uses layout-affecting or unsupported properties")
            if not finite_number(motif.get("durationMs")) or motif.get("durationMs") <= 0:
                reasons.append(f"motif {motif.get('id')} durationMs must be positive")
            if not nonempty_string(motif.get("easing")) or not nonempty_string(motif.get("meaning")):
                reasons.append(f"motif {motif.get('id')} needs easing and comprehension meaning")
        if len(set(all_targets)) > 8:
            reasons.append("motion QA is limited to eight high-value manifest targets")
    reduced = motion.get("reducedMotion") or {}
    if reduced.get("strategy") != "settled-static" or reduced.get("contentVisibleWithoutJs") is not True:
        reasons.append("reducedMotion must expose settled static content with JavaScript disabled")
    if reasons:
        checks.append(finding(
            "blocked",
            "motion-contract",
            "source-requested motion needs a bounded plan before implementation",
            reasons=reasons,
        ))


def resolve_evidence_path(root: Path, value: Any) -> Path | None:
    if not nonempty_string(value):
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_receipt(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return {"path": str(path), "sha256": sha256_file(path), "size": path.stat().st_size}


def validate_template_residue(root: Path, phase: str, checks: list[dict]) -> None:
    required = [
        ("hypotheses", root / "reports" / "hypotheses.md", TEMPLATES / "hypotheses.md"),
        ("photo-asset-review", root / "reports" / "photo-asset-review.md", TEMPLATES / "photo-asset-review.md"),
    ]
    if phase == "completion":
        required.extend([
            ("section-review", root / "reports" / "section-review.md", TEMPLATES / "section-review.md"),
            ("section-scores", root / "reports" / "section-scores.json", TEMPLATES / "section-scores.min.json"),
        ])
    invalid = []
    for label, path, starter in required:
        if not path.is_file():
            invalid.append({"artifact": label, "reason": "required artifact missing", "path": str(path)})
        elif starter.is_file() and sha256_file(path) == sha256_file(starter):
            invalid.append({"artifact": label, "reason": "starter template is still unedited", "path": str(path)})
    if invalid:
        checks.append(finding(
            "blocked",
            "starter-template-residue",
            "required evidence must be authored for this run, not an untouched starter",
            artifacts=invalid,
        ))


def validate_pre_css_order(root: Path, prior_report: dict | None, checks: list[dict]) -> None:
    prior_receipt = ((prior_report or {}).get("inputs") or {}).get("manifest")
    prior_valid = (
        (prior_report or {}).get("status") == "pass"
        and isinstance(prior_receipt, dict)
        and isinstance(prior_receipt.get("sha256"), str)
        and isinstance(prior_receipt.get("size"), int)
        and isinstance((prior_report or {}).get("generatedAt"), str)
    )
    implementation_paths = []
    site = root / "site"
    if site.is_dir():
        for path in site.rglob("*"):
            if path.is_file() and path.stat().st_size > 0 and path.suffix.lower() in {".html", ".css", ".js", ".mjs", ".jsx", ".tsx"}:
                implementation_paths.append(path)
    for path in (
        root / "reports" / "rects.json",
        root / "reports" / "rendered.png",
    ):
        if path.is_file() and path.stat().st_size > 0:
            implementation_paths.append(path)
    fv_tune = root / "reports" / "fv-tune"
    if fv_tune.is_dir():
        implementation_paths.extend(path for path in fv_tune.glob("*.png") if path.stat().st_size > 0)
    if not implementation_paths:
        return
    # A previous hash-bound pass proves that implementation did not begin
    # before the first pre-CSS gate.  Later asset or topology revisions must be
    # able to re-enter the gate without deleting/touching valid site files.
    # Freshness against the *current* manifest is checked by downstream receipt
    # matching; file mtimes are not a safe revision protocol.
    if prior_valid:
        return
    if implementation_paths:
        checks.append(finding(
            "blocked",
            "implementation-before-pre-css",
            "implementation/render evidence exists before a hash-bound pre-CSS pass",
            files=sorted(str(path) for path in implementation_paths),
        ))


def validate_generation_provenance(manifest: dict, root: Path, checks: list[dict]) -> None:
    if (manifest.get("reviewPolicy") or {}).get("exactPromptProvenanceRequired") is not True:
        return
    invalid = []
    for row in manifest.get("elements", []):
        if row.get("assetStrategy") != "generated" or row.get("qaPriority") not in ("fv-critical", "section-critical"):
            continue
        generated = row.get("generatedAsset") or {}
        reasons = []
        prompt_ref = generated.get("promptRef")
        prompt_path = None
        if not isinstance(prompt_ref, dict) or prompt_ref.get("kind") != "exact-prompt":
            reasons.append("promptRef exact-prompt object missing")
        else:
            prompt_path = resolve_evidence_path(root, prompt_ref.get("path"))
            if prompt_path is None or not prompt_path.is_file():
                reasons.append("exact prompt file missing")
            else:
                actual_sha = sha256_file(prompt_path)
                if prompt_ref.get("sha256") != actual_sha:
                    reasons.append("promptRef sha256 does not match exact prompt file")
                try:
                    prompt_text = prompt_path.read_text(encoding="utf-8").strip()
                except (OSError, UnicodeDecodeError):
                    reasons.append("exact prompt file is not readable UTF-8 text")
                else:
                    if prompt_text != str(generated.get("prompt", "")).strip():
                        reasons.append("generatedAsset.prompt must equal the exact prompt file, not a summary")

        asset_path = resolve_evidence_path(root, generated.get("workspacePath"))
        if (
            prompt_path is not None
            and prompt_path.is_file()
            and asset_path is not None
            and asset_path.is_file()
            and prompt_path.stat().st_mtime_ns > asset_path.stat().st_mtime_ns
        ):
            reasons.append(
                "exact prompt file is newer than the adopted generated asset; "
                "create and hash the prompt receipt before invoking the generator"
            )
        receipt_ref = generated.get("generationReceipt")
        if not isinstance(receipt_ref, dict):
            reasons.append("generationReceipt is missing")
        else:
            receipt_path = resolve_evidence_path(root, receipt_ref.get("path"))
            if receipt_path is None or not receipt_path.is_file():
                reasons.append("generationReceipt file missing")
            elif receipt_ref.get("sha256") != sha256_file(receipt_path):
                reasons.append("generationReceipt sha256 mismatch")
            else:
                try:
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    reasons.append("generationReceipt is unreadable JSON")
                else:
                    receipt_prompt = receipt.get("prompt") or {}
                    receipt_asset = receipt.get("asset") or {}
                    if receipt.get("schemaVersion") != "prompt-generation-receipt/v1" or receipt.get("status") != "adopted":
                        reasons.append("generationReceipt must be adopted prompt-generation-receipt/v1")
                    if prompt_path is not None and prompt_path.is_file() and receipt_prompt.get("sha256") != sha256_file(prompt_path):
                        reasons.append("generationReceipt prompt hash mismatch")
                    if asset_path is not None and asset_path.is_file() and receipt_asset.get("sha256") != sha256_file(asset_path):
                        reasons.append("generationReceipt asset hash mismatch")

        input_refs = generated.get("inputRefs")
        if not isinstance(input_refs, list) or not input_refs:
            reasons.append("inputRefs must state which references were actually sent to the generator")
        else:
            referenced_paths = set()
            for ref in input_refs:
                if not isinstance(ref, dict) or not isinstance(ref.get("includedInGeneration"), bool):
                    reasons.append("every inputRef needs includedInGeneration boolean")
                    continue
                ref_path = resolve_evidence_path(root, ref.get("path"))
                if ref_path is None or not ref_path.is_file():
                    reasons.append(f"inputRef missing: {ref.get('path')}")
                    continue
                referenced_paths.add(str(ref.get("path")))
                if ref.get("sha256") != sha256_file(ref_path):
                    reasons.append(f"inputRef sha256 mismatch: {ref.get('path')}")
                if ref.get("role") not in ("composition-reference", "style-reference", "edit-target", "supporting-input"):
                    reasons.append(f"inputRef role invalid: {ref.get('path')}")
            if generated.get("sourceImage") not in referenced_paths:
                reasons.append("generatedAsset.sourceImage must appear in inputRefs")
        if reasons:
            invalid.append({"id": row.get("id"), "reasons": reasons})
    if invalid:
        checks.append(
            finding(
                "blocked",
                "generated-prompt-provenance",
                "generated assets require hash-bound exact prompts and unambiguous input-reference roles",
                elements=invalid,
            )
        )


def contains_japanese(text: str) -> bool:
    return any(
        "\u3040" <= char <= "\u30ff" or "\u3400" <= char <= "\u9fff"
        for char in text
    )


def validate_typography_specialist_report(
    manifest: dict, root: Path, phase: str, checks: list[dict]
) -> None:
    japanese_critical = [
        row.get("id")
        for row in manifest.get("elements", [])
        if row.get("qaPriority") in ("fv-critical", "section-critical")
        and isinstance((row.get("text") or {}).get("content"), str)
        and contains_japanese(row["text"]["content"])
    ]
    if not japanese_critical:
        return
    typography = (manifest.get("specialistReports") or {}).get("typography")
    reasons = []
    report = None
    if not isinstance(typography, dict) or typography.get("contract") != "typography-report/v1":
        reasons.append("specialistReports.typography contract typography-report/v1 missing")
    else:
        path = resolve_evidence_path(root, typography.get("path"))
        if path is None or not path.is_file():
            reasons.append("typography report file missing")
        else:
            if typography.get("sha256") != sha256_file(path):
                reasons.append("typography report sha256 mismatch")
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                reasons.append("typography report is unreadable JSON")
    if isinstance(report, dict):
        if report.get("schemaVersion") != "typography-report/v1":
            reasons.append("typography report schemaVersion mismatch")
        targets = [row for row in report.get("targets", []) if isinstance(row, dict)]
        target_ids = {row.get("id") for row in targets}
        missing_targets = sorted(set(japanese_critical) - target_ids)
        if missing_targets:
            reasons.append("typography report missing critical targets: " + ", ".join(missing_targets))
        manifest_by_id = {
            row.get("id"): row for row in manifest.get("elements", []) if isinstance(row, dict)
        }
        for target in report.get("targets", []) or []:
            if not isinstance(target, dict):
                reasons.append("typography report target must be an object")
                continue
            if "expectedLineCount" in target:
                reasons.append(f"target {target.get('id')} uses deprecated expectedLineCount")
            if not isinstance(target.get("expectedRunCount"), int):
                reasons.append(f"target {target.get('id')} expectedRunCount missing")
            runs = target.get("runs")
            if not isinstance(runs, list) or target.get("expectedRunCount") != len(runs):
                reasons.append(f"target {target.get('id')} run ledger count mismatch")
            else:
                for run in runs:
                    run_path = resolve_evidence_path(root, (run or {}).get("evidencePath")) if isinstance(run, dict) else None
                    if run_path is None or not run_path.is_file() or run_path.stat().st_size == 0:
                        reasons.append(f"target {target.get('id')} run evidence missing")
                        break
            source = target.get("sourceReference") or {}
            source_count = source.get("expectedVisualLineCount")
            manifest_row = manifest_by_id.get(target.get("id")) or {}
            manifest_type_spec = manifest_row.get("typeSpec") or {}
            manifest_count = manifest_type_spec.get("expectedVisualLineCount")
            if not isinstance(source_count, int) or source_count != manifest_count:
                reasons.append(
                    f"target {target.get('id')} sourceReference line count does not match manifest"
                )
            for field in ("sourceImagePath", "cropPath"):
                evidence = resolve_evidence_path(root, source.get(field))
                if evidence is None or not evidence.is_file() or evidence.stat().st_size == 0:
                    reasons.append(f"target {target.get('id')} sourceReference.{field} evidence missing")
            expectations = target.get("expectations") or []
            if not isinstance(expectations, list) or not expectations or any(
                not isinstance(expectation, dict)
                or not isinstance(expectation.get("expectedVisualLineCount"), int)
                for expectation in expectations
            ):
                reasons.append(f"target {target.get('id')} expectedVisualLineCount evidence missing")
            if manifest_row.get("role") == "heading":
                if target.get("sourceImpressionRef") != "manifest:typeSpec.sourceImpression":
                    reasons.append(f"target {target.get('id')} sourceImpressionRef missing")
                tolerances = target.get("impressionTolerances") or {}
                tolerance_fields = (
                    "blockWidthRatio",
                    "blockHeightRatio",
                    "maxLineWidthRatio",
                    "glyphHeightRatio",
                    "trackingEm",
                    "lineAdvanceRatio",
                    "inkDensity",
                    "jumpRatio",
                )
                if not all(
                    finite_number(tolerances.get(field)) and tolerances[field] >= 0
                    for field in tolerance_fields
                ):
                    reasons.append(f"target {target.get('id')} impressionTolerances incomplete")
        if phase == "completion":
            required_states = set((report.get("gate") or {}).get("requiredStateIds") or [])
            states = {
                row.get("id"): row for row in report.get("states", []) if isinstance(row, dict)
            }
            for state_id in required_states:
                state = states.get(state_id) or {}
                browser = str(state.get("browser") or "")
                if state.get("status") != "pass" or not browser or "replace" in browser.lower():
                    reasons.append(f"typography state {state_id} is not a measured browser pass")
                for field in ("screenshotPath", "measurementArtifactPath"):
                    evidence = resolve_evidence_path(root, state.get(field))
                    if evidence is None or not evidence.is_file() or evidence.stat().st_size == 0:
                        reasons.append(f"typography state {state_id} {field} missing")
                measurement = resolve_evidence_path(root, state.get("measurementArtifactPath"))
                if measurement is not None and measurement.is_file() and state.get("measurementArtifactSha256") != sha256_file(measurement):
                    reasons.append(f"typography state {state_id} measurement hash mismatch")
                target_id = state.get("targetId")
                manifest_row = manifest_by_id.get(target_id) or {}
                if manifest_row.get("role") == "heading":
                    target = next((row for row in targets if row.get("id") == target_id), {})
                    source_profile = ((manifest_row.get("typeSpec") or {}).get("sourceImpression") or {})
                    actual = state.get("impressionMetrics") or {}
                    tolerances = target.get("impressionTolerances") or {}
                    pairs = (
                        ("sourceBlockWidthRatio", "blockWidthRatio"),
                        ("sourceBlockHeightRatio", "blockHeightRatio"),
                        ("sourceMaxLineWidthRatio", "maxLineWidthRatio"),
                        ("sourceGlyphHeightRatio", "glyphHeightRatio"),
                        ("sourceTrackingEm", "trackingEm"),
                        ("sourceLineAdvanceRatio", "lineAdvanceRatio"),
                        ("sourceInkDensity", "inkDensity"),
                    )
                    for source_field, actual_field in pairs:
                        source_value = source_profile.get(source_field)
                        actual_value = actual.get(actual_field)
                        tolerance = tolerances.get(actual_field)
                        if not finite_number(actual_value):
                            reasons.append(f"typography state {state_id} {actual_field} missing")
                        elif finite_number(source_value) and finite_number(tolerance) and abs(actual_value - source_value) > tolerance:
                            reasons.append(f"typography state {state_id} {actual_field} exceeds source tolerance")
                    source_jump = source_profile.get("jumpRatios") or {}
                    actual_jump = actual.get("jumpRatios") or {}
                    jump_tolerance = tolerances.get("jumpRatio")
                    for field in ("toLead", "toBody", "toLabel"):
                        if not finite_number(actual_jump.get(field)):
                            reasons.append(f"typography state {state_id} jumpRatios.{field} missing")
                        elif finite_number(source_jump.get(field)) and finite_number(jump_tolerance) and abs(actual_jump[field] - source_jump[field]) > jump_tolerance:
                            reasons.append(f"typography state {state_id} jumpRatios.{field} exceeds source tolerance")
            gate = report.get("gate") or {}
            independent = report.get("independentReview") or {}
            if gate.get("status") != "pass":
                reasons.append("typography report gate must pass at completion")
            if independent.get("status") != "passed" or independent.get("relationToProducer") != "independent":
                reasons.append("typography report needs independent review at completion")
    if reasons:
        checks.append(
            finding(
                "blocked",
                "typography-specialist-report",
                "Japanese critical typography must carry a hash-bound typography-report/v1",
                elements=japanese_critical,
                reasons=reasons,
            )
        )


def validate_specialist_reports(
    manifest: dict, root: Path, phase: str, checks: list[dict]
) -> None:
    """Validate conditionally required cross-skill reports and their receipts."""
    production = manifest.get("productionReadiness") or {}
    if not isinstance(production, dict):
        checks.append(
            finding(
                "blocked",
                "production-readiness-contract",
                "productionReadiness must be an object when present",
            )
        )
        production = {}
    else:
        invalid_flags = [
            key
            for key in ("mediaDeliveryRequired", "interactionQaRequired")
            if key in production and not isinstance(production.get(key), bool)
        ]
        if invalid_flags:
            checks.append(
                finding(
                    "blocked",
                    "production-readiness-contract",
                    "production readiness flags must be boolean",
                    fields=invalid_flags,
                )
            )

    section_frames = [
        row
        for row in manifest.get("referenceImages", [])
        if isinstance(row, dict) and row.get("use") == "section-comp"
    ]
    hybrid_multiframe = manifest.get("mode", "hybrid") == "hybrid" and len(section_frames) >= 2
    generated_critical_photo = any(
        isinstance(row, dict)
        and row.get("mediaClass") in ("photo", "illustration")
        and row.get("assetStrategy") in ("generated", "replace")
        and row.get("qaPriority") in ("fv-critical", "section-critical")
        for row in manifest.get("elements", [])
    )
    continuity_seams = [
        row
        for row in ((manifest.get("pageComposition") or {}).get("seams") or [])
        if isinstance(row, dict)
        and isinstance(row.get("continuity"), dict)
        and row["continuity"].get("required") is True
    ]

    required: list[tuple[str, str, str]] = []
    if hybrid_multiframe:
        required.append(("deviceInventory", "detail-inventory/v1", "complete"))
        if generated_critical_photo:
            required.append(("photoArtDirection", "photo-art-direction/v1", "adopted"))
        if continuity_seams:
            required.append((
                "seamContinuity",
                "seam-continuity/v1",
                "pass" if phase == "completion" else "ready",
            ))
    if phase == "completion" and production.get("mediaDeliveryRequired") is True:
        required.append(("mediaDelivery", "media-delivery-report/v1", "pass"))
    if phase == "completion" and production.get("interactionQaRequired") is True:
        required.append(("interaction", "interaction-report/v1", "pass"))

    bound = manifest.get("specialistReports") or {}
    for key, contract, required_state in required:
        reasons: list[str] = []
        receipt = bound.get(key) if isinstance(bound, dict) else None
        report = None
        path = None
        if not isinstance(receipt, dict) or receipt.get("contract") != contract:
            reasons.append(f"specialistReports.{key} contract {contract} missing")
        else:
            path = resolve_evidence_path(root, receipt.get("path"))
            if path is None or not path.is_file():
                reasons.append("report file missing")
            else:
                if receipt.get("sha256") != sha256_file(path):
                    reasons.append("report sha256 mismatch")
                try:
                    report = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    reasons.append("report is unreadable JSON")
        if isinstance(report, dict):
            if report.get("schemaVersion") != contract:
                reasons.append("report schemaVersion mismatch")
            actual_state = report.get("status")
            if isinstance(actual_state, dict):
                actual_state = actual_state.get("state")
            if actual_state != required_state:
                reasons.append(
                    f"report status must be {required_state!r} for {phase}, got {actual_state!r}"
                )
            if key == "deviceInventory":
                report_ids = {
                    row.get("id")
                    for row in report.get("devices", [])
                    if isinstance(row, dict) and nonempty_string(row.get("id"))
                }
                manifest_ids = {
                    row.get("id")
                    for row in manifest.get("detailInventory", [])
                    if isinstance(row, dict) and nonempty_string(row.get("id"))
                }
                if report_ids != manifest_ids:
                    reasons.append(
                        "device report ids must exactly match manifest detailInventory ids"
                    )
            if key == "seamContinuity":
                expected_pairs = {
                    (row.get("from"), row.get("to")) for row in continuity_seams
                }
                report_pairs = {
                    (row.get("from"), row.get("to"))
                    for row in report.get("seams", [])
                    if isinstance(row, dict)
                }
                if report_pairs != expected_pairs:
                    reasons.append(
                        "seam continuity report pairs must exactly match required manifest seams"
                    )
            if key == "interaction" and path is not None:
                manifest_path = path.parent / "interaction-manifest.json"
                run_receipt_path = path.parent / "interaction-receipt.json"
                try:
                    run_receipt = json.loads(run_receipt_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    reasons.append("interaction receipt is missing or unreadable")
                else:
                    if run_receipt.get("schemaVersion") != "interaction-receipt/v1":
                        reasons.append("interaction receipt schemaVersion mismatch")
                    if not manifest_path.is_file():
                        reasons.append("interaction manifest is missing")
                    else:
                        manifest_sha = sha256_file(manifest_path)
                        if ((run_receipt.get("manifest") or {}).get("sha256") != manifest_sha):
                            reasons.append("interaction receipt manifest sha256 mismatch")
                        if report.get("manifest_sha256") != manifest_sha:
                            reasons.append("interaction report manifest_sha256 mismatch")
                    if ((run_receipt.get("report") or {}).get("sha256") != sha256_file(path)):
                        reasons.append("interaction receipt report sha256 mismatch")
                    specialist = run_receipt.get("specialistReport") or {}
                    if specialist.get("contract") != contract:
                        reasons.append("interaction receipt specialistReport contract mismatch")
                    if specialist.get("path") != receipt.get("path"):
                        reasons.append("interaction receipt specialistReport path mismatch")
                    if specialist.get("sha256") != receipt.get("sha256"):
                        reasons.append("interaction receipt specialistReport sha256 mismatch")
        if reasons:
            checks.append(
                finding(
                    "blocked",
                    f"specialist-report:{key}",
                    f"required {contract} specialist evidence is missing, stale, or non-passing",
                    reasons=reasons,
                )
            )


def validate_semantic_photo_separation(manifest: dict, checks: list[dict]) -> None:
    inventory = manifest.get("detailInventory") or []
    elements_by_id = {
        row.get("id"): row for row in manifest.get("elements", []) if nonempty_string(row.get("id"))
    }
    grouped: dict[str, list[dict]] = {}
    for row in inventory:
        if not isinstance(row, dict) or row.get("kind") != "photo" or row.get("sourceSpecific") is not True:
            continue
        bound = row.get("manifestElementIds") or []
        if len(bound) == 1:
            grouped.setdefault(bound[0], []).append(row)

    invalid = []
    for element_id, rows in grouped.items():
        if len(rows) < 2:
            continue
        element = elements_by_id.get(element_id) or {}
        multi_zone = element.get("multiZoneAsset")
        zones = multi_zone.get("zones") if isinstance(multi_zone, dict) else None
        reasons = []
        if not isinstance(zones, list):
            reasons.append("multiple source photo devices collapsed into one element without multiZoneAsset.zones")
        else:
            asset_width = multi_zone.get("assetWidth")
            asset_height = multi_zone.get("assetHeight")
            if not finite_number(asset_width) or asset_width <= 0 or not finite_number(asset_height) or asset_height <= 0:
                reasons.append("multiZoneAsset needs positive assetWidth and assetHeight")
            expected_ids = {row.get("id") for row in rows}
            actual_ids = {zone.get("inventoryId") for zone in zones if isinstance(zone, dict)}
            if actual_ids != expected_ids:
                reasons.append("zones must cover exactly the bound photo inventory ids")
            roi_values = []
            for zone in zones:
                if not isinstance(zone, dict):
                    reasons.append("zone must be an object")
                    continue
                if not valid_bbox(zone.get("cropRoi")):
                    reasons.append(f"zone {zone.get('inventoryId')} needs cropRoi {{x,y,w,h}}")
                else:
                    roi = tuple(zone["cropRoi"][key] for key in ("x", "y", "w", "h"))
                    roi_values.append(roi)
                    x, y, w, h = roi
                    if finite_number(asset_width) and finite_number(asset_height) and (
                        x < 0 or y < 0 or x + w > asset_width or y + h > asset_height
                    ):
                        reasons.append(f"zone {zone.get('inventoryId')} cropRoi exceeds asset bounds")
                if not nonempty_string(zone.get("subjectSignature")):
                    reasons.append(f"zone {zone.get('inventoryId')} needs subjectSignature")
                if not nonempty_string(zone.get("usedBy")) or zone.get("usedBy") not in elements_by_id:
                    reasons.append(f"zone {zone.get('inventoryId')} usedBy must name an existing manifest element id")
                if not nonempty_string(zone.get("pairPath")):
                    reasons.append(f"zone {zone.get('inventoryId')} needs pairPath")
                if zone.get("pairKind") != "consumer-integration":
                    reasons.append(f"zone {zone.get('inventoryId')} pairKind must be consumer-integration")
            if len(roi_values) != len(set(roi_values)):
                reasons.append("multi-zone crops must not reuse identical ROIs")
            for index, first in enumerate(roi_values):
                ax, ay, aw, ah = first
                for second in roi_values[index + 1:]:
                    bx, by, bw, bh = second
                    overlap_w = max(0, min(ax + aw, bx + bw) - max(ax, bx))
                    overlap_h = max(0, min(ay + ah, by + bh) - max(ay, by))
                    overlap = overlap_w * overlap_h
                    smaller = min(aw * ah, bw * bh)
                    if smaller > 0 and overlap / smaller > 0.25:
                        reasons.append("multi-zone crop overlap exceeds 25% of the smaller zone")
                        break
        if reasons:
            invalid.append({"elementId": element_id, "inventoryIds": [row.get("id") for row in rows], "reasons": reasons})
    if invalid:
        checks.append(
            finding(
                "blocked",
                "semantic-photo-separation",
                "distinct source photo stories need distinct media rows or evidenced non-identical multi-zone crops",
                elements=invalid,
            )
        )


def rects_intersect(a: dict, b: dict) -> bool:
    return (
        min(a["x"] + a["w"], b["x"] + b["w"]) > max(a["x"], b["x"])
        and min(a["y"] + a["h"], b["y"] + b["h"]) > max(a["y"], b["y"])
    )


def validate_photo_geometry(manifest: dict, checks: list[dict]) -> None:
    if (manifest.get("reviewPolicy") or {}).get("photoGeometryRequired") is not True:
        return
    viewport = manifest.get("viewport") or {}
    width, height = viewport.get("width"), viewport.get("height")
    if not finite_number(width) or not finite_number(height):
        return
    element_ids = {row.get("id") for row in manifest.get("elements", []) if nonempty_string(row.get("id"))}
    invalid = []
    for row in manifest.get("elements", []):
        if not (
            row.get("qaPriority") == "fv-critical"
            and row.get("mediaClass") in ("photo", "illustration")
            and row.get("assetStrategy") in ("generated", "replace")
            and row.get("photoCompositionMode") == "full-frame-plate"
        ):
            continue
        reasons = []
        copy_spaces = row.get("copySpace")
        subjects = row.get("subjectZones")
        focals = row.get("responsiveFocalPoints")
        if not isinstance(copy_spaces, list) or not copy_spaces:
            reasons.append("copySpace must be a non-empty array")
            copy_spaces = []
        if not isinstance(subjects, list) or not subjects:
            reasons.append("subjectZones must be a non-empty array")
            subjects = []
        if not isinstance(focals, list):
            reasons.append("responsiveFocalPoints must be an array")
            focals = []
        focal_widths = {item.get("viewportWidth") for item in focals if isinstance(item, dict)}
        for required_width in (390, int(width)):
            if required_width not in focal_widths:
                reasons.append(f"responsiveFocalPoints missing viewportWidth {required_width}")

        valid_copy = []
        for item in copy_spaces:
            if not isinstance(item, dict) or item.get("for") not in element_ids or not valid_bbox(item.get("roi")):
                reasons.append("copySpace needs existing for id and roi {x,y,w,h}")
                continue
            if not finite_number(item.get("minClearance")) or item.get("minClearance") < 0:
                reasons.append(f"copySpace {item.get('for')} needs non-negative minClearance")
            roi = item["roi"]
            if roi["x"] < 0 or roi["y"] < 0 or roi["x"] + roi["w"] > width or roi["y"] + roi["h"] > height:
                reasons.append(f"copySpace {item.get('for')} exceeds canonical FV bounds")
            valid_copy.append(item)
        valid_subjects = []
        for item in subjects:
            if not isinstance(item, dict) or not nonempty_string(item.get("id")) or not valid_bbox(item.get("roi")):
                reasons.append("subjectZone needs id and roi {x,y,w,h}")
                continue
            roi = item["roi"]
            if roi["x"] < 0 or roi["y"] < 0 or roi["x"] + roi["w"] > width or roi["y"] + roi["h"] > height:
                reasons.append(f"subjectZone {item.get('id')} exceeds canonical FV bounds")
            valid_subjects.append(item)
        for copy in valid_copy:
            for subject in valid_subjects:
                if rects_intersect(copy["roi"], subject["roi"]):
                    reasons.append(
                        f"copySpace {copy.get('for')} intersects subjectZone {subject.get('id')}"
                    )
        if reasons:
            invalid.append({"id": row.get("id"), "reasons": reasons})
    if invalid:
        checks.append(
            finding(
                "blocked",
                "photo-geometry-contract",
                "full-frame generated/replaced FV photos need measurable copy space, subject zones, and responsive focal points",
                elements=invalid,
            )
        )


def validate_pixel_foreground_contract(manifest: dict, checks: list[dict]) -> None:
    if manifest.get("mode", "hybrid") != "hybrid":
        return
    viewport = manifest.get("viewport") or {}
    width, height = viewport.get("width"), viewport.get("height")
    if not finite_number(width) or not finite_number(height):
        return
    primary = manifest.get("image")
    full_generated = []
    foreground_candidates = []
    foreground_rows = []
    invalid_candidates = []
    surface_roles = {"button", "nav", "ui", "card", "badge"}
    surface_layers = {"cta", "header-nav", "foreground-card", "accent-band", "photo-overlay-gradient"}
    for row in manifest.get("elements", []):
        bbox = row.get("bbox")
        if not valid_bbox(bbox) or row.get("qaPriority") != "fv-critical":
            continue
        primary_row = not row.get("sourceImage") or not primary or row.get("sourceImage") == primary
        if not primary_row:
            continue
        if (
            row.get("mediaClass") in ("photo", "illustration")
            and row.get("assetStrategy") in ("generated", "replace")
            and bbox["x"] <= 0 and bbox["y"] <= 0
            and bbox["x"] + bbox["w"] >= width
            and bbox["y"] + bbox["h"] >= height
        ):
            full_generated.append(row.get("id"))
        elif (
            row.get("role") in surface_roles
            or row.get("layerRole") in surface_layers
            or row.get("pixelDiffForeground") is True
            or row.get("pixelDiffForegroundExclusion") is not None
        ):
            foreground_candidates.append(row.get("id"))
            if row.get("pixelDiffForeground") is True:
                if nonempty_string((row.get("text") or {}).get("content")):
                    invalid_candidates.append(
                        {"id": row.get("id"), "reason": "split opaque shell and structural text into separate manifest rows"}
                    )
                if not nonempty_string(row.get("pixelDiffForegroundReason")):
                    invalid_candidates.append({"id": row.get("id"), "reason": "pixelDiffForegroundReason missing"})
                foreground_rows.append(row.get("id"))
            else:
                exclusion = row.get("pixelDiffForegroundExclusion")
                if not isinstance(exclusion, dict) or not nonempty_string(exclusion.get("reason")) or not nonempty_string(exclusion.get("pairPath")):
                    invalid_candidates.append(
                        {"id": row.get("id"), "reason": "declare pixelDiffForeground or reason+pairPath exclusion"}
                    )
    if full_generated and (invalid_candidates or (foreground_candidates and not foreground_rows)):
        checks.append(
            finding(
                "blocked",
                "pixel-foreground-contract",
                "every full-frame-generated FV surface candidate must be compared or explicitly excluded, with at least one opaque carve-out when candidates exist",
                generatedMedia=full_generated,
                candidates=foreground_candidates,
                invalid=invalid_candidates,
            )
        )


def validate_surface_decoration_and_line_contracts(
    manifest: dict, root: Path, checks: list[dict]
) -> None:
    """Guard integration failures that generic responsive QA cannot see."""
    elements = [row for row in manifest.get("elements", []) if isinstance(row, dict)]
    by_id = {row.get("id"): row for row in elements if isinstance(row.get("id"), str)}
    japanese = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")

    for row in elements:
        row_id = row.get("id", "<unknown>")
        critical = row.get("qaPriority") in ("fv-critical", "section-critical")
        if (
            critical
            and row.get("mediaClass") in ("photo", "illustration")
            and row.get("visualRole") in ("contained-photo", "object-detail")
        ):
            if not isinstance(row.get("assetUnit"), dict):
                checks.append(finding(
                    "blocked", "asset-unit-missing",
                    f"critical card/contained visual '{row_id}' lacks assetUnit; semantic raster ownership is ambiguous",
                    elementId=row_id,
                ))
            surface = row.get("assetSurfaceContract")
            if not isinstance(surface, dict):
                checks.append(finding(
                    "blocked", "asset-surface-contract-missing",
                    f"critical card/contained visual '{row_id}' lacks assetSurfaceContract; raster and CSS frame ownership is ambiguous",
                    elementId=row_id,
                ))
            else:
                consumers = surface.get("consumerIds") or []
                missing_consumers = [value for value in consumers if value not in by_id]
                if missing_consumers:
                    checks.append(finding(
                        "blocked", "asset-surface-consumer-missing",
                        f"assetSurfaceContract for '{row_id}' names missing consumers",
                        elementId=row_id, missing=missing_consumers,
                    ))
                if surface.get("consumerOwnsFrame") is True and surface.get("assetMustNotContainPanel") is not True:
                    checks.append(finding(
                        "blocked", "asset-surface-double-frame-risk",
                        f"'{row_id}' lets CSS own the frame but does not forbid a baked-in raster panel/card",
                        elementId=row_id,
                    ))
                if surface.get("consumerOwnsBackground") is True and surface.get("assetMustNotContainPadding") is not True:
                    checks.append(finding(
                        "blocked", "asset-surface-double-padding-risk",
                        f"'{row_id}' lets CSS own the background but does not forbid raster padding/color-field margins",
                        elementId=row_id,
                    ))
                review_path = resolve_evidence_path(root, surface.get("reviewPath"))
                if review_path is None or not review_path.is_file() or review_path.stat().st_size == 0:
                    checks.append(finding(
                        "blocked", "asset-surface-review-missing",
                        f"'{row_id}' lacks readable isolated-asset and crop-in-use surface review",
                        elementId=row_id,
                    ))

        craft = row.get("decorativeCraft")
        if isinstance(craft, dict):
            primitive = craft.get("geometryPrimitive")
            if primitive == "circle-arc" and not isinstance(craft.get("circleArcGeometry"), dict):
                checks.append(finding(
                    "blocked", "circle-arc-geometry-missing",
                    f"decorative element '{row_id}' declares a circle arc without diameter/center/visible-arc geometry",
                    elementId=row_id,
                ))
            if primitive == "ellipse":
                exception = craft.get("ellipseException")
                if not isinstance(exception, dict) or exception.get("sourceEvidenced") is not True:
                    checks.append(finding(
                        "blocked", "unevidenced-large-ellipse",
                        f"decorative element '{row_id}' uses an ellipse without source evidence; use a measured bezier or off-canvas true-circle arc",
                        elementId=row_id,
                    ))

        for target_id in row.get("mustStayBehind") or []:
            target = by_id.get(target_id)
            if target is None:
                checks.append(finding(
                    "blocked", "must-stay-behind-target-missing",
                    f"'{row_id}' mustStayBehind target '{target_id}' is missing", elementId=row_id,
                ))
                continue
            if not isinstance(row.get("zLayer"), int) or not isinstance(target.get("zLayer"), int):
                checks.append(finding(
                    "blocked", "must-stay-behind-zlayer-missing",
                    f"'{row_id}' and '{target_id}' need integer zLayer values to prove decorative stacking",
                    elementId=row_id,
                ))
            elif row["zLayer"] >= target["zLayer"]:
                checks.append(finding(
                    "blocked", "must-stay-behind-order",
                    f"'{row_id}' zLayer must be lower than '{target_id}'", elementId=row_id,
                ))

        text = ((row.get("text") or {}).get("content") or "")
        if critical and row.get("role") == "heading" and japanese.search(text):
            contracts = ((row.get("typeSpec") or {}).get("responsiveLineContracts"))
            if not isinstance(contracts, list) or not contracts:
                checks.append(finding(
                    "needs_work", "japanese-responsive-line-contract-missing",
                    f"critical Japanese heading '{row_id}' lacks viewport-specific expected line strings and forbidden orphan fragments",
                    elementId=row_id,
                ))


def validate_multiframe_contract(manifest: dict, root: Path, checks: list[dict]) -> None:
    references = manifest.get("referenceImages", [])
    if not isinstance(references, list):
        checks.append(finding("blocked", "reference-images-array", "referenceImages must be an array"))
        return
    if any(not isinstance(row, dict) for row in references):
        checks.append(finding("blocked", "reference-image-objects", "every referenceImages row must be an object"))
        return

    frame_rows = [row for row in references if row.get("use") == "section-comp"]
    frame_paths = {row.get("path") for row in frame_rows if nonempty_string(row.get("path"))}
    unknown_sources = sorted(
        {
            row.get("sourceImage")
            for row in manifest.get("elements", [])
            if row.get("sourceImage") and row.get("sourceImage") not in frame_paths
        }
    )
    if unknown_sources:
        checks.append(
            finding("blocked", "element-source-image", "element sourceImage must name a registered section-comp path", paths=unknown_sources)
        )

    if len(frame_rows) < 2:
        return
    page = manifest.get("pageComposition")
    if not isinstance(page, dict):
        checks.append(finding("blocked", "page-composition-object", "multi-frame manifest requires pageComposition object"))
        return
    sections = page.get("sections")
    seams = page.get("seams")
    if not isinstance(sections, list) or any(not isinstance(row, dict) for row in sections):
        checks.append(finding("blocked", "page-composition-sections", "pageComposition.sections must be an array of objects"))
        return
    if not isinstance(seams, list) or any(not isinstance(row, dict) for row in seams):
        checks.append(finding("blocked", "page-composition-seams", "pageComposition.seams must be an array of objects"))
        return

    frame_sections = [row.get("section") for row in frame_rows]
    contracted_sections = [row.get("section") for row in sections]
    if frame_sections != contracted_sections:
        checks.append(
            finding(
                "blocked",
                "page-composition-section-order",
                "pageComposition.sections must match section-comp order exactly",
                expected=frame_sections,
                actual=contracted_sections,
            )
        )
    expected_seams = list(zip(frame_sections, frame_sections[1:]))
    actual_seams = [(row.get("from"), row.get("to")) for row in seams]
    if expected_seams != actual_seams:
        checks.append(
            finding(
                "blocked",
                "page-composition-seam-order",
                "pageComposition.seams must cover every adjacent section pair in order",
                expected=expected_seams,
                actual=actual_seams,
            )
        )

    element_ids = {
        row.get("id")
        for row in manifest.get("elements", [])
        if isinstance(row, dict) and nonempty_string(row.get("id"))
    }
    required_layers = {"target-surface", "incoming-preview"}
    connective_layers = {"outgoing-environment", "connective-motif"}
    for seam in seams:
        continuity = seam.get("continuity")
        if continuity is None:
            continue
        pair = f"{seam.get('from')}->{seam.get('to')}"
        reasons: list[str] = []
        if not isinstance(continuity, dict) or not isinstance(continuity.get("required"), bool):
            checks.append(finding(
                "blocked",
                "seam-continuity-contract",
                f"seam '{pair}' continuity.required must be boolean",
            ))
            continue
        if continuity.get("required") is not True:
            continue

        source = continuity.get("sourceRef") or {}
        if not nonempty_string(source.get("path")) or not nonempty_string(source.get("quote")):
            reasons.append("sourceRef.path and verbatim sourceRef.quote are required")
        else:
            source_path = resolve_evidence_path(root, source.get("path"))
            if source_path is None or not source_path.is_file():
                reasons.append("sourceRef.path evidence is missing")
            else:
                try:
                    source_text = source_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    reasons.append("sourceRef.path must be readable UTF-8 text")
                else:
                    if source.get("quote") not in source_text:
                        reasons.append("sourceRef.quote is not verbatim text from sourceRef.path")

        if continuity.get("surfaceOwner") not in ("to-section", "shared"):
            reasons.append("surfaceOwner must be to-section or shared")
        if continuity.get("geometryPrimitive") not in ("bezier", "circle-arc", "freeform-path"):
            reasons.append("geometryPrimitive must be bezier, circle-arc, or freeform-path")
        layers = continuity.get("layers")
        layer_set = set(layers) if isinstance(layers, list) else set()
        if len(layer_set) < 3 or not required_layers.issubset(layer_set) or not layer_set.intersection(connective_layers):
            reasons.append(
                "layers need target-surface + incoming-preview + outgoing-environment or connective-motif"
            )
        preview_targets = continuity.get("previewTargets")
        if not isinstance(preview_targets, list) or not preview_targets:
            reasons.append("previewTargets must contain at least one manifest element id")
        elif any(target not in element_ids for target in preview_targets):
            reasons.append("previewTargets must reference manifest element ids")
        cue_target = continuity.get("cueTarget")
        if cue_target is not None and cue_target not in element_ids:
            reasons.append("cueTarget must reference a manifest element id")
        for field in ("desktopEvidencePath", "mobileEvidencePath", "colorSampleReport"):
            if not nonempty_string(continuity.get(field)):
                reasons.append(f"{field} planned evidence path is required")

        if reasons:
            checks.append(finding(
                "blocked",
                "seam-continuity-contract",
                f"seam '{pair}' needs a bounded art-directed continuity plan before CSS",
                seam=pair,
                reasons=reasons,
            ))


def validate_scores_shape(scores: Any, checks: list[dict]) -> None:
    if not isinstance(scores, dict):
        checks.append(finding("blocked", "section-scores-object", "section-scores root must be a JSON object"))
        return
    sections = scores.get("sections")
    if not isinstance(sections, list):
        checks.append(
            finding(
                "blocked",
                "section-scores-sections-array",
                "section-scores.sections must be an array, not an object/dict",
                actualType=type(sections).__name__,
            )
        )
        return
    invalid_sections = [
        index
        for index, row in enumerate(sections)
        if not isinstance(row, dict) or not isinstance(row.get("axes"), dict) or not row.get("axes")
    ]
    if invalid_sections:
        checks.append(
            finding("blocked", "section-score-rows", "each section score needs an object row with non-empty axes", indexes=invalid_sections)
        )
    page = scores.get("page")
    if not isinstance(page, dict) or not (page.get("score") is not None or isinstance(page.get("axes"), dict)):
        checks.append(finding("blocked", "section-scores-page", "section-scores.page needs score or axes"))
    dispositions = scores.get("dispositions")
    if not isinstance(dispositions, list) or any(not isinstance(row, dict) for row in dispositions):
        checks.append(finding("blocked", "section-scores-dispositions", "section-scores.dispositions must be an array of objects"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("work_root")
    ap.add_argument("--phase", choices=("pre-css", "completion"), default="pre-css")
    ap.add_argument("--manifest")
    ap.add_argument("--scores")
    ap.add_argument("--out")
    args = ap.parse_args()

    root = Path(args.work_root)
    manifest_path = Path(args.manifest) if args.manifest else root / "manifest.json"
    scores_path = Path(args.scores) if args.scores else root / "reports" / "section-scores.json"
    out_path = Path(args.out) if args.out else root / "reports" / "contract-doctor.json"
    prior_report = None
    if out_path.is_file():
        try:
            candidate = json.loads(out_path.read_text(encoding="utf-8"))
            prior_report = candidate if isinstance(candidate, dict) else None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            prior_report = None
    checks: list[dict] = []
    asset_implementation_allowed = False

    manifest = read_json(manifest_path, "manifest", checks)
    shape_ok = validate_manifest_shape(manifest, checks) if manifest is not None else False
    if shape_ok:
        validate_template_residue(root, args.phase, checks)
        if args.phase == "pre-css":
            validate_pre_css_order(root, prior_report, checks)
        validate_measurement_contract(manifest, checks)
        validate_global_ownership(manifest, checks)
        validate_fv_text_lines(manifest, checks)
        validate_typography_impression(manifest, checks)
        validate_multiframe_contract(manifest, root, checks)
        validate_detail_inventory(manifest, checks)
        validate_asset_units(manifest, checks)
        validate_review_policy(manifest, checks)
        validate_motion_contract(manifest, root, checks)
        validate_generation_provenance(manifest, root, checks)
        validate_typography_specialist_report(manifest, root, args.phase, checks)
        validate_specialist_reports(manifest, root, args.phase, checks)
        validate_semantic_photo_separation(manifest, checks)
        validate_photo_geometry(manifest, checks)
        validate_pixel_foreground_contract(manifest, checks)
        validate_surface_decoration_and_line_contracts(manifest, root, checks)
        try:
            asset = evaluate_asset_policy(manifest, root)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            checks.append(
                finding("blocked", "asset-policy-input-shape", f"asset policy could not read the manifest contract: {exc}")
            )
        else:
            asset_implementation_allowed = bool(asset.get("implementationAllowed"))
            failures = [row for row in asset.get("checks", []) if row.get("status") != "pass"]
            if failures:
                for row in failures:
                    checks.append(
                        finding(
                            row.get("status", "blocked"),
                            f"asset:{row.get('id', 'policy')}",
                            row.get("message", "asset policy failed"),
                            elementId=row.get("elementId"),
                        )
                    )
            else:
                checks.append(finding("pass", "asset-policy", "photo/illustration decisions pass the real pre-CSS asset policy"))

    if args.phase == "completion":
        scores = read_json(scores_path, "section-scores", checks)
        if scores is not None:
            validate_scores_shape(scores, checks)

    if not checks:
        checks.append(finding("pass", "contract", "contract is valid"))
    elif not any(row["status"] != "pass" for row in checks):
        checks.append(finding("pass", "contract-shape", "manifest and artifact shapes are valid"))

    status = "blocked" if any(row["status"] == "blocked" for row in checks) else (
        "needs_work" if any(row["status"] == "needs_work" for row in checks) else "pass"
    )
    result = {
        "status": status,
        "phase": args.phase,
        "workRoot": str(root),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "inputs": {"manifest": file_receipt(manifest_path)},
        "implementationAllowed": (
            args.phase == "pre-css" and status != "blocked" and asset_implementation_allowed
        ),
        "completionQaAllowed": args.phase == "completion" and status == "pass",
        "checks": checks,
        "summary": {
            "pass": sum(row["status"] == "pass" for row in checks),
            "needs_work": sum(row["status"] == "needs_work" for row in checks),
            "blocked": sum(row["status"] == "blocked" for row in checks),
        },
        "contract": (
            "Run pre-css until implementationAllowed is true before writing section CSS (pass normally; needs_work only for an earned placeholder). Run completion after section-scores exist, "
            "then continue to artifact_check.py and completion_gate.py; this doctor never lowers those gates."
        ),
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if status == "pass" else 2 if status == "blocked" else 1)


if __name__ == "__main__":
    main()
