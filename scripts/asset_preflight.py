#!/usr/bin/env python3
"""Block invalid photo/illustration asset decisions before CSS is written.

The contamination checker can only judge the pixels inside an adopted crop.
It cannot tell whether the crop escaped baked-in foreground matter by throwing
away the composition the comp actually specified. This preflight evaluates the
manifest decision instead: source-frame overlap, visual role, composition
preservation, generation attempts, and on-disk evidence.

Usage:
  python3 asset_preflight.py MANIFEST [--work-root WORK_ROOT] [--out REPORT]

Exit codes:
  0 pass, 1 needs_work (earned placeholder), 2 blocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zlib
from pathlib import Path

from surface_pixels import (
    inspect_png_surface,
    inspect_protected_color_retention,
    parse_hex_color,
    rgb_distance,
)


PHOTO_CLASSES = {"photo", "illustration"}
CRITICAL_PRIORITIES = {"fv-critical", "section-critical"}
RASTER_STRATEGIES = {"crop-asset", "generated", "replace", "placeholder"}
SURFACE_MODES = {
    "alpha_floating",
    "opaque_full_bleed",
    "opaque_masked_merge",
    "opaque_tone_matched",
    "intentional_frame",
}
SOURCE_TOPOLOGIES = {
    "section_field",
    "floating_scene",
    "contained_artwork",
    "tone_merged_object",
    "source_visible_frame",
}
EDGE_POLICIES = {"alpha", "bleed", "mask", "tone_match", "source_frame", "not_visible"}
TOPOLOGY_MODES = {
    "section_field": {"opaque_full_bleed", "opaque_masked_merge"},
    "floating_scene": {"alpha_floating"},
    "contained_artwork": {
        "alpha_floating",
        "opaque_full_bleed",
        "opaque_masked_merge",
        "opaque_tone_matched",
    },
    "tone_merged_object": {"alpha_floating", "opaque_masked_merge", "opaque_tone_matched"},
    "source_visible_frame": {"intentional_frame"},
}
MODE_EDGE_POLICIES = {
    "alpha_floating": {"alpha", "not_visible"},
    "opaque_full_bleed": {"bleed", "not_visible"},
    "opaque_masked_merge": {"bleed", "mask", "not_visible"},
    "opaque_tone_matched": {"tone_match", "not_visible"},
    "intentional_frame": {"source_frame", "not_visible"},
}
TOPOLOGY_UNIT_KINDS = {
    "section_field": {"full_field_scene_plate", "clean_background_plate"},
    "floating_scene": {"transparent_foreground", "transparent_scene"},
    "contained_artwork": {"card_artwork_plate", "atomic_raster"},
    "tone_merged_object": {"transparent_foreground", "transparent_scene", "atomic_raster"},
    "source_visible_frame": {"card_artwork_plate", "atomic_raster"},
}


def finding(status: str, fid: str, message: str, element_id: str, **extra) -> dict:
    row = {
        "id": fid,
        "status": status,
        "elementId": element_id,
        "message": message,
    }
    row.update(extra)
    return row


def resolve_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [root / path, Path.cwd() / path]
    candidates.extend(parent / path for parent in root.parents)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return root / path


def readable_file(root: Path, value: str | None) -> bool:
    path = resolve_path(root, value)
    return bool(path and path.is_file() and path.stat().st_size > 0)


def failed_generation_attempts(element: dict) -> list[dict]:
    return [
        attempt
        for attempt in element.get("generationAttempts", []) or []
        if attempt.get("status") == "failed"
        and attempt.get("generator")
        and attempt.get("prompt")
        and attempt.get("error")
    ]


def require_file_evidence(
    checks: list[dict], root: Path, element_id: str, payload: dict, prefix: str
) -> None:
    for field in ("reviewPath", "pairPath"):
        value = payload.get(field)
        if not readable_file(root, value):
            checks.append(
                finding(
                    "blocked",
                    f"{prefix}-{field}-missing",
                    f"'{element_id}' lacks readable {field} evidence: {value}",
                    element_id,
                )
            )


def require_clean_check(
    checks: list[dict], element_id: str, payload: dict, prefix: str
) -> None:
    contamination = payload.get("contaminationCheck") or {}
    if contamination.get("verdict") != "clean" or not contamination.get("method"):
        checks.append(
            finding(
                "blocked",
                f"{prefix}-contamination-proof",
                f"'{element_id}' needs contaminationCheck.method and verdict='clean'",
                element_id,
            )
        )


def evaluate_semantic_pixel_protection(
    checks: list[dict], root: Path, element: dict
) -> None:
    element_id = str(element.get("id") or "<missing-id>")
    generated = element.get("generatedAsset") or {}
    if generated.get("backgroundRemovalUsed") is not True:
        return
    protection = element.get("semanticPixelProtection")
    if not isinstance(protection, dict):
        checks.append(finding(
            "blocked", "semantic-pixel-protection-missing",
            f"'{element_id}' used background removal without protected semantic color checks",
            element_id,
        ))
        return
    source_path = resolve_path(root, protection.get("sourcePath"))
    master_path = resolve_path(root, protection.get("transparentMasterPath"))
    samples = protection.get("protectedSamples")
    if (
        source_path is None or not source_path.is_file()
        or master_path is None or not master_path.is_file()
        or not isinstance(samples, list) or not samples
    ):
        checks.append(finding(
            "blocked", "semantic-pixel-protection-evidence-missing",
            f"'{element_id}' needs readable pre-key/master PNGs and protectedSamples",
            element_id,
        ))
        return
    if not readable_file(root, protection.get("reviewPath")):
        checks.append(finding(
            "blocked", "semantic-pixel-protection-review-missing",
            f"'{element_id}' needs a readable 200% semantic-detail review crop",
            element_id,
        ))
    try:
        metrics = inspect_protected_color_retention(source_path, master_path, samples)
    except (OSError, ValueError, TypeError, AttributeError, zlib.error) as exc:
        checks.append(finding(
            "blocked", "semantic-pixel-protection-read-failed",
            f"'{element_id}' protected semantic pixels could not be inspected: {exc}",
            element_id,
        ))
        return
    if not metrics["pass"]:
        failed = [row for row in metrics["samples"] if not row["pass"]]
        checks.append(finding(
            "blocked", "semantic-pixel-loss",
            f"'{element_id}' background removal erased or weakened protected semantic pixels",
            element_id, failedSamples=failed, pixelMetrics=metrics,
        ))
    else:
        checks.append(finding(
            "pass", "semantic-pixels-retained",
            f"'{element_id}' protected semantic colors survived background removal",
            element_id, pixelMetrics=metrics,
        ))


def adopted_workspace_path(element: dict) -> str | None:
    payload_name = {
        "generated": "generatedAsset",
        "replace": "replacedAsset",
        "crop-asset": "croppedAsset",
    }.get(element.get("assetStrategy"))
    payload = element.get(payload_name) if payload_name else None
    return payload.get("workspacePath") if isinstance(payload, dict) else None


def adopted_asset_receipts(manifest: dict, root: Path) -> list[dict]:
    """Bind the exact raster bytes authorized by this preflight report."""
    receipts = []
    for element in manifest.get("elements", []):
        if not isinstance(element, dict):
            continue
        value = adopted_workspace_path(element)
        path = resolve_path(root, value)
        if not value or not path or not path.is_file():
            continue
        data = path.read_bytes()
        receipts.append({
            "elementId": str(element.get("id") or "<missing-id>"),
            "path": value,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        })
    return receipts


def evaluate_surface_integration(
    checks: list[dict], root: Path, element: dict
) -> None:
    """Validate the raster's real pixels against its web-surface ownership."""
    surface_contract = element.get("assetSurfaceContract")
    if not isinstance(surface_contract, dict):
        return
    element_id = str(element.get("id") or "<missing-id>")
    integration = element.get("surfaceIntegration")
    if not isinstance(integration, dict):
        checks.append(
            finding(
                "blocked",
                "surface-integration-missing",
                (
                    f"'{element_id}' declares an assetSurfaceContract but not how the "
                    "raster joins the web surface"
                ),
                element_id,
            )
        )
        return

    mode = integration.get("mode")
    topology = integration.get("sourceTopology")
    topology_evidence = integration.get("sourceTopologyEvidencePath")
    edge_policy = integration.get("edgePolicy")
    owner = integration.get("consumerSurfaceOwner")
    whitespace_owner = integration.get("outerWhitespaceOwner")
    missing = []
    if mode not in SURFACE_MODES:
        missing.append("mode")
    if topology not in SOURCE_TOPOLOGIES:
        missing.append("sourceTopology")
    if not topology_evidence:
        missing.append("sourceTopologyEvidencePath")
    if not isinstance(edge_policy, dict) or set(edge_policy) != {"top", "right", "bottom", "left"}:
        missing.append("edgePolicy")
    elif any(value not in EDGE_POLICIES for value in edge_policy.values()):
        missing.append("edgePolicy values")
    if owner not in {"css", "asset", "shared"}:
        missing.append("consumerSurfaceOwner")
    if whitespace_owner not in {"css", "asset", "none"}:
        missing.append("outerWhitespaceOwner")
    if not integration.get("cropInUsePath"):
        missing.append("cropInUsePath")
    if missing:
        checks.append(
            finding(
                "blocked",
                "surface-integration-fields-missing",
                f"'{element_id}' surfaceIntegration is incomplete: {', '.join(missing)}",
                element_id,
                missing=missing,
            )
        )
        return
    if not readable_file(root, topology_evidence):
        checks.append(
            finding(
                "blocked",
                "surface-topology-evidence-missing",
                f"'{element_id}' lacks a readable source-topology crop",
                element_id,
            )
        )
    if not readable_file(root, integration.get("cropInUsePath")):
        checks.append(
            finding(
                "blocked",
                "surface-crop-in-use-missing",
                f"'{element_id}' lacks a readable final in-context surface crop",
                element_id,
            )
        )

    allowed_modes = TOPOLOGY_MODES.get(topology, set())
    if mode not in allowed_modes:
        checks.append(
            finding(
                "blocked",
                "surface-topology-mode-conflict",
                (
                    f"'{element_id}' sourceTopology={topology} cannot use mode={mode}; "
                    "return to raster generation instead of inventing a framed image"
                ),
                element_id,
                allowedModes=sorted(allowed_modes),
            )
        )
    allowed_edges = MODE_EDGE_POLICIES.get(mode, set())
    invalid_edges = {
        edge: value for edge, value in edge_policy.items() if value not in allowed_edges
    }
    if invalid_edges:
        checks.append(
            finding(
                "blocked",
                "surface-edge-policy-conflict",
                f"'{element_id}' edgePolicy contradicts mode={mode}",
                element_id,
                invalidEdges=invalid_edges,
                allowedEdgePolicies=sorted(allowed_edges),
            )
        )

    unit = element.get("assetUnit")
    unit_kind = unit.get("kind") if isinstance(unit, dict) else None
    allowed_kinds = TOPOLOGY_UNIT_KINDS.get(topology, set())
    if unit_kind is not None and unit_kind not in allowed_kinds:
        checks.append(
            finding(
                "blocked",
                "surface-topology-unit-conflict",
                f"'{element_id}' sourceTopology={topology} cannot use assetUnit.kind={unit_kind}",
                element_id,
                allowedAssetUnitKinds=sorted(allowed_kinds),
            )
        )

    if topology == "section_field":
        if surface_contract.get("consumerOwnsFrame") is True:
            checks.append(
                finding(
                    "blocked",
                    "surface-section-field-invented-frame",
                    f"'{element_id}' owns the section field in the source but its consumer invents a frame",
                    element_id,
                )
            )
        if surface_contract.get("assetMustBleedToEdges") is not True:
            checks.append(
                finding(
                    "blocked",
                    "surface-section-field-must-bleed",
                    f"'{element_id}' section field must bleed to its section surface",
                    element_id,
                )
            )
        if unit_kind == "full_field_scene_plate" and not (
            element.get("copySpace") or element.get("copySpaceNotRequiredReason")
        ):
            checks.append(
                finding(
                    "blocked",
                    "surface-section-field-copy-space-missing",
                    f"'{element_id}' full-field scene must declare copySpace or why none is needed",
                    element_id,
                )
            )
    elif topology == "floating_scene" and surface_contract.get("consumerOwnsFrame") is True:
        checks.append(
            finding(
                "blocked",
                "surface-floating-scene-invented-frame",
                f"'{element_id}' floats in the source but its consumer invents an image frame",
                element_id,
            )
        )

    workspace_path = resolve_path(root, adopted_workspace_path(element))
    if workspace_path is None or not workspace_path.is_file():
        return
    try:
        metrics = inspect_png_surface(workspace_path)
    except (OSError, ValueError, zlib.error) as exc:
        checks.append(
            finding(
                "blocked",
                "surface-pixel-read-failed",
                f"'{element_id}' surface pixels could not be inspected: {exc}",
                element_id,
            )
        )
        return

    transparent = metrics["transparentPixelFraction"]
    uniform_band = metrics["uniformOuterBandFraction"]
    if mode == "alpha_floating":
        if transparent < 0.05:
            checks.append(
                finding(
                    "blocked",
                    "surface-alpha-required",
                    f"'{element_id}' is alpha_floating but fewer than 5% of sampled pixels are transparent",
                    element_id,
                    pixelMetrics=metrics,
                )
            )
    elif mode == "opaque_full_bleed":
        if surface_contract.get("assetMustBleedToEdges") is not True:
            checks.append(
                finding(
                    "blocked",
                    "surface-full-bleed-contract-conflict",
                    f"'{element_id}' is opaque_full_bleed but assetMustBleedToEdges is not true",
                    element_id,
                    pixelMetrics=metrics,
                )
            )
        if owner == "css" or surface_contract.get("consumerOwnsBackground") is True:
            checks.append(
                finding(
                    "blocked",
                    "surface-full-bleed-owner-conflict",
                    f"'{element_id}' full-bleed raster and CSS both claim the background surface",
                    element_id,
                    pixelMetrics=metrics,
                )
            )
    elif mode == "opaque_masked_merge":
        if not integration.get("maskOwner"):
            checks.append(
                finding(
                    "blocked",
                    "surface-mask-owner-missing",
                    f"'{element_id}' masked merge does not name the CSS/SVG mask owner",
                    element_id,
                    pixelMetrics=metrics,
                )
            )
    elif mode == "opaque_tone_matched":
        color = integration.get("consumerBackgroundColor")
        try:
            expected_rgb = parse_hex_color(color)
        except (AttributeError, TypeError, ValueError):
            checks.append(
                finding(
                    "blocked",
                    "surface-consumer-color-missing",
                    f"'{element_id}' tone-matched mode needs consumerBackgroundColor #RRGGBB",
                    element_id,
                    pixelMetrics=metrics,
                )
            )
        else:
            tolerance = integration.get("edgeColorTolerance", 12)
            if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or tolerance < 0:
                tolerance = 12
            distance = rgb_distance(metrics["edgeMeanRgb"], expected_rgb)
            if distance > tolerance:
                checks.append(
                    finding(
                        "blocked",
                        "surface-edge-color-mismatch",
                        (
                            f"'{element_id}' edge color differs from its consumer surface "
                            f"by {distance:.2f}, above tolerance {tolerance}"
                        ),
                        element_id,
                        colorDistance=round(distance, 3),
                        pixelMetrics=metrics,
                    )
                )
    elif mode == "intentional_frame":
        if integration.get("sourceFrameVisible") is not True or not integration.get("sourceEvidencePath"):
            checks.append(
                finding(
                    "blocked",
                    "surface-intentional-frame-unproven",
                    f"'{element_id}' may keep a raster frame only with source-visible frame evidence",
                    element_id,
                    pixelMetrics=metrics,
                )
            )

    double_padding_risk = (
        mode not in {"opaque_masked_merge", "opaque_tone_matched", "intentional_frame"}
        and surface_contract.get("consumerOwnsBackground") is True
        and surface_contract.get("assetMustNotContainPadding") is True
        and whitespace_owner != "asset"
        and transparent < 0.01
        and uniform_band >= 0.04
    )
    if double_padding_risk:
        checks.append(
            finding(
                "blocked",
                "surface-double-padding-risk",
                (
                    f"'{element_id}' has an opaque uniform outer band while CSS owns the "
                    "background/padding; regenerate transparent, bleed/mask it, or tone-match it"
                ),
                element_id,
                pixelMetrics=metrics,
            )
        )

    if not any(
        row.get("status") == "blocked"
        and row.get("elementId") == element_id
        and str(row.get("id", "")).startswith("surface-")
        for row in checks
    ):
        checks.append(
            finding(
                "pass",
                "surface-integration-valid",
                f"'{element_id}' pixels and web-surface ownership agree",
                element_id,
                mode=mode,
                pixelMetrics=metrics,
            )
        )


