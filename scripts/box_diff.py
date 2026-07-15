#!/usr/bin/env python3
"""box_diff: compare manifest (expected boxes from mockup) vs DOMRects (actual).

The primary repair signal. A pixel heatmap says WHERE it differs; a box diff
says WHICH element and BY HOW MUCH — directly translatable to a CSS fix.

CRITICAL — CASCADE RULE: layout errors propagate downward in normal flow.
A dy=+24 on a mid-page element is usually caused by a section ABOVE it.
Therefore the report is sorted in document order and you must fix ONLY the
FIRST failing item, re-render, and re-diff. Most downstream failures will
disappear on their own. Never patch every delta at once.

Usage:
  python3 box_diff.py manifest.json rects.json [--out report.json]
                      [--section-relative]

Manifest elements need: id, el (data-el value), bbox {x,y,w,h}, priority.
Tolerances default by priority (px): critical 4/4/8/8, high 8/8/12/12,
normal 16/16/24/24, low 32/32/48/48 — override per element via "tolerance".

--section-relative (multi-frame comp sets): elements whose `sourceImage`
maps to a `section-comp` reference frame are compared in FRAME-LOCAL
coordinates — the rendered y of their section root is subtracted from the
actual rect before diffing. Section roots themselves are compared on
width/height only. The height check is ONE-SIDED (density contract as a
floor): a section rendering shorter than its frame has collapsed and
fails; a section rendering TALLER passes — translating a 16:9 frame into
a taller section with breathing whitespace is correct page composition,
not an error. Their x/y belong to the page composition, no frame owns
them.

Provenance guard: elements tagged `bboxSource: implementation-derived`
whose qaPriority is fv-critical/section-critical are counted and warned
about — a manifest back-filled from your own render makes this diff a
tautology, not evidence.
"""
import argparse
import json
import math
import sys

