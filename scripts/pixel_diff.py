#!/usr/bin/env python3
"""pixel_diff: masked pixel comparison for FINAL visual QA (not for layout repair).

Layout repair belongs to box_diff. Pixel diff catches what boxes cannot:
object-fit cropping, gradient direction, shadow strength, border radius feel.

Text regions MUST be masked: the mockup's generated glyphs are not a real
font, so their pixels can never match a browser render — chasing them makes
the repair loop oscillate. With --manifest, elements marked
"maskInPixelDiff": true are masked automatically.

In hybrid mode, FV photo/illustration elements shipped through `generated` or
`replace` are also excluded automatically: pixel identity is impossible by
construction and their quality is owned by asset_preflight, crop pairs, and
impression metrics. Opaque source-comparable foreground surfaces explicitly
marked `pixelDiffForeground: true` are carved back into comparison; structural
glyphs remain masked separately. Coverage is then measured against the remaining eligible
non-generated pixels. If an accepted full-frame regenerated plate leaves no
pixel-comparable area, the explicit verdict is `not_applicable_generated_media`
rather than a fake good score or an inevitable needs_work.

Usage:
  python3 pixel_diff.py mockup.png rendered.png --out-heatmap diff.png \
      [--manifest manifest.json] [--mask x,y,w,h ...] [--threshold 32] \
      [--min-coverage 0.20]

Output: heatmap PNG (red = differing) + JSON score.
"""
import argparse
import json
import sys

import cv2
import numpy as np


