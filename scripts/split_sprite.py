#!/usr/bin/env python3
"""Split a transparent sprite by measured alpha clusters, never equal widths."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runs_from_mask(mask: np.ndarray) -> list[list[int]]:
    padded = np.concatenate(([False], mask, [False]))
    starts = np.flatnonzero(~padded[:-1] & padded[1:])
    ends = np.flatnonzero(padded[:-1] & ~padded[1:]) - 1
    return [[int(start), int(end)] for start, end in zip(starts, ends)]


def merge_to_count(runs: list[list[int]], count: int) -> tuple[list[list[int]], list[dict]]:
    merged = [row[:] for row in runs]
    history = []
    while len(merged) > count:
        gaps = [merged[index + 1][0] - merged[index][1] - 1 for index in range(len(merged) - 1)]
        index = min(range(len(gaps)), key=lambda candidate: (gaps[candidate], candidate))
        left, right = merged[index], merged[index + 1]
        history.append({"gapPx": gaps[index], "left": left[:], "right": right[:]})
        merged[index:index + 2] = [[left[0], right[1]]]
    return merged, history


def edge_alpha_counts(alpha: np.ndarray) -> dict[str, int]:
    return {
        "top": int(np.count_nonzero(alpha[0, :])),
        "right": int(np.count_nonzero(alpha[:, -1])),
        "bottom": int(np.count_nonzero(alpha[-1, :])),
        "left": int(np.count_nonzero(alpha[:, 0])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--names", required=True, help="Comma-separated output stems in left-to-right order")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--alpha-threshold", type=int, default=24)
    parser.add_argument("--min-column-pixels", type=int, default=2)
    parser.add_argument("--padding", type=int, default=40)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = Path(args.image).resolve()
    out_dir = Path(args.out_dir).resolve()
    report_path = Path(args.report).resolve()
    names = [value.strip() for value in args.names.split(",") if value.strip()]
    if args.count < 1 or len(names) != args.count:
        parser.error("--count must be positive and equal the number of --names")
    if not 0 <= args.alpha_threshold <= 255 or args.min_column_pixels < 1:
        parser.error("invalid alpha threshold or minimum column pixel count")

    image = Image.open(source).convert("RGBA")
    pixels = np.asarray(image)
    alpha = pixels[:, :, 3]
    occupied = (alpha >= args.alpha_threshold).sum(axis=0) >= args.min_column_pixels
    raw_runs = runs_from_mask(occupied)
    status = "pass"
    errors = []
    if len(raw_runs) < args.count:
        status = "blocked"
        errors.append(f"detected only {len(raw_runs)} alpha runs for {args.count} requested sprites")
        clusters, merge_history = raw_runs, []
    else:
        clusters, merge_history = merge_to_count(raw_runs, args.count)
    if len(clusters) != args.count:
        status = "blocked"

    outputs = []
    out_dir.mkdir(parents=True, exist_ok=True)
    if status == "pass":
        for name, (x0, x1) in zip(names, clusters):
            cluster_alpha = alpha[:, x0:x1 + 1]
            ys, xs = np.nonzero(cluster_alpha >= args.alpha_threshold)
            if not len(xs):
                errors.append(f"cluster {name} is empty")
                status = "blocked"
                continue
            bbox = {
                "x": int(x0 + xs.min()),
                "y": int(ys.min()),
                "w": int(xs.max() - xs.min() + 1),
                "h": int(ys.max() - ys.min() + 1),
            }
            crop = image.crop((bbox["x"], bbox["y"], bbox["x"] + bbox["w"], bbox["y"] + bbox["h"]))
            side = max(crop.width, crop.height) + 2 * args.padding
            canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            canvas.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
            if side != args.size:
                canvas = canvas.resize((args.size, args.size), Image.Resampling.LANCZOS)
            edge_counts = edge_alpha_counts(np.asarray(canvas)[:, :, 3])
            if any(edge_counts.values()):
                status = "blocked"
                errors.append(f"{name} has non-transparent cut edge")
            output = out_dir / f"{name}.png"
            if output.exists() and not args.force:
                parser.error(f"refusing to overwrite {output}; pass --force")
            canvas.save(output, optimize=True)
            outputs.append({
                "name": name,
                "path": str(output),
                "sourceBbox": bbox,
                "edgeAlphaPixels": edge_counts,
                "sha256": sha256(output),
            })

    report = {
        "schemaVersion": "sprite-split/v1",
        "status": status,
        "source": {"path": str(source), "sha256": sha256(source), "width": image.width, "height": image.height},
        "settings": {
            "expectedCount": args.count,
            "alphaThreshold": args.alpha_threshold,
            "minColumnPixels": args.min_column_pixels,
            "padding": args.padding,
            "outputSize": args.size,
        },
        "rawRuns": raw_runs,
        "mergeHistory": merge_history,
        "clusters": clusters,
        "outputs": outputs,
        "errors": errors,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