DEFAULT_TOL = {
    "critical": {"x": 4, "y": 4, "w": 8, "h": 8},
    "high": {"x": 8, "y": 8, "w": 12, "h": 12},
    "normal": {"x": 16, "y": 16, "w": 24, "h": 24},
    "low": {"x": 32, "y": 32, "w": 48, "h": 48},
}


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def valid_bbox(value):
    return (isinstance(value, dict) and
            all(key in value and valid_number(value[key]) for key in ("x", "y", "w", "h")) and
            value["w"] > 0 and value["h"] > 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest")
    ap.add_argument("rects")
    ap.add_argument("--out")
    ap.add_argument("--section-relative", action="store_true",
                    help="multi-frame comp sets: compare sourceImage elements "
                         "in frame-local coords (section root y subtracted); "
                         "section roots compared on w/h only")
    args = ap.parse_args()

    manifest = json.load(open(args.manifest))
    rects_data = json.load(open(args.rects))
    actual = {r["el"]: r for r in rects_data.get("rects", [])}

    frame_section = {}
    if args.section_relative:
        for ri in manifest.get("referenceImages", []):
            if ri.get("use") == "section-comp" and ri.get("section"):
                frame_section[ri["path"]] = ri["section"]

    raw_elements = manifest.get("elements", [])
    invalid_manifest = []
    if not isinstance(raw_elements, list):
        invalid_manifest.append({
            "path": "elements",
            "message": "manifest.elements must be an array",
            "actualType": type(raw_elements).__name__,
        })
        raw_elements = []
    elements = []
    for index, element in enumerate(raw_elements):
        if not isinstance(element, dict):
            invalid_manifest.append({
                "path": f"elements[{index}]",
                "message": "element must be an object",
                "actualType": type(element).__name__,
            })
            continue
        bbox = element.get("bbox")
        if not valid_bbox(bbox):
            invalid_manifest.append({
                "path": f"elements[{index}].bbox",
                "id": element.get("id"),
                "message": "bbox must be an object {x,y,w,h} with finite numbers and positive w/h; arrays are invalid",
                "actualType": type(bbox).__name__,
                "value": bbox,
            })
            continue
        tolerance = element.get("tolerance")
        if tolerance is not None and not isinstance(tolerance, dict):
            invalid_manifest.append({
                "path": f"elements[{index}].tolerance",
                "id": element.get("id"),
                "message": "tolerance must be an object keyed by x/y/w/h",
                "actualType": type(tolerance).__name__,
            })
            continue
        elements.append(element)

    if invalid_manifest:
        report = {
            "status": "blocked",
            "mode": "section-relative" if args.section_relative else "page-global",
            "summary": {
                "total": 0,
                "pass": 0,
                "fail": 0,
                "missing_in_dom": [],
                "pass_rate": None,
                "implementation_derived_critical": [],
                "y_waived_recomposition": 0,
                "tolerance_overrides": 0,
                "invalid_manifest": len(invalid_manifest),
            },
            "invalidManifest": invalid_manifest,
            "first_fix": {
                "id": "manifest-contract",
                "instruction": "Run contract_doctor.py and repair the manifest shape before box diff; do not tune CSS against an invalid bbox contract.",
            },
            "items": [],
        }
        text = json.dumps(report, indent=2)
        if args.out:
            with open(args.out, "w") as handle:
                handle.write(text + "\n")
            print(f"box_diff: blocked by {len(invalid_manifest)} invalid manifest row(s)")
            print(f"wrote {args.out}")
        else:
            print(text)
        sys.exit(2)

    def tolerance_for(el):
        return tolerance_detail_for(el)["value"]

    def tolerance_detail_for(el):
        pri = el.get("priority", "normal")
        default = DEFAULT_TOL.get(pri, DEFAULT_TOL["normal"])
        override = {k: v for k, v in (el.get("tolerance") or {}).items()
                    if k in ("x", "y", "w", "h")}
        value = {**default, **override}
        return {
            "value": value,
            "source": "manifest" if override else "default",
            "default": default,
            "override": override,
            "overridden_axes": sorted(override),
        }

    section_roots = {}
    if args.section_relative:
        for el in elements:
            frame = el.get("sourceImage", "")
            sec_el = frame_section.get(frame)
            if sec_el and el.get("el") == sec_el and el.get("bbox"):
                section_roots[(frame, sec_el)] = {
                    "element": el,
                    "actual": actual.get(sec_el),
                    "tolerance": tolerance_for(el),
                }

    items, missing, tainted = [], [], []
    y_waived_recomposition = 0
    for el in elements:
        eid, key = el.get("id", el.get("el")), el.get("el")
        exp = el.get("bbox")
        if not key or not exp:
            continue
        pri = el.get("priority", "normal")
        qa = el.get("qaPriority")
        if el.get("bboxSource") == "implementation-derived" and qa in ("fv-critical", "section-critical"):
            tainted.append({"id": eid, "el": key, "qaPriority": qa})
        tol_detail = tolerance_detail_for(el)
        tol = tol_detail["value"]
        act = actual.get(key)
        if act is None:
            missing.append({"id": eid, "el": key, "priority": pri})
            continue

        sec_el = frame_section.get(el.get("sourceImage", ""))
        viewport_global = (
            el.get("placementScope") in ("viewport-fixed", "viewport-edge") or
            el.get("positioning") in ("fixed", "sticky")
        )
        axes, coord_space = ("x", "y", "w", "h"), "page"
        act_cmp = {k: act[k] for k in ("x", "y", "w", "h")}
        page_exp = dict(exp)
        if sec_el:
            if key == sec_el:
                # section root: w/h only (h vs frame height = density contract)
                axes, coord_space = ("w", "h"), "section-root"
                page_exp = {"x": act["x"], "y": act["y"], "w": exp["w"], "h": exp["h"]}
            elif viewport_global:
                # Global chrome can be measured in the FV comp while living
                # outside the section in the DOM. Its rect is viewport/page
                # based; subtracting the section root creates a fake y miss.
                coord_space = "viewport-global"
                sec_act = actual.get(sec_el)
                page_exp = {**exp, "y": exp["y"] + (sec_act["y"] if sec_act else 0)}
            else:
                sec_act = actual.get(sec_el)
                if sec_act is None:
                    missing.append({"id": eid, "el": key, "priority": pri,
                                    "reason": f"section root '{sec_el}' missing in DOM"})
                    continue
                coord_space = "frame-local"
                act_cmp = {"x": act["x"], "y": round(act["y"] - sec_act["y"], 1),
                           "w": act["w"], "h": act["h"]}
                page_exp = {**exp, "y": exp["y"] + sec_act["y"]}

        d = {k: round(act_cmp[k] - exp[k], 1) for k in axes}
        if coord_space == "section-root":
            # density contract is a floor: only a collapse (shorter than
            # the frame) fails; a taller, breathing section is correct.
            fails = [k for k in axes
                     if (d[k] < -tol[k] if k == "h" else abs(d[k]) > tol[k])]
        else:
            fails = [k for k in axes if abs(d[k]) > tol[k]]
        y_waived = False
        if (coord_space == "frame-local" and "y" in fails and
                qa != "fv-critical"):
            root = section_roots.get((el.get("sourceImage", ""), sec_el))
            root_el = root["element"] if root else None
            root_act = root["actual"] if root else None
            root_exp = root_el.get("bbox") if root_el else None
            root_tol = root["tolerance"] if root else None
            if root_act and root_exp and root_act["h"] - root_exp["h"] > root_tol["h"]:
                fails = [k for k in fails if k != "y"]
                y_waived = True
                y_waived_recomposition += 1
        items.append({
            "id": eid, "el": key, "priority": pri,
            "expected": exp,
            "actual": act_cmp,
            "delta": d, "tolerance": tol,
            "toleranceSource": tol_detail["source"],
            "toleranceDefault": tol_detail["default"],
            "toleranceOverride": tol_detail["override"],
            "toleranceOverriddenAxes": tol_detail["overridden_axes"],
            "coordSpace": coord_space,
            "pass": not fails, "failed_axes": fails,
            "_page_expected": page_exp,
            "rendered_font": {k: act[k] for k in ("fontSize", "lineHeight", "fontFamily") if k in act},
            **({"y_waived_recomposition": True} if y_waived else {}),
        })

    items.sort(key=lambda i: (i["_page_expected"]["y"], i["_page_expected"]["x"]))  # document order
    fails = [i for i in items if not i["pass"]]

    # first_fix: first failure in document order, but if it CONTAINS later
    # failing elements it is a container whose error originates inside —
    # drill down to the first failing leaf within it.
    def contains(outer, inner):
        o, n = outer["_page_expected"], inner["_page_expected"]
        return (o["x"] <= n["x"] + 1 and o["y"] <= n["y"] + 1 and
                o["x"] + o["w"] >= n["x"] + n["w"] - 1 and
                o["y"] + o["h"] >= n["y"] + n["h"] - 1 and
                (o["w"] > n["w"] or o["h"] > n["h"]))

    def density_floor_failure(item):
        return (item.get("coordSpace") == "section-root" and
                "h" in item.get("failed_axes", []) and
                item.get("delta", {}).get("h", 0) < 0)

    first, chain = (fails[0] if fails else None), []
    while first is not None:
        if density_floor_failure(first):
            break
        inner = next((f for f in fails if f is not first and contains(first, f)), None)
        if inner is None:
            break
        chain.append(first["id"])
        first = inner

    for i in items:
        i["pageExpected"] = i.pop("_page_expected")

    report = {
        "mode": "section-relative" if args.section_relative else "page-global",
        "summary": {
            "total": len(items), "pass": len(items) - len(fails), "fail": len(fails),
            "missing_in_dom": missing,
            "pass_rate": round((len(items) - len(fails)) / len(items), 3) if items else None,
            "implementation_derived_critical": tainted,
            "y_waived_recomposition": y_waived_recomposition,
            "tolerance_overrides": sum(1 for i in items if i.get("toleranceSource") == "manifest"),
        },
        "first_fix": None if first is None else {
            **{k: first[k] for k in ("id", "el", "delta", "failed_axes",
                                     "tolerance", "toleranceSource",
                                     "toleranceOverride", "toleranceOverriddenAxes")},
            "container_chain": chain,
            "instruction": (
                "Fix ONLY this element (first failing leaf in document order), "
                "then re-render and re-diff. Downstream deltas likely cascade from it. "
                "Diagnose the CAUSE (usually spacing/size of this or the previous block) "
                "instead of offsetting this element locally."
                + (" This is a density-floor failure: the section collapsed below "
                   "its comp frame's height. Restore type scale, vertical paddings "
                   "and whitespace rhythm; do not shrink children to make the frame fit."
                   if density_floor_failure(first) else "")
                + (" Containers in container_chain fail because of this leaf; "
                   "they should heal once it is fixed." if chain else "")
            ),
        },
        "items": items,
    }
    text = json.dumps(report, indent=2)
    if args.out:
        open(args.out, "w").write(text)

    s = report["summary"]
    print(f"box_diff: {s['pass']}/{s['total']} pass"
          + (f", {len(s['missing_in_dom'])} missing" if s["missing_in_dom"] else ""))
    if tainted:
        print(f"WARNING: {len(tainted)} fv-critical/section-critical element(s) have "
              f"bboxSource=implementation-derived — this diff is a tautology for them, "
              f"not fidelity evidence. Re-measure from the comp frames: "
              + ", ".join(t["id"] for t in tainted))
    if first:
        d = first["delta"]
        deltas = " ".join(f"d{k}={d[k]}" for k in ("x", "y", "w", "h") if k in d)
        tol_note = (
            f"tolSource={first.get('toleranceSource')}"
            + (f" overrideAxes={','.join(first.get('toleranceOverriddenAxes', []))}"
               if first.get("toleranceOverride") else "")
        )
        print(f"FIRST FIX -> {first['id']} [{first['el']}] "
              f"{deltas} (axes: {','.join(first['failed_axes'])}; {tol_note})")
    elif items:
        print("all elements within tolerance")
    if args.out:
        print(f"wrote {args.out}")
    if not args.out:
        print(text)


if __name__ == "__main__":
    main()
