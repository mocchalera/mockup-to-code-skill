#!/usr/bin/env python3
"""crop_pair: side-by-side comp-vs-build crop evidence, one command.

Phase 7 verdicts (present/adapted/missing/waived) and FV-gate typography
checks must be judged from RENDERED PIXELS, not from code or memory
(principle 14). This tool makes that judgment auditable: it cuts the same
device region out of the comp frame and out of the build render/strip,
scales both to a shared height (default 2x zoom), labels the halves, and
writes ONE pair image the review can cite by path.

Works with OpenCV or Pillow+numpy (fallback-safe — evidence generation
must never depend on cv2).

Usage:
  python3 crop_pair.py \
    --comp work/mockups/section-01-hero.png  --comp-roi 40,90,760,420 \
    --build work/reports/rendered.png        --build-roi 24,80,700,400 \
    --out work/reports/crops/01-hero-heading-pair.png --zoom 2

  # labels default to COMP / BUILD; override for e.g. font bake-offs:
  ... --label-a "COMP" --label-b "Noto Sans JP 900"

Output: PNG (comp left, build right, labeled) + a one-line JSON report on
stdout with the resolved ROIs, zoom, and output path — paste the path into
the section-review verdict row.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _imgcompat as imc

LABEL_H = 28
GAP = 6
BG = 255


def parse_roi(s):
    p = [int(v) for v in s.replace(" ", "").split(",")]
    if len(p) != 4:
        raise argparse.ArgumentTypeError("roi must be x,y,w,h")
    return p


def crop(path, roi):
    img = imc.imread(path)
    if img is None:
        sys.exit(f"cannot read image: {path}")
    H, W = img.shape[:2]
    x, y, w, h = roi
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        sys.exit(f"roi {roi} is outside {path} ({W}x{H})")
    return img[y0:y1, x0:x1], [x0, y0, x1 - x0, y1 - y0]


def scale_to_height(img, target_h):
    h, w = img.shape[:2]
    return imc.resize(img, max(1, round(w * target_h / h)), target_h)


def draw_label(canvas, text, x, y):
    """Draw label text with whichever backend exists."""
    if imc.HAS_CV2:
        import cv2
        cv2.putText(canvas, text, (x + 4, y + LABEL_H - 9),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
        return canvas
    from PIL import Image, ImageDraw
    pil = Image.fromarray(canvas[:, :, ::-1])
    ImageDraw.Draw(pil).text((x + 4, y + 7), text, fill=(30, 30, 30))
    return np.asarray(pil)[:, :, ::-1].copy()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comp", required=True, help="comp frame image")
    ap.add_argument("--comp-roi", type=parse_roi, required=True)
    ap.add_argument("--build", required=True, help="build render / section strip")
    ap.add_argument("--build-roi", type=parse_roi, required=True)
    ap.add_argument("--out", required=True, help="output pair PNG")
    ap.add_argument("--zoom", type=float, default=2.0,
                    help="zoom factor applied to the comp crop height (default 2)")
    ap.add_argument("--label-a", default="COMP")
    ap.add_argument("--label-b", default="BUILD")
    args = ap.parse_args()

    a, roi_a = crop(args.comp, args.comp_roi)
    b, roi_b = crop(args.build, args.build_roi)

    target_h = max(1, round(a.shape[0] * args.zoom))
    a = scale_to_height(a, target_h)
    b = scale_to_height(b, target_h)

    W = a.shape[1] + GAP + b.shape[1]
    canvas = np.full((LABEL_H + target_h, W, 3), BG, dtype=np.uint8)
    canvas[LABEL_H:, :a.shape[1]] = a
    canvas[LABEL_H:, a.shape[1] + GAP:] = b
    canvas = draw_label(canvas, args.label_a, 0, 0)
    canvas = draw_label(canvas, args.label_b, a.shape[1] + GAP, 0)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    imc.imwrite(args.out, canvas)
    print(json.dumps({"out": args.out, "comp_roi": roi_a, "build_roi": roi_b,
                      "zoom": args.zoom, "backend": imc.BACKEND}))


if __name__ == "__main__":
    main()
