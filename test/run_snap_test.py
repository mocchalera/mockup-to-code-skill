#!/usr/bin/env python3
"""Validation A: snap_bbox recovery accuracy against ground truth.

Perturbs known-true bboxes by +/-5..14px per edge (seeded), runs snap_bbox,
and measures how close the snapped boxes come back to the truth.
Box-like (flat-color) elements and text elements are scored separately —
text glyph extents differ from DOM boxes by design (half-leading).
"""
import json
import random
import sys

sys.path.insert(0, "scripts")
import cv2
from snap_bbox import gradient_maps, snap_box  # noqa: E402

BOX_ELS = ["hero-photo", "hero-cta", "card-1", "card-2", "card-3", "footer"]
TEXT_ELS = ["hero-title", "works-heading"]
RADIUS = 16

rng = random.Random(42)


def perturb(v):
    return v + rng.choice([-1, 1]) * rng.randint(5, 14)


def main():
    truth = {r["el"]: r for r in json.load(open("test/work/truth_rects.json"))["rects"]}
    img = cv2.imread("test/work/mockup.png", cv2.IMREAD_COLOR)
    gx, gy = gradient_maps(img)

    def run(els, label):
        errs, rows = [], []
        for el in els:
            t = truth[el]
            tb = [round(t["x"]), round(t["y"]), round(t["w"]), round(t["h"])]
            guess = [perturb(tb[0]), perturb(tb[1]), perturb(tb[2]), perturb(tb[3])]
            r = snap_box(gx, gy, guess, RADIUS)
            s = r["snapped"]
            e = [abs(s[i] - tb[i]) for i in range(4)]
            errs.extend(e)
            rows.append((el, tb, guess, s, e, r["weak_edges"]))
        print(f"\n== {label} ==")
        for el, tb, g, s, e, weak in rows:
            print(f"{el:14s} truth={tb} guess={g}")
            print(f"{'':14s} snap ={s}  err(x,y,w,h)={e}  weak={weak}")
        mean = sum(errs) / len(errs)
        mx = max(errs)
        print(f"-- {label}: mean abs err {mean:.2f}px, max {mx}px over {len(rows)} boxes")
        return mean, mx

    bm, bx = run(BOX_ELS, "flat/box elements")
    tm, tx = run(TEXT_ELS, "text elements (glyph box vs DOM box — offset expected)")

    print("\n== verdict ==")
    print(f"box elements:  mean {bm:.2f}px / max {bx}px  ({'PASS' if bx <= 2 else 'CHECK'})")
    print(f"text elements: mean {tm:.2f}px / max {tx}px  (systematic half-leading offset)")
    json.dump({"box": {"mean": bm, "max": bx}, "text": {"mean": tm, "max": tx}},
              open("test/work/snap_test.json", "w"), indent=2)


if __name__ == "__main__":
    main()