def parse_roi(s):
    p = [int(v) for v in s.replace(" ", "").split(",")]
    if len(p) != 4:
        raise argparse.ArgumentTypeError("mask must be x,y,w,h")
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mockup")
    ap.add_argument("rendered")
    ap.add_argument("--manifest", help="auto-mask elements with maskInPixelDiff")
    ap.add_argument("--mask", action="append", type=parse_roi, default=[])
    ap.add_argument("--threshold", type=int, default=32,
                    help="per-pixel RGB distance counted as 'different' (default 32)")
    ap.add_argument(
        "--min-coverage",
        type=float,
        help=(
            "minimum unmasked comparison coverage required for a usable verdict; "
            "defaults to 0.50 for pixel-clone and 0.20 otherwise"
        ),
    )
    ap.add_argument("--out-heatmap")
    ap.add_argument("--out", help="JSON report path")
    args = ap.parse_args()

    a = cv2.imread(args.mockup, cv2.IMREAD_COLOR)
    b = cv2.imread(args.rendered, cv2.IMREAD_COLOR)
    if a is None or b is None:
        sys.exit("cannot read input images")
    if a.shape[1] != b.shape[1]:
        sys.exit(f"width mismatch {a.shape[1]} vs {b.shape[1]} — render at the mockup's "
                 "normalized width; do not rescale to compare")
    h = min(a.shape[0], b.shape[0])
    height_gap = abs(a.shape[0] - b.shape[0])
    a, b = a[:h], b[:h]

    manual_masks = list(args.mask)
    text_masks = []
    generated_media_masks = []
    generated_media_elements = []
    foreground_carveouts = []
    foreground_elements = []
    foreground_exclusions = []
    manifest = None
    if args.manifest:
        with open(args.manifest, encoding="utf-8") as handle:
            manifest = json.load(handle)
        pad = 4
        for el in manifest.get("elements", []):
            if el.get("text", {}).get("maskInPixelDiff") and el.get("bbox"):
                bb = el["bbox"]
                text_masks.append([bb["x"] - pad, bb["y"] - pad, bb["w"] + 2 * pad, bb["h"] + 2 * pad])
            is_irreproducible_hybrid_media = (
                manifest.get("mode", "hybrid") == "hybrid"
                and el.get("mediaClass") in ("photo", "illustration")
                and el.get("assetStrategy") in ("generated", "replace")
                and el.get("bbox")
                and (
                    not el.get("sourceImage")
                    or not manifest.get("image")
                    or el.get("sourceImage") == manifest.get("image")
                )
            )
            if is_irreproducible_hybrid_media:
                bb = el["bbox"]
                generated_media_masks.append([bb["x"], bb["y"], bb["w"], bb["h"]])
                generated_media_elements.append(el.get("id") or el.get("el"))
            if el.get("pixelDiffForeground") is True and el.get("bbox"):
                bb = el["bbox"]
                foreground_carveouts.append([bb["x"], bb["y"], bb["w"], bb["h"]])
                foreground_elements.append(el.get("id") or el.get("el"))
            if el.get("pixelDiffForegroundExclusion"):
                foreground_exclusions.append(el.get("id") or el.get("el"))

    dist = np.linalg.norm(a.astype(np.float32) - b.astype(np.float32), axis=2)
    generated_media_excluded = np.zeros((h, a.shape[1]), dtype=bool)
    for m in generated_media_masks:
        mx, my, mw, mh = (int(round(v)) for v in m)
        generated_media_excluded[max(0, my):my + mh, max(0, mx):mx + mw] = True
    foreground_reincluded = np.zeros((h, a.shape[1]), dtype=bool)
    for m in foreground_carveouts:
        mx, my, mw, mh = (int(round(v)) for v in m)
        y1, y2 = max(0, my), min(h, my + mh)
        x1, x2 = max(0, mx), min(a.shape[1], mx + mw)
        foreground_reincluded[y1:y2, x1:x2] = generated_media_excluded[y1:y2, x1:x2]
        generated_media_excluded[y1:y2, x1:x2] = False
    valid = ~generated_media_excluded
    masks = manual_masks + text_masks + generated_media_masks
    for m in manual_masks + text_masks:
        mx, my, mw, mh = (int(round(v)) for v in m)
        valid[max(0, my):my + mh, max(0, mx):mx + mw] = False

    diff = (dist > args.threshold) & valid
    compared_px = int(valid.sum())
    total_px = int(valid.size)
    masked_px = total_px - compared_px
    coverage = float(compared_px) / float(total_px or 1)
    generated_media_masked_px = int(generated_media_excluded.sum())
    foreground_reincluded_px = int(foreground_reincluded.sum())
    foreground_regions = []
    for element_id, region in zip(foreground_elements, foreground_carveouts):
        mx, my, mw, mh = (int(round(v)) for v in region)
        y1, y2 = max(0, my), min(h, my + mh)
        x1, x2 = max(0, mx), min(a.shape[1], mx + mw)
        area_px = max(0, y2 - y1) * max(0, x2 - x1)
        compared_region_px = int(valid[y1:y2, x1:x2].sum())
        foreground_regions.append(
            {
                "id": element_id,
                "area_px": area_px,
                "compared_px": compared_region_px,
                "comparison_coverage": round(compared_region_px / float(area_px or 1), 5),
            }
        )
    generated_media_coverage = float(generated_media_masked_px) / float(total_px or 1)
    eligible_non_generated_px = total_px - generated_media_masked_px
    eligible_coverage = (
        float(compared_px) / float(eligible_non_generated_px)
        if eligible_non_generated_px > 0 else None
    )
    mode = (manifest or {}).get("mode", "hybrid")
    default_min_coverage = 0.50 if mode == "pixel-clone" else 0.20
    min_coverage = default_min_coverage if args.min_coverage is None else args.min_coverage
    if not 0.0 <= min_coverage <= 1.0:
        sys.exit("--min-coverage must be between 0 and 1")
    score = float(diff.sum()) / float(compared_px or 1)
    pixel_evidence_applicable = eligible_non_generated_px > 0
    pixel_verdict = (
        "not_applicable" if not pixel_evidence_applicable
        else "good" if score < 0.02
        else "acceptable" if score < 0.06
        else "needs_work"
    )
    coverage_for_gate = eligible_coverage if generated_media_masks else coverage
    evidence_sufficient = bool(
        pixel_evidence_applicable and compared_px > 0 and
        coverage_for_gate is not None and coverage_for_gate >= min_coverage
    )
    if not pixel_evidence_applicable and generated_media_masks:
        verdict = "not_applicable_generated_media"
    else:
        verdict = pixel_verdict if evidence_sufficient else "insufficient_coverage"

    if args.out_heatmap:
        base = cv2.cvtColor(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR) // 2 + 96
        heat = base.copy()
        heat[diff] = (60, 60, 230)
        heat[~valid] //= 2  # darken masked regions
        cv2.imwrite(args.out_heatmap, heat)

    report = {
        "diff_ratio": round(score, 5),
        "compared_px": compared_px,
        "masked_px": masked_px,
        "total_px": total_px,
        "comparison_coverage": round(coverage, 5),
        "eligible_non_generated_media_px": int(eligible_non_generated_px),
        "eligible_comparison_coverage": (
            round(eligible_coverage, 5) if eligible_coverage is not None else None
        ),
        "generated_media_masked_px": generated_media_masked_px,
        "generated_media_coverage": round(generated_media_coverage, 5),
        "auto_generated_media_masks": generated_media_elements,
        "auto_foreground_carveouts": foreground_elements,
        "auto_foreground_exclusions": foreground_exclusions,
        "foreground_regions": foreground_regions,
        "foreground_reincluded_px": foreground_reincluded_px,
        "foreground_union_coverage": round(foreground_reincluded_px / float(total_px or 1), 5),
        "min_comparison_coverage": round(min_coverage, 5),
        "coverage_sufficient": evidence_sufficient,
        "pixel_evidence_applicable": pixel_evidence_applicable,
        "masked_regions": len(masks),
        "height_gap_px": int(height_gap),
        "threshold": args.threshold,
        "heatmap": args.out_heatmap,
        "verdict": verdict,
        "pixel_verdict": pixel_verdict,
        "note": (
            "pixel identity is not applicable because verified generated/replaced hybrid media owns the full FV and no opaque foreground carve-out remains; asset policy, crop pairs, box diff and impression metrics remain mandatory"
            if verdict == "not_applicable_generated_media"
            else "comparison coverage is too low for a trustworthy pixel verdict; reduce text/manual masks "
            "or report pixel evidence as unavailable"
            if not evidence_sufficient
            else "inspect the heatmap; concentrated red = real problem, "
                 "scattered speckle = anti-aliasing noise"
        ),
    }
    if args.out:
        open(args.out, "w").write(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
