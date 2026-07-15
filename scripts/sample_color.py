#!/usr/bin/env python3
"""sample_color: measured color tokens from a mockup region (no LLM eyeballing).

K-means clustering over pixels in an ROI. Flat clusters (low internal std)
are UI colors safe to tokenize; textured clusters are photo/gradient content
and must NOT become CSS color tokens.

Works with OpenCV or, as a fallback, Pillow + numpy (see _imgcompat.py).

Usage:
  python3 sample_color.py mockup.png --roi 0,0,1440,120 --k 4
  python3 sample_color.py mockup.png --roi 0,0,1440,900 --exclude 720,120,600,640

Output (JSON): clusters sorted by share:
  [{"hex": "#f4552f", "share": 0.18, "std": 4.2, "kind": "flat"}, ...]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _imgcompat as imc

MAX_SAMPLES = 40000
FLAT_STD = 14.0


def parse_roi(s):
    p = [int(v) for v in s.replace(" ", "").split(",")]
    if len(p) != 4:
        raise argparse.ArgumentTypeError("roi must be x,y,w,h")
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--roi", type=parse_roi, help="x,y,w,h (default: whole image)")
    ap.add_argument("--exclude", action="append", type=parse_roi, default=[],
                    help="mask out region x,y,w,h (repeatable; e.g. photos)")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out")
    args = ap.parse_args()

    img = imc.imread(args.image)
    if img is None:
        sys.exit(f"cannot read image: {args.image}")

    mask = np.ones(img.shape[:2], dtype=bool)
    for ex, ey, ew, eh in args.exclude:
        mask[ey:ey + eh, ex:ex + ew] = False
    if args.roi:
        x, y, w, h = args.roi
        roi_mask = np.zeros_like(mask)
        roi_mask[y:y + h, x:x + w] = True
        mask &= roi_mask

    pixels = img[mask].astype(np.float32)
    if len(pixels) == 0:
        sys.exit("empty region after masking")
    if len(pixels) > MAX_SAMPLES:
        pixels = pixels[np.random.default_rng(0).choice(len(pixels), MAX_SAMPLES, replace=False)]

    k = min(args.k, len(np.unique(pixels, axis=0)))
    labels, centers = imc.kmeans(pixels, k)

    clusters = []
    for i in range(k):
        member = pixels[labels == i]
        if len(member) == 0:
            continue
        std = float(member.std(axis=0).mean())
        b, g, r = centers[i]
        clusters.append({
            "hex": "#{:02x}{:02x}{:02x}".format(int(round(r)), int(round(g)), int(round(b))),
            "share": round(len(member) / len(pixels), 4),
            "std": round(std, 1),
            "kind": "flat" if std < FLAT_STD else "textured",
        })
    clusters.sort(key=lambda c: -c["share"])

    out = {"image": args.image, "roi": args.roi, "excluded": args.exclude,
           "samples": int(len(pixels)), "clusters": clusters,
           "backend": imc.BACKEND,
           "note": "only kind=flat clusters are safe as CSS color tokens"}
    text = json.dumps(out, indent=2)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
