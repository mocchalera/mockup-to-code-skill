#!/usr/bin/env python3
"""normalize_image: put the mockup into the ONE canonical coordinate space.

Run this FIRST. VLM vision sees a downscaled copy of large images, and
generated mockups are often 1536/2048px wide while the implementation targets
1440px. All hypotheses, measurements, manifests, DOMRects and diffs must live
in a single coordinate space: the target viewport width.

Works with OpenCV or, as a fallback, Pillow + numpy (see _imgcompat.py).

Usage:
  python3 normalize_image.py raw_mockup.png --width 1440 --out work/mockup.png

Output: resized PNG + JSON with the scale factor (for tracing back if needed).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _imgcompat as imc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    img = imc.imread(args.image)
    if img is None:
        sys.exit(f"cannot read image: {args.image}")
    H, W = img.shape[:2]
    scale = args.width / W
    out_h = int(round(H * scale))
    resized = imc.resize(img, args.width, out_h)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    imc.imwrite(args.out, resized)
    print(json.dumps({
        "source": args.image, "source_size": [W, H],
        "out": args.out, "out_size": [args.width, out_h],
        "scale": round(scale, 6),
        "backend": imc.BACKEND,
        "note": "all downstream coordinates are in this normalized space",
    }, indent=2))


if __name__ == "__main__":
    main()
