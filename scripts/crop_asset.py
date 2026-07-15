#!/usr/bin/env python3
"""crop_asset: cut a visual asset out of the mockup, with contamination check.

Photos/illustrations/complex decorations should be cropped as real assets,
never recreated in CSS. BUT: AI-generated mockups usually have text BAKED
INTO the photo — copy, headings, years, CTAs. Shipping such a crop under
real HTML text doubles the text; shipping it alone freezes unownable copy
into an image. This script warns about text-like regions inside the crop. It
never authorizes adoption: it cannot tell whether the ROI escaped overlap by
deleting the comp's intended environment or focal composition. A pixel-clean
result is only a candidate and must still pass asset_preflight.py.

When the crop IS contaminated, do not ship it: either obtain a layered /
text-free source asset, or REGENERATE the photo with imagegen
(assetStrategy: "generated" + generatedAsset evidence in the manifest).

Cropping works with OpenCV or Pillow+numpy; the contamination heuristic
needs OpenCV — without it the report says "unavailable" and you MUST
inspect the crop visually before use.

Usage:
  python3 crop_asset.py mockup.png --roi 720,120,520,640 --out assets/hero-photo.png
  python3 crop_asset.py mockup.png --roi 720,120,520,640 --out a.png --pad 4
  python3 crop_asset.py rendered.png --roi 0,900,1440,900 --out section.png \
      --purpose evidence-crop

Output: PNG + JSON report:
  {"contamination": {"text_like_share": 0.031, "suspect_regions": [...],
    "adoption_allowed": false,
    "recommended_action": "reject_or_regenerate_with_imagegen_or_layer_asset"}}

The check is a heuristic (edge-dense, line-like components). Always ALSO
inspect the crop visually and run asset_preflight.py before using it.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _imgcompat as imc

if imc.HAS_CV2:
    import cv2

CONTAMINATION_SHARE = 0.015


def parse_roi(s):
    p = [int(v) for v in s.replace(" ", "").split(",")]
    if len(p) != 4:
        raise argparse.ArgumentTypeError("roi must be x,y,w,h")
    return p


def text_like_regions(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 80, 200)
    # connect glyphs within a word horizontally
    dil = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3)))
    n, _, stats, _ = cv2.connectedComponentsWithStats(dil, connectivity=8)
    H, W = gray.shape
    suspects, area = [], 0
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if not (7 <= h <= 90):          # glyph-line height range
            continue
        if w < h * 1.6:                  # words/lines are elongated
            continue
        fill = a / float(w * h)
        if fill < 0.15 or fill > 0.95:   # too sparse or solid block
            continue
        suspects.append({"bbox": [int(x), int(y), int(w), int(h)], "fill": round(float(fill), 2)})
        area += int(w) * int(h)
    suspects.sort(key=lambda s: -(s["bbox"][2] * s["bbox"][3]))
    return suspects[:12], float(area) / float(H * W)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--roi", type=parse_roi, required=True)
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument(
        "--purpose",
        choices=("asset-candidate", "evidence-crop"),
        default="asset-candidate",
        help="asset candidates run contamination QA; rendered evidence crops do not",
    )
    ap.add_argument(
        "--no-check",
        action="store_true",
        help="legacy skip flag; output remains explicitly ineligible for asset adoption",
    )
    args = ap.parse_args()

    img = imc.imread(args.image)
    if img is None:
        sys.exit(f"cannot read image: {args.image}")
    H, W = img.shape[:2]
    x, y, w, h = args.roi
    x0, y0 = max(0, x - args.pad), max(0, y - args.pad)
    x1, y1 = min(W, x + w + args.pad), min(H, y + h + args.pad)
    crop = img[y0:y1, x0:x1]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    imc.imwrite(args.out, crop)

    report = {"image": args.image, "roi": [x0, y0, x1 - x0, y1 - y0], "out": args.out,
              "backend": imc.BACKEND, "purpose": args.purpose}
    skip_check = args.no_check or args.purpose == "evidence-crop"
    if skip_check:
        report["contamination"] = {
            "check": (
                "not_applicable_evidence_crop"
                if args.purpose == "evidence-crop"
                else "skipped_legacy_no_check"
            ),
            "adoption_allowed": False,
            "recommended_action": "do_not_use_as_asset_source",
            "note": (
                "This crop is presentation/QA evidence only. It cannot satisfy "
                "asset_preflight or generated/cropped asset proof."
            ),
        }
    else:
        if imc.HAS_CV2:
            suspects, share = text_like_regions(crop)
            contaminated = share > CONTAMINATION_SHARE
            report["contamination"] = {
                "text_like_share": round(share, 4),
                "contaminated": contaminated,
                "pixel_verdict": "suspect" if contaminated else "clean_candidate",
                "adoption_allowed": False,
                "suspect_regions": suspects if contaminated else suspects[:3],
                "recommended_action": (
                    "reject_or_regenerate_with_imagegen_or_layer_asset"
                    if contaminated
                    else "run_asset_preflight_before_adoption"
                ),
                "note": (
                    "heuristic pixel check only — verify visually, then run "
                    "asset_preflight.py; this report does not assess source-frame "
                    "overlap or composition preservation"
                ),
            }
        else:
            report["contamination"] = {
                "check": "unavailable_no_cv2",
                "adoption_allowed": False,
                "recommended_action": "inspect_visually_then_run_asset_preflight",
                "note": "OpenCV missing — YOU must look at the crop and confirm no "
                        "baked-in text, then classify source overlap/composition with "
                        "asset_preflight.py; if text is present, regenerate the photo",
            }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
