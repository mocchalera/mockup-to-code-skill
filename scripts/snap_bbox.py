#!/usr/bin/env python3
"""snap_bbox: refine hypothesized bounding boxes by snapping edges to gradients.

Core measurement primitive. The LLM's vision provides APPROXIMATE bboxes
(typically within +/-15px); this script refines each edge independently by
searching within --radius px for the strongest perpendicular color gradient.

    Detection is hard and brittle. Refinement is easy and robust.

Usage:
  python3 snap_bbox.py mockup.png --bbox 120,180,680,160 [--bbox ...] --radius 16
  python3 snap_bbox.py mockup.png --bbox 120,180,680,160 --out result.json

Output (JSON to stdout or --out):
  {"results": [{"input": [x,y,w,h], "snapped": [x,y,w,h],
    "edges": {"left": {"pos": 118, "moved": -2, "confidence": 0.91}, ...},
    "weak_edges": ["bottom"]}]}

Confidence: peak_gradient / (peak + median) in the search window.
  ~0.5 = no edge found (flat area) -> edge keeps the input guess, listed
  in weak_edges. >0.75 = strong, trustworthy edge.
"""
import argparse
import json
import sys

import cv2
import numpy as np

WEAK_THRESHOLD = 0.62
MARGIN_RATIO = 0.12  # shrink the sampling span to avoid corner effects


def gradient_maps(img):
    f = img.astype(np.float32)
    gx = np.abs(cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3))
    gy = np.abs(cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3))
    if gx.ndim == 3:  # color-aware: max over channels catches equal-luminance edges
        gx = gx.max(axis=2)
        gy = gy.max(axis=2)
    return gx, gy


def snap_1d(scores, guess, radius, length):
    lo = max(0, guess - radius)
    hi = min(length - 1, guess + radius)
    if hi <= lo:
        return guess, 0.0
    window = scores[lo:hi + 1]
    peak_i = int(np.argmax(window))
    peak = float(window[peak_i])
    med = float(np.median(window))
    conf = peak / (peak + med + 1e-6)
    pos = lo + peak_i

    if conf < WEAK_THRESHOLD:
        # full-bleed elements: a canvas boundary within reach IS the edge
        if guess - radius <= 0:
            return 0, 0.99
        if guess + radius >= length - 1:
            return length - 1, 0.99
        # otherwise stay weak: the CALLER decides whether to widen the radius.
        # (silent auto-widening chases distant unrelated edges — do not add it)
    return pos, round(conf, 3)


def snap_box(gx, gy, bbox, radius):
    H, W = gx.shape
    x, y, w, h = bbox
    x2, y2 = x + w, y + h
    my = max(2, int(h * MARGIN_RATIO))
    mx = max(2, int(w * MARGIN_RATIO))
    ys = slice(max(0, y + my), min(H, y2 - my))
    xs = slice(max(0, x + mx), min(W, x2 - mx))

    # 1D score per candidate position = mean perpendicular gradient along the edge line
    col_score = gx[ys, :].mean(axis=0)   # for left/right (vertical edges)
    row_score = gy[:, xs].mean(axis=1)   # for top/bottom (horizontal edges)

    edges = {}
    for name, scores, guess, length in (
        ("left", col_score, x, W), ("right", col_score, x2, W),
        ("top", row_score, y, H), ("bottom", row_score, y2, H),
    ):
        pos, conf = snap_1d(scores, guess, radius, length)
        edges[name] = {"pos": int(pos), "moved": int(pos - guess), "confidence": conf}

    weak = [n for n, e in edges.items() if e["confidence"] < WEAK_THRESHOLD]
    for n in weak:  # no reliable edge -> keep the hypothesis
        guess = {"left": x, "right": x2, "top": y, "bottom": y2}[n]
        edges[n]["pos"] = int(guess)
        edges[n]["moved"] = 0

    nx, ny = edges["left"]["pos"], edges["top"]["pos"]
    nw, nh = edges["right"]["pos"] - nx, edges["bottom"]["pos"] - ny
    return {
        "input": [x, y, w, h],
        "snapped": [int(nx), int(ny), int(nw), int(nh)],
        "edges": edges,
        "weak_edges": weak,
    }


def parse_bbox(s):
    parts = [int(round(float(p))) for p in s.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be x,y,w,h")
    return parts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--bbox", action="append", required=True, type=parse_bbox,
                    help="hypothesis bbox as x,y,w,h (repeatable)")
    ap.add_argument("--radius", type=int, default=16,
                    help="search radius in px around each edge (default 16)")
    ap.add_argument("--out", help="write JSON here instead of stdout")
    args = ap.parse_args()

    img = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"cannot read image: {args.image}")
    gx, gy = gradient_maps(img)

    out = {"image": args.image, "radius": args.radius,
           "results": [snap_box(gx, gy, b, args.radius) for b in args.bbox]}
    text = json.dumps(out, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