def evaluate_asset_policy(manifest: dict, work_root: Path | str) -> dict:
    root = Path(work_root)
    checks: list[dict] = []
    photo_led = manifest.get("photoLed")
    critical_assets = [
        element
        for element in manifest.get("elements", []) or []
        if element.get("mediaClass") in PHOTO_CLASSES
        and element.get("qaPriority") in CRITICAL_PRIORITIES
    ]

    if not isinstance(photo_led, bool):
        checks.append(
            {
                "id": "photo-led-declaration-missing",
                "status": "blocked",
                "message": "manifest must declare photoLed: true or false before asset selection",
            }
        )
    elif photo_led and not critical_assets:
        checks.append(
            {
                "id": "photo-led-assets-missing",
                "status": "blocked",
                "message": "photoLed=true but no fv/section-critical photo or illustration is declared",
            }
        )
    elif not photo_led and critical_assets:
        checks.append(
            {
                "id": "photo-led-declaration-inconsistent",
                "status": "blocked",
                "message": "photoLed=false conflicts with declared critical photo/illustration assets",
            }
        )
    elif not critical_assets:
        checks.append(
            {
                "id": "critical-photo-assets",
                "status": "pass",
                "message": "no fv/section-critical photo or illustration assets declared",
            }
        )

    for element in critical_assets:
        element_id = str(element.get("id") or "<missing-id>")
        strategy = element.get("assetStrategy")
        overlap = element.get("sourceFrameHasForegroundOverlap")
        clean_layered = element.get("cleanLayeredSource")
        visual_role = element.get("visualRole")
        source_frame = element.get("sourceImage") or manifest.get("image")

        decision_missing = []
        if not isinstance(overlap, bool):
            decision_missing.append("sourceFrameHasForegroundOverlap")
        if not isinstance(clean_layered, bool):
            decision_missing.append("cleanLayeredSource")
        if not visual_role:
            decision_missing.append("visualRole")
        if not source_frame:
            decision_missing.append("sourceImage or manifest.image")
        if decision_missing:
            checks.append(
                finding(
                    "blocked",
                    "asset-decision-fields-missing",
                    f"'{element_id}' must declare before asset selection: {', '.join(decision_missing)}",
                    element_id,
                    missing=decision_missing,
                )
            )
            continue
        if overlap is True and not element.get("sourceFrameOverlapKinds"):
            checks.append(
                finding(
                    "blocked",
                    "asset-overlap-kinds-missing",
                    f"'{element_id}' declares source overlap but does not list the overlapping devices",
                    element_id,
                )
            )
        if strategy not in RASTER_STRATEGIES:
            checks.append(
                finding(
                    "blocked",
                    "asset-raster-strategy-invalid",
                    f"'{element_id}' photo-class asset uses invalid strategy '{strategy}'",
                    element_id,
                )
            )
            continue

        if strategy in {"generated", "replace"}:
            surface_missing = []
            if not isinstance(element.get("assetUnit"), dict):
                surface_missing.append("assetUnit")
            if not isinstance(element.get("assetSurfaceContract"), dict):
                surface_missing.append("assetSurfaceContract")
            if not isinstance(element.get("surfaceIntegration"), dict):
                surface_missing.append("surfaceIntegration")
            if surface_missing:
                checks.append(
                    finding(
                        "blocked",
                        "surface-contract-fields-missing",
                        (
                            f"'{element_id}' generated/replaced critical raster must freeze "
                            f"generation unit and source surface topology: {', '.join(surface_missing)}"
                        ),
                        element_id,
                        missing=surface_missing,
                    )
                )

        if strategy == "crop-asset":
            if overlap is True and clean_layered is not True:
                checks.append(
                    finding(
                        "blocked",
                        "asset-overlap-crop-forbidden",
                        (
                            f"'{element_id}' crops a fused photo field. A clean-looking subcrop "
                            "does not preserve the comp's environment; regenerate or replace the full plate"
                        ),
                        element_id,
                        implementationAllowed=False,
                    )
                )
            if element.get("cropPreservesComposition") is not True:
                checks.append(
                    finding(
                        "blocked",
                        "asset-crop-composition-unproven",
                        f"'{element_id}' crop does not prove that the comp's photo composition is preserved",
                        element_id,
                    )
                )
            cropped = element.get("croppedAsset") or {}
            missing = [
                key
                for key in ("workspacePath", "sourcePath", "sourceRoi", "reviewPath", "pairPath")
                if not cropped.get(key)
            ]
            if missing:
                checks.append(
                    finding(
                        "blocked",
                        "cropped-asset-fields-missing",
                        f"'{element_id}' croppedAsset missing fields: {', '.join(missing)}",
                        element_id,
                    )
                )
            else:
                if not readable_file(root, cropped.get("workspacePath")):
                    checks.append(
                        finding(
                            "blocked",
                            "cropped-asset-file-missing",
                            f"'{element_id}' crop file is missing or empty: {cropped.get('workspacePath')}",
                            element_id,
                        )
                    )
                if not readable_file(root, cropped.get("sourcePath")):
                    checks.append(
                        finding(
                            "blocked",
                            "cropped-asset-source-file-missing",
                            f"'{element_id}' crop source is missing or empty: {cropped.get('sourcePath')}",
                            element_id,
                        )
                    )
                if overlap is True and clean_layered is True:
                    clean_source = resolve_path(root, cropped.get("sourcePath"))
                    fused_source = resolve_path(root, source_frame)
                    if clean_source == fused_source:
                        checks.append(
                            finding(
                                "blocked",
                                "clean-layered-source-proof-invalid",
                                f"'{element_id}' claims a clean layered source but croppedAsset.sourcePath is the fused comp",
                                element_id,
                            )
                        )
                require_clean_check(checks, element_id, cropped, "cropped-asset")
                require_file_evidence(checks, root, element_id, cropped, "cropped-asset")

        elif strategy == "generated":
            generated = element.get("generatedAsset") or {}
            missing = [
                key
                for key in ("prompt", "sourceImage", "workspacePath", "generator", "reviewPath", "pairPath")
                if not generated.get(key)
            ]
            if missing:
                checks.append(
                    finding(
                        "blocked",
                        "generated-asset-fields-missing",
                        f"'{element_id}' generatedAsset missing fields: {', '.join(missing)}",
                        element_id,
                    )
                )
            else:
                if not readable_file(root, generated.get("sourceImage")):
                    checks.append(
                        finding(
                            "blocked",
                            "generated-asset-source-file-missing",
                            f"'{element_id}' generation source is missing or empty: {generated.get('sourceImage')}",
                            element_id,
                        )
                    )
                if not readable_file(root, generated.get("workspacePath")):
                    checks.append(
                        finding(
                            "blocked",
                            "generated-asset-file-missing",
                            f"'{element_id}' generated file is missing or empty: {generated.get('workspacePath')}",
                            element_id,
                        )
                    )
                require_clean_check(checks, element_id, generated, "generated-asset")
                require_file_evidence(checks, root, element_id, generated, "generated-asset")

        elif strategy == "replace":
            replaced = element.get("replacedAsset") or {}
            missing = [
                key
                for key in (
                    "sourcePath",
                    "workspacePath",
                    "replacementKind",
                    "matchRationale",
                    "reviewPath",
                    "pairPath",
                )
                if not replaced.get(key)
            ]
            if missing:
                checks.append(
                    finding(
                        "blocked",
                        "replaced-asset-fields-missing",
                        f"'{element_id}' replacedAsset missing fields: {', '.join(missing)}",
                        element_id,
                    )
                )
            else:
                if not readable_file(root, replaced.get("workspacePath")):
                    checks.append(
                        finding(
                            "blocked",
                            "replaced-asset-file-missing",
                            f"'{element_id}' replacement file is missing or empty: {replaced.get('workspacePath')}",
                            element_id,
                        )
                    )
                require_clean_check(checks, element_id, replaced, "replaced-asset")
                require_file_evidence(checks, root, element_id, replaced, "replaced-asset")
            if replaced.get("replacementKind") == "licensed-stock" and not replaced.get("license"):
                checks.append(
                    finding(
                        "blocked",
                        "stock-license-missing",
                        f"'{element_id}' licensed stock replacement has no license/source record",
                        element_id,
                    )
                )
            if overlap is True and replaced.get("replacementKind") == "licensed-stock" and not failed_generation_attempts(element):
                checks.append(
                    finding(
                        "blocked",
                        "generation-attempt-missing-before-stock",
                        f"'{element_id}' fell back to stock without a recorded failed generation attempt",
                        element_id,
                    )
                )
        elif strategy == "placeholder":
            if not failed_generation_attempts(element):
                checks.append(
                    finding(
                        "blocked",
                        "generation-attempt-missing-before-placeholder",
                        f"'{element_id}' uses a placeholder without a recorded failed generation attempt",
                        element_id,
                        implementationAllowed=False,
                    )
                )
            else:
                checks.append(
                    finding(
                        "needs_work",
                        "asset-placeholder-earned",
                        f"'{element_id}' has an earned placeholder; implementation may continue but completion may not",
                        element_id,
                        implementationAllowed=True,
                        completionAllowed=False,
                    )
                )

        evaluate_semantic_pixel_protection(checks, root, element)
        evaluate_surface_integration(checks, root, element)

        element_blocked = any(
            row.get("status") == "blocked" and row.get("elementId") == element_id
            for row in checks
        )
        element_needs_work = any(
            row.get("status") == "needs_work" and row.get("elementId") == element_id
            for row in checks
        )
        if not element_blocked and not element_needs_work:
            checks.append(
                finding(
                    "pass",
                    "asset-decision-valid",
                    f"'{element_id}' asset decision is evidenced and implementation-ready",
                    element_id,
                )
            )

    # Lettering decals are exempt from DOM copy checks, so their exact content
    # and shipped asset must be proved here instead. Otherwise a generated
    # strategy with no bitmap can satisfy visual-check by rendering an empty div.
    for element in manifest.get("elements", []) or []:
        if element.get("mediaClass") != "lettering-decal":
            continue
        element_id = str(element.get("id") or "<missing-id>")
        strategy = element.get("assetStrategy")
        proof = element.get("letteringProof") or {}
        content = (element.get("text") or {}).get("content")
        missing = [key for key in ("exactText", "method", "pairPath") if not proof.get(key)]
        if not content:
            missing.append("text.content")
        if missing:
            checks.append(
                finding(
                    "blocked",
                    "lettering-proof-fields-missing",
                    f"'{element_id}' lettering proof missing fields: {', '.join(missing)}",
                    element_id,
                )
            )
            continue
        if proof.get("exactText") != content:
            checks.append(
                finding(
                    "blocked",
                    "lettering-exact-text-mismatch",
                    f"'{element_id}' letteringProof.exactText does not match text.content",
                    element_id,
                )
            )
        if not readable_file(root, proof.get("pairPath")):
            checks.append(
                finding(
                    "blocked",
                    "lettering-pair-missing",
                    f"'{element_id}' lacks readable exact-text crop-pair evidence: {proof.get('pairPath')}",
                    element_id,
                )
            )
        payload_name = {
            "generated": "generatedAsset",
            "replace": "replacedAsset",
            "crop-asset": "croppedAsset",
        }.get(strategy)
        if payload_name:
            payload = element.get(payload_name) or {}
            workspace_path = payload.get("workspacePath")
            if not workspace_path or not readable_file(root, workspace_path):
                checks.append(
                    finding(
                        "blocked",
                        "lettering-asset-file-missing",
                        f"'{element_id}' lacks a readable shipped lettering asset: {workspace_path}",
                        element_id,
                    )
                )
            if strategy == "generated" and (
                not payload.get("generator") or not payload.get("prompt")
            ):
                checks.append(
                    finding(
                        "blocked",
                        "lettering-generation-evidence-missing",
                        f"'{element_id}' generated lettering lacks generator/prompt evidence",
                        element_id,
                    )
                )
        elif strategy not in {"svg", "html-text"}:
            checks.append(
                finding(
                    "blocked",
                    "lettering-strategy-invalid",
                    f"'{element_id}' uses unsupported lettering strategy '{strategy}'",
                    element_id,
                )
            )

    status = "blocked" if any(row["status"] == "blocked" for row in checks) else (
        "needs_work" if any(row["status"] == "needs_work" for row in checks) else "pass"
    )
    return {
        "status": status,
        "implementationAllowed": status != "blocked",
        "completionAllowed": status == "pass",
        "checks": checks,
        "summary": {
            "pass": sum(row["status"] == "pass" for row in checks),
            "needs_work": sum(row["status"] == "needs_work" for row in checks),
            "blocked": sum(row["status"] == "blocked" for row in checks),
        },
        "contract": (
            "Run after manifest asset decisions and before CSS. A blocked result stops "
            "implementation. needs_work is reserved for an earned placeholder and prevents completion."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--work-root")
    parser.add_argument("--out")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = {}
    root = Path(args.work_root) if args.work_root else manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result = {
            "status": "blocked",
            "implementationAllowed": False,
            "completionAllowed": False,
            "checks": [
                {
                    "id": "manifest-unreadable",
                    "status": "blocked",
                    "message": f"cannot read manifest {manifest_path}: {exc}",
                }
            ],
        }
    else:
        result = evaluate_asset_policy(manifest, root)
    if manifest_path.is_file():
        data = manifest_path.read_bytes()
        result["inputs"] = {
            "manifest": {
                "path": str(manifest_path),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            },
            "assets": adopted_asset_receipts(manifest, root),
        }

    output = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output + "\n", encoding="utf-8")
    print(output)
    sys.exit(0 if result["status"] == "pass" else 2 if result["status"] == "blocked" else 1)


if __name__ == "__main__":
    main()
