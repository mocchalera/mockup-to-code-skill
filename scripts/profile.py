#!/usr/bin/env python3
"""profile: 1D structural profile of a mockup along an axis.

Used to form/verify hypotheses about section boundaries, container edges,
column gaps, and card grids WITHOUT fragile full-page detection.

  axis=y : per-row stats  -> horizontal quiet bands = section paddings/gaps
  axis=x : per-col stats  -> vertical quiet bands  = container margins/gutters

Usage:
  python3 profile.py mockup.png --axis y                     # whole image
  python3 profile.py mockup.png --axis x --roi 0,760,1440,480  # card grid row

Output (JSON): compact summary, not raw arrays.
  quiet_bands: runs of low edge-density (candidate whitespace)
               [{"start": 700, "end": 779, "len": 80, "color": "#ffffff"}]
  change_points: strongest mean-color transitions [{"pos": 640, "strength": 0.42}]
"""
import argparse
import json
import sys

import cv2
import numpy as np


def parse_roi(s):
    p = [int(v) for v in s.replace(" ", "").split(",")]
    if len(p) != 4:
        raise argparse.ArgumentTypeError("roi must be x,y,w,h")
    return p


def rgb_hex(bgr):
    return "#{:02x}{:02x}{:02x}".format(int(bgr[2]), int(bgr[1]), int(bgr[0]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--axis", choices=["x", "y"], required=True)
    ap.add_argument("--roi", type=parse_roi, help="restrict to x,y,w,h")
    ap.add_argument("--quiet", type=float, default=0.06,
                    help="edge-density threshold (relative to max) for quiet bands")
    ap.add_argument("--min-band", type=int, default=6, help="min quiet band length px")
    ap.add_argument("--top", type=int, default=20, help="max change points reported")
    ap.add_argument("--out")
    args = ap.parse_args()

    img = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if img is None:
        sys.exit(f"cannot read image: {args.image}")

    ox = oy = 0
    if args.roi:
        x, y, w, h = args.roi
        img = img[y:y + h, x:x + w]
        ox, oy = x, y

    f = img.astype(np.float32)
    grad = np.abs(cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)).max(axis=2) + \
           np.abs(cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)).max(axis=2)

    reduce_axis = 1 if args.axis == "y" else 0  # y-profile aggregates over columns
    density = grad.mean(axis=reduce_axis)
    density = density / (density.max() + 1e-6)
    mean_color = f.mean(axis=reduce_axis)  # (N, 3) BGR per position

    offset = oy if args.axis == "y" else ox

    # quiet bands (run-length encode low-density positions)
    quiet = density < args.quiet
    bands = []
    i = 0
    N = len(density)
    while i < N:
        if quiet[i]:
            j = i
            while j + 1 < N and quiet[j + 1]:
                j += 1
            if j - i + 1 >= args.min_band:
                bands.append({
                    "start": i + offset, "end": j + offset, "len": j - i + 1,
                    "color": rgb_hex(mean_color[i:j + 1].mean(axis=0)),
                })
            i = j + 1
        else:
            i += 1

    # change points: peaks in mean-color first difference.
    # ABSOLUTE threshold (RGB distance), not max-normalized: one huge transition
    # (e.g. white->black footer) must not suppress subtle section boundaries
    # (e.g. #ffffff -> #f7f5f2).
    diff = np.linalg.norm(np.diff(mean_color, axis=0), axis=1)
    idx = np.argsort(diff)[::-1]
    change_points, used = [], []
    for i in idx:
        if diff[i] < 4.0 or len(change_points) >= args.top:
            break
        if any(abs(i - u) < 8 for u in used):  # non-max suppression
            continue
        used.append(i)
        change_points.append({"pos": int(i) + offset,
                              "strength": round(float(diff[i]), 1),
                              "from": rgb_hex(mean_color[max(0, i - 3)]),
                              "to": rgb_hex(mean_color[min(len(mean_color) - 1, i + 4)])})
    change_points.sort(key=lambda c: c["pos"])

    out = {"image": args.image, "axis": args.axis, "roi": args.roi,
           "length": N, "offset": offset,
           "quiet_bands": bands, "change_points": change_points}
    text = json.dumps(out, indent=2)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
