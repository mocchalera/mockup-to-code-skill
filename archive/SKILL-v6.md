---
name: mockup-to-code
description: >
  Convert a static web-design mockup image (AI-generated or hand-made comp/カンプ)
  into high-fidelity HTML/CSS. Three modes: pixel-clone (measured reproduction),
  production, and hybrid (decompose an AI-generated comp — regenerate photos
  text-free, rebuild all type in HTML/CSS, reconstruct the visual language with
  a layer plan). Enforces a media-class asset policy (photo content stays
  raster — regenerated or licensed stock, never redrawn as SVG/CSS; vector
  drawing only for decorative geometry, flat UI and icon-set icons) and a
  per-block type spec (in-line scale steps, weight class, serif accents,
  letterform-matched font selection). Uses hypothesis-driven measurement (snap_bbox, profile,
  sample_color), an element manifest binding mockup regions to DOM selectors,
  a document-order box-diff repair loop, intent verification (visual-check),
  a comp-side detail inventory with a per-section review pass, and masked
  pixel diff for final QA. Review verdicts are judged on rendered pixels
  via saved comp-vs-build crop pairs (crop_pair.py), the inventory must
  account for the whole frame including the section's environment/ground,
  display lockups carry per-line box contracts, JP display fonts are
  chosen by bake-off, section scores are the minimum across
  composition/typography/palette/details axes, and OpenCV fallback is
  allowed only after a recorded failed install attempt. Also handles multi-frame comp sets
  (one reference image per section of a single page, e.g. an AI-generated
  10-image LP) with a fidelity gradient — FV near-pixel-strict, below-FV
  essence-first — plus a page composition plan (seams, connective motifs,
  whitespace rhythm) and a page-flow review so the frames become one
  scrolling LP, not stacked slides. Trigger when the user wants to code a
  design image into a web page with high visual fidelity:
  「この画像をHTML/CSSにして」「カンプをコーディングして」「デザイン画像を再現して」
  "code this mockup", "implement this design image".
---

# mockup-to-code

Reverse-engineer a static mockup image into HTML/CSS through **measurement,
not eyeballing**. You (the LLM) interpret meaning and form hypotheses; scripts
measure pixels; the browser answers with DOMRects; box diff tells you exactly
what to fix.

## Fidelity modes (decide first, record in manifest `mode`)

| mode | goal | primary signal | typical input |
| --- | --- | --- | --- |
| `pixel-clone` | reproduce ONE authoritative comp exactly | box diff → masked pixel diff | hand-made comp, existing-site screenshot |
| `production` | clean production code informed by the comp | box diff on key elements, relaxed tolerances | comp + a real content/CMS reality |
| `hybrid` | **reconstruct the comp's visual language** | layer plan + box diff + visual-check + section review (FV gate + detail pass) | **AI-generated comp** (the usual case) |

**Hybrid is the default for AI-generated comps**, because in them photo, type
and decoration are fused into one raster: cropping and pixel-matching cannot
reach quality. Instead you *decompose*: photos are regenerated/extracted
text-free, ALL type is rebuilt in HTML/CSS, and stacking is designed
explicitly. Success is not bbox equality — it is judged on: FV impression,
typographic hierarchy, how the photo is used (background layer vs cheap
card), correct layering, no responsive breakage, and whether the comp's
small design devices (accent underlines, tick marks, eyebrow rules,
watermark type, frame offsets, hand-drawn strokes) survived — the detail
pass. Field data: a build with the right layout but the devices dropped
scores ~4–5/10 against its comp; the devices are half the perceived quality.

**Multiple reference images — decide which of two cases you are in:**

- **Mood boards / alt comps** are *visual-language sources*, not reproduction
  targets: sample colors/type-treatments/layering ideas from them, register
  them in the manifest `referenceImages` with `use: "visual-language"`, and
  reproduce only the one primary comp's structure.
- **A sectioned comp set** — ref-01…ref-NN where each image IS the comp for
  one section of a single page (the usual shape of an AI-generated LP) — is
  **multi-frame hybrid**. Every frame is the primary comp *for its section*:
  register each with `use: "section-comp"` + `section` (the section's
  `data-el`), normalize ALL frames to the same width (Phase 0), and set
  `sourceImage` on each element so its bbox is unambiguous (frame-local
  coordinates). QA is scoped per frame, not page-global: run the full
  box-diff loop on the FV frame (there frame and page coordinates coincide);
  for other sections box-diff `section-critical` elements on
  width/height/within-section offsets only — cross-section y positions come
  from your page composition, no frame owns them (`box_diff.py
  --section-relative` does this coordinate transform for you) — and let
  visual-check plus the Phase 7 section review carry the rest. Each frame's
  height at the canonical width is the **density floor** for its section: a
  section that renders at 60% of its frame's height has collapsed (cramped
  type, starved whitespace) no matter how the boxes inside "fit". Taller
  than the frame is NOT a failure — see the fidelity gradient below.

  **The fidelity gradient (multi-frame):** the frames are separately
  generated 16:9 slides — their letterbox composition, per-frame full-bleed
  framing and uniform height are *generator artifacts*, not design
  decisions. Reproduce accordingly:

  - **FV frame: near-pixel-strict.** The first view is judged like a
    poster comp — composition, type scale, photo treatment, device set all
    at full box-diff depth.
  - **Every frame below: essence-first, flow-first.** Reproduce the
    frame's *essence* (Phase 1 essence ledger: its core statement, its
    distinctive devices, its palette/mood) and its internal hierarchy —
    but the section's height, outer margins and seam to its neighbors
    belong to the **page composition plan (Phase 4.5)**, not to the frame.
    A frame crammed into 810px of 16:9 usually wants to breathe taller on
    a scrolling page. Spending loop iterations matching a below-FV frame's
    letterbox geometry while the page reads as stacked slides is the
    characteristic multi-frame failure: half-faithful everywhere,
    compelling nowhere.

### Hybrid multi-frame — minimum artifact checklist

The rest of this document is the reference; THIS is what a run must
produce, in order. A missing artifact means the phase was skipped, not
"streamlined":

1. `work/mockups/` — every frame normalized to one width (Phase 0)
2. `reports/hypotheses.md` — per frame: essence ledger, detail inventory
   **ending in the environment/ground row**, **type spec** with per-line
   decomposition, font bake-off record (Phase 1)
3. `work/manifest.json` — comp-measured FV + `section-critical` bboxes
   incl. per-line heading entries; media class + asset strategy per
   visual (Phases 2–3)
4. Layer-plan fields in the manifest + page composition plan block
   (Phases 4 / 4.5)
5. Desktop AND mobile render from the FIRST loop iteration (Phase 6)
6. `box_diff.py --section-relative` report (Phase 6)
7. `visual-check.mjs --viewports 1440x900,390x844` (Phase 7)
8. `work/reports/crops/` — crop-pair evidence (`crop_pair.py`): FV type
   lockup, every detail-inventory verdict, every adopted photo asset
   (Phase 7)
9. `reports/section-review.md` — FV gate, per-section detail disposition
   with crop-pair paths, palette hex pairs, axis-min scores, additions
   table, page-flow review (Phase 7)
10. FV-frame masked pixel diff (Phase 8 — skippable only with a recorded
    failed OpenCV install attempt)

## Effort scoping (which phases run at full depth)

The full pipeline (hypothesis → measurement → manifest → layer plan → box
loop → intent QA → pixel QA) is the *pixel-clone* path. Running every phase
at full depth on a whole LP is waste; scope by mode:

| phase | pixel-clone | production | hybrid (incl. multi-frame LP) |
| --- | --- | --- | --- |
| 0 normalize | required | required | required (every frame) |
| 1–2 hypothesize + measure | every important element | key elements | FV + `section-critical`; `estimated` OK below that |
| 3 manifest | full | full | full — it is the QA contract; bboxes may be sparse |
| 4 layer plan | where overlap exists | where overlap exists | required for FV + every overlap |
| 4.5 page composition plan | — | — | **required for multi-frame** |
| 6 box loop | full, all priorities | critical + high | FV frame full; elsewhere `section-critical` only |
| 7 visual-check + section review (FV gate) | recommended | required | **required — this is the hybrid bar** |
| 8 pixel diff | required | optional | **FV frame required** (photo+text masked); below-FV optional |

When a deadline forces cuts, cut *measurement depth* (more `estimated`
bboxes on `normal`/`low` elements) — never the Phase 7 evidence and never
the asset-contamination gate (principle 6).

## Core principles (non-negotiable)

1. **Do not estimate when you can measure.** Vision-only px values are allowed
   only for `priority: low` elements, and must be tagged `bboxSource: estimated`.
2. **Do not measure globally when you can measure locally.** Form a hypothesis
   first ("card grid around y=760–1240"), then measure that ROI.
3. **Do not diff pixels when you can diff boxes.** Box diff is the repair
   signal; pixel diff is final QA only.
4. **Do not patch CSS that has no manifest mapping.** Every repaired element
   carries a `data-el` attribute bound in the manifest.
5. **Never ship generated glyphs — but DO chase the typography.** Text
   content lives in HTML with a real frozen font; compare text by
   bbox/line-count, mask it in pixel diff. What you *must* reproduce in CSS is
   the comp's typographic treatment: size, tightness (palt/negative tracking),
   leading, tilt, outline, band, vertical writing, whitespace. In FV/hero/
   poster sections this treatment IS the perceived quality
   (`templates/poster-typography.css` has the patterns). The Phase 1
   **type spec** decomposes this treatment — in-line scale steps, weight
   class, serif accents, per-word markers — BEFORE fonts are chosen;
   comps craft their typography deliberately, and a rebuild that flattens
   it is a drop even when the bbox passes.
6. **Never ship a photo with baked-in text or design elements — no
   exceptions, no concealment.** If a crop is contaminated, regenerate it
   text-free (or get a layered source) and rebuild the text in HTML on top.
   If regeneration is unavailable or cannot honestly match, ship an explicit
   `placeholder` and ask the user for the real asset (Phase 3 asset policy).
   "It's small background text", "a gradient will hide it", "inpaint later"
   are not options. Re-run the contamination check on every crop you ship —
   residual sign/logo/UI text in `work/assets/` is a completion blocker.
7. **Decide layering before styling.** For FV and any overlapping elements,
   the layer plan (what sits on what, and why) comes before CSS.
8. **Fix the FIRST failing element in document order, then re-render.**
   Layout errors cascade downward — one upstream fix clears many downstream
   deltas. Never patch all deltas in one pass.
9. **Measure the comp before you implement.** In hybrid, FV and
   `section-critical` bboxes are measured from the comp frames BEFORE any
   CSS exists. A manifest back-filled from your own render turns box diff
   into a tautology — 29/29 pass with zero information (this has happened).
   Numbers read back from DOMRects are tagged
   `bboxSource: implementation-derived` and never count as fidelity
   evidence for fv-critical / section-critical elements.
10. **The comp's quality lives in its details.** Every visible device —
    accent underline, tick mark, eyebrow label + rule, letterspacing
    treatment, hand-drawn stroke, watermark/oversized type, photo frame
    offset, tilt, badge, speech bubble — is enumerated in the Phase 1
    detail inventory and dispositioned (present / adapted / waived-with-
    reason) in the Phase 7 section review. `decorative`/`detail` priority
    exempts an element from the box-diff loop, never from existing.
11. **Reproduce the motif, not a category stand-in.** A device's
    *specific content* is the device: an oversized outline 「止」 is that
    kanji (chosen for meaning), not "some outline shapes"; a workflow
    card is its icon + label + status chip, not a bare labeled box; a
    dashboard mock is its donut/number/checklist, not an abstract blur.
    Substituting a generic abstraction where the comp has a specific
    motif is a **drop**, and in the section review it is verdict
    `missing` — never `present`, never `adapted`. Field data: a build
    whose reviews said "present/adapted" on such substitutions
    self-scored 8/10 and was user-scored 5/10.
12. **Additions never occlude the comp.** Elements the comp does not
    have (handoff requirements, CTA ribbons, nav) get their own layer-
    plan entry with `mustNotCover` listing every comp element they could
    touch. An addition that covers or crops a comp device is a
    completion blocker — you may not self-waive it as "acceptable"; make
    room by recomposing, or ask the user.
13. **A visual's medium is part of the design — photo-class content
    stays photographic.** Classify every visual in Phase 1 by media
    class: `photo` (people, places, objects with real lighting),
    `illustration`, `ui-mock` (flat app UI), `icon`,
    `decorative-geometry` (lines, bands, blobs, gradient fields). The
    build must satisfy each visual **in the same class**. Drawing in
    SVG/CSS is legitimate ONLY for decorative geometry, flat UI mocks
    and icons. A photo-class visual rebuilt as vector shapes, a flat
    avatar, or a CSS "figure" is a **media-class drop**: verdict
    `missing` (never `adapted`), FV gate fail, section score capped at
    4 — one such substitution reads as design collapse no matter how
    clean everything around it is. Rendering your own HTML/CSS/SVG to
    PNG does not make it a `generated` asset for photo-class visuals;
    "generator" in the asset policy means a raster image model
    (imagegen, `cockpit gen-image`, …) or licensed stock. No generator
    available ≠ permission to vectorize — that case is `placeholder` +
    ask. Field data: a build that shipped a vector avatar for a
    photographic hero subject self-scored 7.8/10; the user scored it 3/10.
14. **Verdicts are judged on rendered pixels, from saved crop pairs.**
    A section-review verdict or FV-gate checkbox backed by code
    inspection ("the DOM has a text-stroke", "the CSS sets 900") or by
    memory of what you built is not a judgment — it is a hope. Every
    detail-disposition row and every FV typography check cites a
    crop-pair file (`scripts/crop_pair.py`, comp region vs the same
    region of the build render) under `work/reports/crops/`. Field data:
    a run graded an outline 「止」 `present` from its CSS while the
    render showed broken rectangles.
15. **Account for the whole frame — the ground is a device.** Frame
    area no inventory row names is where drops hide. Per frame, the
    detail inventory ends with a row for the section's *environment
    itself* — scene photo, glass mega-panel, colored field, gradient
    wash — with its media class. A photographic desk-scene environment
    replaced by flat white is a media-class drop (verdict `missing`,
    section capped at 4) exactly like a vectorized avatar. Field data: a
    run dropped an entire desk-scene photo and its review never
    mentioned it, because no row had ever named it; the section
    self-scored 7.5.

## Setup (once per environment)

```bash
bash scripts/setup_env.sh
```

Never hard-fails without telling you the alternative. It reports two axes:

- **browser** — discovery order: `CHROME_PATH` > playwright-managed Chromium >
  system Chrome/Chromium/Edge (macOS `/Applications/Google Chrome.app/…`
  works out of the box) > playwright download. `render.mjs` and
  `visual-check.mjs` use the same discovery.
- **python** — OpenCV+numpy = full functionality. Pillow+numpy = fallback:
  `normalize_image` / `sample_color` / `crop_asset` still work;
  `snap_bbox`, `profile`, `pixel_diff` and the crop contamination check
  need OpenCV (then rely on visual inspection + visual-check instead).

### Recommended Python environment for full measurement

For highest-fidelity measurement, prefer a project-local virtual environment
over machine-global Python installs. OpenCV is required for `snap_bbox`,
`profile`, `pixel_diff`, and crop contamination checks.

```bash
cd /path/to/project
python3.13 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install opencv-python numpy pillow
```

Verify:

```bash
.venv/bin/python - <<'PY'
import cv2, numpy, PIL
print("cv2", cv2.__version__)
print("numpy", numpy.__version__)
print("Pillow", PIL.__version__)
PY
```

Use this Python when running measurement scripts:

```bash
.venv/bin/python scripts/snap_bbox.py ...
.venv/bin/python scripts/pixel_diff.py ...
```

Add `.venv/` to `.gitignore`. Avoid machine-global installs unless the user
explicitly asks for them.

### No-OpenCV fallback (dependency-gated environments)

**Fallback must be earned, not assumed.** `setup_env.sh` reporting
"Pillow fallback" is a diagnosis, not a permission. Before accepting
fallback, ATTEMPT the venv install above (`pip install --dry-run
opencv-python` first costs seconds). Fallback mode is legitimate only
when (a) the install attempt actually failed — paste the command and its
error into the completion report — or (b) the user/environment
explicitly forbids installs. Field data: a run accepted fallback on a
machine where the dry-run resolved an arm64 wheel; every downstream
weakness of that build (hand-measured boxes, no pixel diff, no
contamination check, unverified typography) traced back to that one
unforced choice.

When the install genuinely cannot happen, do not stall and do not
silently degrade — follow this policy:

- **Measurement**: `snap_bbox`/`profile` are unavailable. Measure FV and
  `section-critical` bboxes by reading coordinates off the normalized
  frame yourself (zoom in, count against the 1440px space) and tag them
  `bboxSource: normalized`; values from a handoff/spec doc are
  `bboxSource: user`. Both are acceptable *for measurement* in this mode —
  principle 9 still applies: never back-fill from your own DOMRects.
- **Widen tolerances one step** for hand-measured elements; hand reads
  are ±5–10px at best. Concretely: keep `priority` (it still ranks
  repair order) and set an explicit `tolerance` instead — critical ±4 →
  ±8, high ±8 → ±16, normal ±16 → ±24. Example manifest entry in this
  mode:

  ```json
  { "id": "hero-heading", "el": "hero-heading",
    "priority": "critical", "qaPriority": "fv-critical",
    "bbox": [64, 176, 690, 320], "bboxSource": "normalized",
    "tolerance": { "x": 8, "y": 8, "w": 8, "h": 8 },
    "notes": "hand-measured off the normalized frame (no OpenCV)" }
  ```
- **Normalization/cropping**: use OS tools (`sips` on macOS, ImageMagick)
  for resize; use Playwright clip screenshots (scroll the section into
  view first — clip is viewport-relative) instead of `crop_asset.py` for
  section strips.
- **Contamination check** (principle 6) has no script: eyeball every
  shipped crop at ≥200% zoom, corners and edges included, and say so.
- **Report it**: the completion report must state that measurement ran in
  fallback mode, which elements are hand-measured, and that pixel-level
  claims are correspondingly weaker. "29/29 box diff" over hand-measured
  boxes is a weaker claim than the same number over snapped boxes.

### Rendering environments

`render.mjs`/`visual-check.mjs` (headless, file-based evidence) are the
default. When they cannot run, or when you are *iterating live* on a design,
use whichever of these exists — same checks, different transport:

- **MCP Playwright** (`mcp__playwright_*` / `mcp__plugin_playwright_*`):
  navigate to the file/dev-server, `browser_resize` per viewport,
  `browser_evaluate` the same DOMRect/overlap probes, screenshot.
- **In-app preview / Chrome extension**: best for look-and-tune loops on the
  FV — adjust CSS while watching, then run the file-based loop once at the
  end to produce evidence.
- Whatever the transport, the *artifacts* stay the same: rects → box-report,
  visual-check.json, screenshots in `work/reports/`.

## Workspace layout

```
work/
  mockup.png        # normalized mockup (canonical coordinate space)
  manifest.json     # element manifest (schemas/element_manifest.schema.json)
  site/index.html   # implementation
  site/css/…
  assets/           # cropped AND generated assets
  reports/          # hypotheses.md, rects.json, box-report.json,
                    # visual-check.json, section-review.md, sections/,
                    # pixel-report.json, diff.png, imagegen-prompt.md
```

## Phase 0 — Normalize the coordinate space

```bash
python3 scripts/normalize_image.py raw.png --width 1440 --out work/mockup.png
```

Everything downstream (your hypotheses, measurements, manifest, DOMRects)
lives in this one space. Reason: your vision sees a *downscaled* copy of large
images — talking in two coordinate spaces silently corrupts every number.

Ask the user (if unknown): target viewport width, fidelity mode
(**pixel-clone / production / hybrid** — hybrid for AI-generated comps),
available fonts, whether layered source assets exist (background-only,
photos-only, text-free versions — these beat cropping every time), and
whether an image generator (imagegen, `cockpit gen-image` etc.) is
available for regenerating contaminated photos, and whether licensed
stock photography is acceptable when generation is unavailable or cannot
honestly match.

## Phase 1 — Hypotheses (your job)

Look at `work/mockup.png` and write down, per section: role (header / hero /
cards / CTA / footer…), approximate bboxes of important elements, what is the
**design's core** (the thing that must not be compromised — e.g. oversized
heading overlapping the photo), and an asset strategy guess per visual
(html-text / css / svg / crop-asset / replace / generated).

Record it in `work/reports/hypotheses.md` (start from
`templates/hypotheses.md`) — **required in hybrid**; the Phase 7 section
review checks the build against this file. Per section it holds: role,
design core, layout hypothesis, the **display-type scale ratio** (tallest
glyph height ÷ frame height), the asset plan, and the **detail inventory**:
every small design device you can see — accent underlines / hand-drawn
strokes, tick marks, eyebrow labels + rule lines, letterspaced EN captions,
watermark / oversized cropped type, photo frame offsets & accent borders,
tilts, speech bubbles, badges, shadow/radius language, gradient veils,
glass/emboss surface layers, inset section frames, brand lockups,
in-photo UI content (dashboard numbers, status chips) that must be
rebuilt as HTML overlays. Hunt them deliberately: zoom into each frame
and sweep corners, under-headings, card edges, photo edges — AI comps
hide half their charm below 100% zoom, and a device you never listed is a
device you will silently drop.

Three granularity rules keep the inventory honest:

- **Record the content, not the category** (principle 11). Write "outline
  kanji 「止」, ~560px, upper-left, cropped by frame edge", not "oversized
  outline glyph". Write the actual icon subjects, chip texts, numbers.
  The category survives a rewrite; the content is what gets dropped.
- **Open up composite devices.** A card/panel gets one row per internal
  part that carries design (icon, label, status chip, connector, rule) —
  one row saying "workflow cards" hides three drops. If a row's plan says
  "HTML card", ask what's *inside* it in the comp and list that too.
- **Account for the ground (principle 15).** The last row per frame is
  the section's environment itself — the scene photo the content sits
  in, the glass mega-panel, the colored field, the gradient wash — with
  its media class. No row for the background is how an entire desk-scene
  photo vanishes from a build without any verdict ever being recorded.
  Sweep the frame once more asking "what carries the remaining area?" —
  every region belongs to some row or to an explicitly named plain
  ground.

**Type spec (per display-text block — heading, lead, price, dates, big
labels; required in hybrid):** the comp's typography is *designed*;
decompose it before any font is chosen. Record per block in
hypotheses.md:

- **Letterform class & weight** — gothic / mincho(serif) / rounded /
  display; weight class (a 900 display gothic and a 700 body gothic are
  different animals); stroke contrast.
- **In-line scale steps** — JP display headings routinely set kana /
  particles smaller than the kanji (「社長自らが」 with 「らが」 at
  ~0.6×; measure the ratio off the comp) and numbers larger than their
  unit suffixes (「55,000円」, dates vs weekday labels). A flat
  single-size rebuild of a stepped heading is a typography drop.
- **Per-word accents** — color swaps, marker bands, underline segments
  bound to *specific words*, not applied per-block.
- **Numeral / date treatment** — serif dates or prices over a gothic
  body is a common comp device; it must survive.
- **Tracking / leading class** per block (tight display vs airy caption).
- **Per-line decomposition (fv-critical lockups):** split the lockup
  into its rendered lines and accent spans, and measure each line's bbox
  in the comp (snap_bbox, or hand-measured in fallback). These become
  span-level manifest elements (`data-el="hero-title-line1"` …) — the
  only way the box loop can SEE crushed tracking or a flattened scale
  step. A single block-level bbox passes while the lockup inside it
  distorts; field data: a build hit its heading block box while negative
  tracking crushed the glyphs into near-collision, and nothing measured
  it.

**Font bake-off (JP display roles; required in hybrid):** render the
real heading copy in the 2–3 candidate fonts (one scratch HTML file),
crop-pair each against the comp glyphs (`crop_pair.py --label-b
"<candidate>"`), pick by letterform — weight, width, counters, terminal
shape — and record the pair paths + a one-line rationale in
hypotheses.md. The pick's known residual (e.g. "narrower 型 than comp")
is written down now, not discovered by the user later. JP font deltas
dominate perceived fidelity; choosing from a font's name instead of a
bake-off is how a poster comp flattens into a default-looking page.

The Phase 3 font policy consumes this spec role by role;
`templates/poster-typography.css` has the implementation patterns
(scale-step spans, serif accent role).

**Essence ledger (multi-frame, per frame):** 3–5 bullets naming what must
survive translation to the scrolling page — the frame's core statement,
its 1–2 signature devices, its palette/mood — plus, explicitly, the
**frame artifacts to translate, not copy** (16:9 letterbox height, slide-
style full-bleed edges, per-frame background resets). Phase 4.5 composes
the page from these ledgers; Phase 7 judges below-FV sections against
them.

Verify section boundaries cheaply:

```bash
python3 scripts/profile.py work/mockup.png --axis y            # section bands
python3 scripts/profile.py work/mockup.png --axis x --roi 0,760,1440,480  # container/gutters
```

## Phase 2 — Measure (scripts' job)

Refine every important bbox — your guesses are input, not truth:

```bash
python3 scripts/snap_bbox.py work/mockup.png \
  --bbox 118,178,684,158 --bbox 122,782,370,416 --radius 16
```

- Choose `--radius` larger than your expected hypothesis error (default 16;
  use 24–32 if unsure). `weak_edges` = no reliable gradient in the window:
  either your guess was off by more than the radius (re-hypothesize, or re-run
  that one box with a bigger radius) or the boundary is genuinely soft
  (accept with wider tolerance). The tool never widens silently — distant
  unrelated edges are worse than an honest "weak".
- Edges at the canvas boundary (full-bleed sections) snap to the boundary
  automatically.
- **Text bboxes are glyph-tight.** snap_bbox returns the visual glyph box,
  which is SMALLER than a DOM box (half-leading, side bearing; measured:
  ~29px top offset on an 88px heading). Implement measured text with the
  `.text-trim` utility (text-box-trim, Chrome 133+; in `templates/base.css`)
  so DOMRects match glyph boxes within ~3px. If text-box-trim is unavailable,
  compare x/width strictly but y via center with slack ≈ half-leading.
- Colors — never eyeball hex values:

```bash
python3 scripts/sample_color.py work/mockup.png --roi 0,0,1440,120 --k 4
```

Only `kind: flat` clusters become CSS tokens. `textured` = photo/gradient.

- **Display-type scale:** snap_bbox the tallest display-glyph block per
  frame and record `glyphHeight / frameHeight` in hypotheses.md. This one
  ratio is the strongest "poster vs timid" signal — a build that collapses
  it (comp 0.33 → build 0.13) reads as cheap even when every inner box
  "fits". The implemented heading must hit the comp bbox at canonical
  width; `clamp()` caps that flatten the ratio are a defect.
- Normalize measurements into intent: cluster the measured gaps into a spacing
  scale (snap values within ±3px to the nearest step; prefer the scale the
  data suggests — 4/8/10px systems all occur). Record both raw and normalized.

## Phase 3 — Element manifest (the contract)

Write `work/manifest.json` per `schemas/element_manifest.schema.json`. Every
important element gets: `id`, `el` (its `data-el` value), measured `bbox`,
`bboxSource`, `priority`, and for text: frozen real `fontFamily` +
`maskInPixelDiff: true`. Set top-level `mode`; in hybrid also set per-element
`qaPriority` (`fv-critical` / `section-critical` / `decorative`) and
`textRecreation`. In a multi-frame comp set additionally set per-element
`sourceImage` — which frame the bbox was measured in; its coordinates are
frame-local.

**Frame-local means measured against the frame image.** The section root
sits at 0,0 of its frame, and EVERY descendant's bbox is that element's
position *in the frame image itself*. `box_diff.py --section-relative`
subtracts only the section ROOT's rendered origin — so a child written in
some inner container's coordinate space (offsets relative to a shell/card
padding box, or CSS values copied from your implementation) will miss by
exactly that container's offset. Field case: Decision Card children
manifested in card-local coordinates failed box diff by the card shell's
offset until re-measured against the frame.

**In hybrid, the manifest is a pre-implementation gate:** FV +
`section-critical` bboxes must be comp-measured (`snap_bbox` / `profile` /
`normalized`) before Phase 5 starts. If you later read numbers back from
your own DOMRects (to tighten a contract), tag them
`bboxSource: implementation-derived` — they are never fidelity evidence
(principle 9).

Priorities drive tolerances (critical ±4px … low ±32px). Hero heading,
container, CTA, first-view image are `critical`. Background decoration,
shadows, grain are `low` — do not spend loop iterations on them, but list
them in the detail inventory (`qaPriority: detail`): the box loop skips
them, the Phase 7 section review does not.

**Composite-text rule:** a manifest `text.content` is checked by
visual-check as one contiguous DOM text run. Never pack a whole card's
worth of copy (label + heading + date + note) into one element's content —
DOM labels/icons between the parts break the match. Manifest the child
elements separately, each with its own short contiguous copy string; give
the parent a bbox but no `text`.

**Span-level contract for display lockups:** each rendered line of an
fv-critical heading is its own manifest element, with the per-line comp
bbox from the Phase 1 decomposition; accent spans that carry their own
treatment (scale step, color swap, marker band) get entries too. A
lockup contracted only as one block box is a lockup free to distort.

**Business-requirement additions:** an element the comp does not have
but the handoff requires (decision rail, sticky CTA, legal note) is
manifested with `addition: true` + `additionReason` naming the
requirement. Additions are excluded from fidelity evidence — they appear
in the section review's separate additions table, never as
detail-inventory verdicts — and always carry `mustNotCover`
(principle 12).

**Box-diff measurability rule:** the box loop measures real DOM boxes
(`getBoundingClientRect`). Pseudo-elements (`::before`/`::after`
underlines, rules, ticks) do not contribute — if a device's extent must
be verified by box diff, make it a real element or give the host an
explicit size; otherwise leave it `qaPriority: detail` and let the
section review judge it. Do not burn loop iterations reconciling a bbox
with decoration the DOM cannot see.

**Font policy:** pick real fonts NOW, **per text role from the Phase 1
type spec**, judged against a zoomed crop of the comp's actual glyphs —
weight, width, stroke contrast, terminal shape, counter openness — not
from a font's name. Loadable candidates (Google Fonts etc.): JP gothic —
Noto Sans JP (has 900), Zen Kaku Gothic New, M PLUS 1p/2; JP mincho —
Shippori Mincho (B1 for display), Zen Old Mincho, Noto Serif JP; latin —
Inter, Poppins, Montserrat, Playfair Display. Anti-laziness rules:

- Defaulting every role to one family at 700 is font-selection laziness.
  Display roles in AI comps usually need 800–900, and a serif/mincho
  accent role (dates, prices, decision words) is common — honor it.
- Display type never ships on a system-ui fallback: load the webfont and
  confirm it actually rendered (a fallback font shifts every glyph box —
  the box loop will show it; treat a suspiciously-off text bbox as a
  font-load failure before retuning font-size).
- Record `fontFamily` per role in the manifest plus a one-line rationale
  in hypotheses.md (what in the letterforms matched).

Generated glyphs are never shipped — but their typographic *treatment*
is faithfully rebuilt in CSS (principle 5). Font-size is found by the
render loop (render → compare bbox → adjust), never by reading pixel
heights (cap-height ≠ font-size).

**Asset policy — media class first (principle 13):** set `mediaClass`
per visual in the manifest, then use the matching path:

- `decorative-geometry` (lines, bands, blobs, gradient fields, abstract
  shapes) → CSS/SVG. This is the ONLY class where free-hand vector
  drawing is the right tool.
- `ui-mock` (flat app panels, charts, status chips that the comp itself
  presents as flat UI) → HTML/CSS rebuild with the comp's specific
  content (principle 11). This is a rebuild of *flat UI* — never a
  license to flatten photographic content into flat UI.
- `icon` → an established open icon set FIRST (Lucide, Tabler, Phosphor,
  Heroicons, Material Symbols): pick the glyph whose subject matches the
  comp's icon, inline the SVG, match the comp's stroke weight / corner
  style / size, and record `iconSource` (e.g. `"lucide:trending-up"`) in
  the manifest. Hand-drawing a bespoke path is a last resort for
  subjects no set covers — and then it reproduces the comp's specific
  subject, not a simplified stand-in.
- `photo` / `illustration` → the decision tree below. **Never SVG/CSS**,
  and never an HTML/CSS scene rendered to PNG.

**Asset policy (decision tree per photo/illustration visual):**

1. Layered / text-free source asset exists → use it (`assetStrategy` per kind).
2. **A text-free asset you already own matches → `replace`** — but judge it
   exactly like a generated candidate before adopting: same subject type,
   same mood & lighting, compatible color grade, right aspect/focal for the
   crop. Record `replacedAsset {sourcePath, matchRationale, usedBy}` in the
   manifest and re-judge it in the section review. A mismatched replacement
   (a cold corporate shot standing in for a warm casual scene) drags the
   whole section below what a good regeneration would give — when in doubt,
   regenerate; when close-but-off in tone, harmonize with a CSS `filter`
   grade and note it in `replacedAsset.grading`.
3. Clean photo region → `crop_asset.py`; check the contamination report.
4. **Contaminated crop (text or design elements baked into the photo — the
   NORM in AI comps): do NOT ship it.** Escalate in this order and record
   the outcome in the manifest:
   1. **Regenerate** an image-only asset with the available generator
      (imagegen / cockpit gen-image / …): describe the photo *without any
      text*, match subject, lighting, mood, palette and aspect; save under
      `work/assets/`. **Adoption checklist — every box, per candidate,
      before it enters `work/assets/`** (record failures and regenerate;
      don't rationalize):
      - [ ] zero text/logos/signage/readable UI anywhere (≥200% zoom sweep)
      - [ ] subject type & identity match the comp (age, build, wardrobe;
            faces are the highest bar — "different person" fails)
      - [ ] mood & lighting match (warm/cool, high-key/low-key, candid/formal)
      - [ ] color grade compatible with the section palette
      - [ ] aspect & focal placement fit the manifest bbox and crop
      - [ ] the layer plan's empty zones are actually empty (copy space
            where HTML type will sit; face/key detail clear of headings &
            CTA per `mustNotCover`)
      - [ ] in-photo props that carry design (dashboard content, notebook
            branding) are either absent or planned as HTML overlays
      Set `assetStrategy: "generated"` + `generatedAsset {prompt,
      sourceImage, workspacePath, generator, usedBy}`, and save the prompt
      to `work/reports/imagegen-prompt.md`. Record the per-candidate
      checklist verdicts in `work/reports/photo-asset-review.md` (start
      from `templates/photo-asset-review.md`) — adopted AND rejected
      candidates, each with its failing box. **Prompt + source + saved path
      + where used = required evidence.** The generator must be a raster
      image model — rendering your own HTML/CSS/SVG to PNG is not
      generation for photo-class visuals (principle 13).
   2. **Licensed stock photo** (Unsplash / Pexels / a stock account the
      user holds) when no raster generator is available, or when
      generation cannot honestly match — faces are the highest bar.
      Judge candidates with the same adoption checklist above; adopt as
      `assetStrategy: "replace"` with `replacedAsset {sourcePath: URL/id,
      license, matchRationale, usedBy}`. Text/logos/signage inside a
      stock photo are contamination like anywhere else.
   3. **Placeholder + ask.** If neither generation nor stock can honestly
      match (a different person's face is worse than a neutral block),
      place an explicit placeholder — a solid/gradient block or
      clearly-labeled stand-in sized by the manifest bbox, never a
      blurred or overlay-masked copy of the contaminated crop, and
      **never a vector/illustration redraw of the photo subject**: a
      labeled gray block is honest and reviewable; a flat avatar
      pretending to be the photo is a media-class drop that caps the
      section at 4 (principle 13). Set `assetStrategy: "placeholder"`,
      note in the manifest what asset is needed, and ask the user to
      provide the original material. List every placeholder in the
      completion report; the job is not done while one exists silently.

   There is no further option: do not accept "low-risk" background text,
   do not hide contamination under gradients/overlays, do not defer to a
   hypothetical later inpaint, do not redraw the photo as vectors. Re-run the contamination check
   (`crop_asset.py` report, or visual inspection without cv2) on every crop
   that ends up in `work/assets/`.
5. All copy — headings, body, years, CTA labels, vertical labels, band
   phrases, outline display type — is `html-text` (`textRecreation:
   content-html` or `visual-match-css`), never part of an image.

```bash
python3 scripts/crop_asset.py work/mockup.png --roi 720,120,520,640 --out work/assets/hero-photo.png
```

## Phase 4 — Layer plan (hybrid: mandatory before any CSS)

For the FV and every region with overlap, decide **what sits on what and
why** — in the manifest, not in your head. Per element: `layerRole`
(background-photo / photo-overlay-gradient / primary-html-type /
decorative-outline-type / accent-band / vertical-label / foreground-card /
dark-bottom-panel / cta …), `zLayer`, `positioning` (flow unless truly
layered), `overlapIntent` (what the overlap must look like), `blendMode` if
any, `mustNotCover` (ids this element must never obscure — e.g. overlay must
not cover the heading; heading must not cover the subject's face),
`backgroundBehavior` for images (**full-bleed** = seamless background layer;
`framed` only when the comp genuinely shows a card).

The single most quality-deciding call in a poster FV is usually here: the
hero photo is a **full-bleed background layer** (`.fv-bg` scaffolding in
`templates/poster-typography.css`), not an `<img>` card in the flow.
`visual-check.mjs` enforces the declared intent later, so declare it honestly.

**Additions** (elements the comp does not have — handoff-required CTA
ribbons, nav bars, legal notes) are layered here too, per principle 12:
each gets a layer-plan entry with `mustNotCover` naming every comp element
near it. If the addition doesn't fit without covering or cropping a comp
device, recompose the region (shrink/move the addition, re-flow the
devices) or ask the user which wins — never ship the occlusion with a
self-granted waiver.

See `references/fv-poster-example.md` for a complete worked example
(layer plan table → imagegen regeneration → HTML type rebuild → evidence).

## Phase 4.5 — Page composition plan (multi-frame: mandatory)

The frames tell you what each section says; **nobody has yet designed the
page**. Before implementing, write a page-flow block in hypotheses.md that
composes the frames into ONE scrolling LP — this is where the vertical
narrative, the "keep scrolling" pull, comes from, and no per-frame
fidelity can substitute for it:

- **Seam plan — one line per adjacent pair** (01→02, 02→03, …): how does
  the eye cross the boundary? Background continuity (shared white, a
  color band ending, a photo edge), contrast cut vs smooth hand-off,
  spacing at the seam (a seam is allowed to breathe — stacked 16:9
  full-bleeds with zero rhythm read as a slideshow, the characteristic
  failure), and any device that *bridges* it (a motif line crossing the
  boundary, a heading pulled up over the previous section's edge, an
  overlapping card).
- **Connective motifs**: recurring devices from the essence ledgers
  (accent lines, label style, numbering, palette accents) and where each
  recurs so the page reads as one hand. A motif that appears once per
  frame because each frame was generated separately often *wants* to be
  a single continuous system on the page.
- **Whitespace & density rhythm**: which sections are dense, which are
  air; where the reader gets a pause before the next push (especially
  before/after CTA sections). Section heights follow content + rhythm
  with the frame height as the density floor — a below-FV section may
  (often should) run taller than its 16:9 frame.
- **Scroll narrative**: one sentence per section boundary on what the
  reader should feel/expect next; check the page top-to-bottom order
  still tells the story the frames imply.

Phase 7 reviews the built page against this block (page-flow review).
Skipping this phase and reproducing frames independently is how a build
ends up "every section 8/10, the page 5/10".

## Phase 5 — Implement, one section at a time

Order: header → hero → then down the page. The first view decides the
perceived quality; lock it first.

Rules:

- Start from `templates/base.css`; for poster/hero typography include
  `templates/poster-typography.css` (giant JP heading, outline type,
  highlight band, vertical label, thin EN caption, signature, FV layer
  scaffolding) and bind its custom properties to manifest tokens.
- Put measured/normalized values into CSS custom properties (tokens first,
  few section-local vars second).
- Every manifest element carries its `data-el` attribute.
- Semantic HTML, flex/grid flow layout; `position: absolute` only as the
  layer plan dictates (decorations and true overlaps).
- Dimensions that carry the design — type scale, container, section
  paddings, photo boxes, CTA — must trace to the manifest or a token.
  Small decorative/tuning px literals (borders, tick widths, nudges) are
  fine; traceability is for the critical numbers, not every literal.
- Do not "improve" the design. **Reproduce first; adjust second, on the
  record.** Readability/CVR/brand-system adjustments come only after the
  section survives its Phase 7 review in the comp's own terms, and each
  one is recorded in the manifest as `intentAdjustment` (what deviates
  from the comp, which user requirement demands it). An unrecorded
  deviation is a drop. "It reads better as a B2B LP" is the
  characteristic drift that flattens a poster comp into a generic web
  page (field data) — that trade-off belongs to the user, not to you.

## Phase 6 — Render → box diff → repair loop

```bash
node scripts/render.mjs --html work/site/index.html --viewport 1440x900 \
  --out-png work/reports/rendered.png --out-rects work/reports/rects.json
python3 scripts/box_diff.py work/manifest.json work/reports/rects.json \
  --out work/reports/box-report.json
```

**Multi-frame comp sets — this exact invocation is the contract:**

```bash
python3 scripts/box_diff.py work/manifest.json work/reports/rects.json \
  --section-relative --out work/reports/box-report.json
```

Do not substitute a pre-existing `npm run box-diff` / wrapper script
without confirming it passes `--section-relative` — page-global wrappers
fail everything below the first section (frame-local manifest bboxes vs
page-global DOMRects), and "fixing" those failures destroys the page.
With the flag, elements with a `sourceImage` are compared in frame-local
coordinates (their section root's rendered y is subtracted from the
actual rect), and section roots are compared on width/height only —
height against the frame height as a one-sided **density floor**:
shorter = collapsed = fail; taller = legitimate page composition
(Phase 4.5) = pass.

The report is document-ordered and names a `first_fix` — already drilled down
to the first failing LEAF (containers that fail only because of a child are
listed in `container_chain` and will heal on their own). **Diagnose its
cause** (usually spacing/size of that block or the one above), patch that one
thing, re-render, re-diff. Do not compensate downstream elements for an
upstream error. Reading deltas: a `dy` shared by everything below a point =
one spacing error at that point; `dx` growing per grid column = gap error
(dx/column-index); `dh` on text = font-size or line-height
(dh / line-count / line-height-ratio ≈ font-size delta).

Validated expectation: with 4 planted errors, 11/13 elements failed at first
diff; 3 diagnose-one-fix iterations reached 13/13 (2/13 → 7/13 → 12/13 →
13/13). If your pass count is not climbing like this, you are patching
symptoms, not causes.

Text elements: if the bbox height/line-count is off, binary-search font-size /
line-height through the loop (2–3 renders converge).

**Hybrid: run mobile alongside desktop from the FIRST loop iteration** —
big type, background layers and overlaps break silently on SP, and finding
that after desktop convergence forces rework. Minimum simultaneous checks:
no horizontal scroll, no text overlap, FV height sane, CTA visible
(exactly what `visual-check.mjs --viewports 1440x900,390x844` reports).

**Stopping criteria per section:** all `critical`+`high` pass, or 5 iterations,
or 2 consecutive iterations without improvement (then flag the residual to the
user instead of thrashing).

**Hybrid-residual rule (when box diff and visual intent collide):** a
residual box-diff failure may be closed as `hybrid-residual` instead of
"unfinished" ONLY when all three hold: visual-check passes on both
viewports; the owning section's review score (from crop pairs) is ≥7;
and the cause is named as one of *hand-measured-bbox* /
*flow-first-recomposition (Phase 4.5)* / *recorded intentAdjustment or
addition*. Every hybrid-residual is listed in the completion report with
its cause. Anything not meeting all three is unfinished work — and when
choosing where the next iteration goes, typography and detail devices
usually buy more perceived quality than another box-nudging pass.

## Phase 7 — Intent QA: visual-check + section review (FV gate)

Box diff proves geometry; this phase proves the *intent* survived. In
hybrid mode `visual-check.json` AND `work/reports/section-review.md` are
required completion evidence.

```bash
node scripts/visual-check.mjs --html work/site/index.html \
  --manifest work/manifest.json --viewports 1440x900,390x844 \
  --out work/reports/visual-check.json
```

Hard checks: images all load, no horizontal scroll, every manifest copy
string present, every `data-el` present, `full-bleed` backgrounds really are
absolute full-width layers (not cards), `mustNotCover` pairs don't intersect,
fv-critical headings ≥28px on mobile, CTA visible on mobile. Warnings:
undeclared text overlaps (either declare the `overlapIntent` or fix them).

Both `render.mjs` and `visual-check.mjs` force-load lazy images before
measuring (set `loading=eager`, scroll through the page, wait for settle) —
so an `images` violation means the image genuinely does not load, not that
it was below the fold. If you verify through another transport (MCP
Playwright, in-app browser), scroll to the page end before probing, or you
will reproduce the false failure.

**Section review** (hybrid: required, `work/reports/section-review.md`,
start from `templates/section-review.md`) — geometry passed; now judge
each section against its comp with your eyes. Cut the rendered page into
per-section strips so the comparison is honest (y/h from rects.json):

```bash
python3 scripts/crop_asset.py work/reports/rendered.png \
  --roi 0,<section.y>,1440,<section.h> --out work/reports/sections/03-value.png
```

(If `crop_asset.py` is unavailable — no cv2/Pillow — use `sips -c`/
ImageMagick, or Playwright clip screenshots after scrolling the section
into view; clip coordinates are viewport-relative.)

**Crop-pair evidence (principle 14) — the review's currency:**

```bash
python3 scripts/crop_pair.py \
  --comp work/mockups/section-01-hero.png --comp-roi 40,90,760,440 \
  --build work/reports/rendered.png       --build-roi 24,70,700,400 \
  --out work/reports/crops/01-hero-lockup-pair.png --zoom 2
```

Required pairs, saved under `work/reports/crops/` and cited by path in
the review: the FV type lockup at ≥2× zoom, every detail-inventory row's
verdict, every adopted photo asset vs its comp region, and the CTA + key
numerals/dates/prices. A verdict row without a pair path is not a
verdict. "The CSS has it" is not evidence — judge what rendered
(`crop_pair.py` runs on Pillow alone, so fallback mode never excuses
skipping this).

Per section, strip and frame side by side at the same width, record:

1. Layout & composition — macro placement right?
2. Display-type scale ratio vs hypotheses.md — poster or timid?
3. Palette & photo mood — replaced/generated assets included: subject,
   mood, color grade, aspect. A photo that "loads fine" but reads cold
   when the comp is warm fails here. **Measure the palette, don't vibe
   it**: run `sample_color.py` on a comp-frame ROI and on the same ROI
   of your strip (both work in Pillow fallback) and record the hex pairs
   in the review. A washed/pastel build against a crisp comp — veils
   over the photo, tints where the comp has white, gray where it has
   navy — is a measurable drift, and it sinks the "as a website" score
   even when every box passes.
4. **Detail disposition** — walk the Phase 1 detail inventory item by item.
   Judge each device from a **zoomed crop pair** (comp device region vs
   the same region of your strip), not from the full-section thumbnail or
   memory — at section scale every drop looks fine. Verdicts are defined,
   not vibes:
   - `present` — the device's *specific content* (glyph, icon subject,
     chip text, number) and treatment survive. A generic stand-in where
     the comp has a specific motif is NOT present (principle 11).
   - `adapted` — must state BOTH what was preserved AND what was lost,
     and why the loss is acceptable. "Adapted" with no named loss is
     `missing` wearing a costume; an addition covering a comp device is
     never "adapted" (principle 12).
   - `missing` — fix it before completion, or escalate to `waived`.
   - `waived` — only with a reason the *user* would accept (their
     constraint, their instruction), stated. Self-granted waivers for
     effort reasons don't exist.
   An unlisted disposition is a silent drop.
5. Score the section 0–10 against its frame — as the frame's designer
   would score it — on FOUR axes: composition, typography, palette &
   photo, detail devices. **The section score is the MINIMUM of the four
   axes, never the average** — the user sees the collapsed axis, not
   your mean; a 9-composition/4-typography section IS a 4. Anchors (per
   axis): 8+ = the designer recognizes their work, devices intact; 6–7 =
   structure right, some treatment diluted; 4–5 = "layout right, devices
   dropped/genericized" — the classic inflated self-review sits here
   while calling itself 8; ≤3 = structure broken.

**A section below 7 goes back to implementation before the job is done.**
"Layout right, devices missing" typically scores 4–5 — that is exactly the
gap this pass exists to close; do not report completion over it.

**Calibration & independence:** implementing agents grade their own work
~3 points high — three consecutive field runs: self 8+/user 5, self
7.8/user 3, self 7.5–8/user 3.7. Before reporting, re-judge every
`present` against its crop pair, and treat any score you can't back with
a pair path as suspect. A `waived` verdict requires the user's words — a
verbatim quote from their instruction or handoff, cited — never your
paraphrase of their priorities ("the handoff prioritizes conversion" is
a self-waiver wearing a quote's clothes). When the setup allows it, have
a different agent or a fresh session run this review from the crop pairs
alone: fresh eyes don't inherit your rationalizations.

**Additions table (separate from detail disposition):** every
`addition: true` element is listed here with its `additionReason` and
its `mustNotCover` outcome. Additions never appear as detail verdicts
and never raise a fidelity score — they are the user's requirements,
audited for occlusion, not comp devices.

**Page-flow review (multi-frame: required):** after per-section blocks,
judge the assembled page against the Phase 4.5 plan — scroll the real
page (or read the full-page screenshot top-to-bottom) and record: each
seam as designed? (one line per boundary), connective motifs actually
recur?, whitespace rhythm present or is the page a stack of 16:9 slabs?,
scroll narrative holds? Score the page-as-a-page 0–10, same anchors, and
carry a below-7 flow score back to implementation exactly like a failing
section. Per-frame scores do not average into this number — four 8/10
sections can compose a 5/10 page, and this build gets judged as a page.

**FV QA gate** — the first view is judged separately and harder; record the
answers in the FV block of section-review.md. Look at the desktop AND
mobile screenshots and answer each (these need your eyes, not a script):

- [ ] Photo reads as a seamless background — not a framed card that cheapens it
- [ ] Main heading is unmistakably the visual protagonist (size, contrast)
- [ ] Type does not collide with the subject's face / key photo detail
- [ ] Overlay gradient guarantees copy legibility at every breakpoint
- [ ] The FV works *as a poster* including CTA, signature, year, vertical label
- [ ] On SP the heading has not shrunk into a caption; FV height is sane
- [ ] Typographic treatment matches the comp: tightness, leading, band,
      outline, in-line scale steps, weight class, serif accents (the
      Phase 1 type spec, block by block)
- [ ] Every photo-class visual is a real raster (generated / stock /
      layered source) — no vector, CSS or flat-avatar stand-in
      (principle 13)

Each typography/poster checkbox is answered from a crop pair (principle
14) — cite the pair path next to the box. Any "no" → back to the layer
plan or typography, not to pixel-nudging.

## Phase 8 — Pixel QA: masked pixel diff (pixel-clone; hybrid: FV frame)

```bash
python3 scripts/pixel_diff.py work/mockup.png work/reports/rendered.png \
  --manifest work/manifest.json --out-heatmap work/reports/diff.png \
  --out work/reports/pixel-report.json
```

Text regions are auto-masked. Read the heatmap yourself: concentrated red =
object-fit cropping, gradient direction, shadow/radius issues (things boxes
can't see). Scattered speckle = anti-aliasing noise, ignore. In hybrid the
photo was *regenerated*, so its region can never pixel-match — mask it or
skip pixel diff for that area; intent QA (Phase 7) is the hybrid bar.

**Multi-frame hybrid: run it on the FV frame** (comp frame vs the FV
region of the render), photo and text regions masked, and judge the
residue: layout bands, overlay veils, palette washes, device geometry.
The FV is graded near-pixel-strict by the user, and box tolerances —
especially hand-measured ones — happily pass an FV where *everything* is
slightly off; the heatmap is what catches a washed-out or subtly
distorted first view. Skippable only when OpenCV is genuinely
unavailable after a recorded failed install attempt (Setup gate).

## Phase 9 — Responsive

- **pixel-clone / production:** only after desktop matches (Phase 8).
- **hybrid:** SP has been checked since Phase 6; this phase is where you
  *finish* it, not start it.

Derive SP behavior from structure when no SP comp exists: grid → stack;
true overlap → release or re-anchor (vertical label → horizontal eyebrow);
oversized type → `clamp()` with a floor that keeps the poster feel (the
28px mobile-heading check); full-bleed background → keep full-bleed, move
the focal point with `object-position`; dark bottom panel → sticks to
viewport bottom or flows after content — pick per content length. If an SP
mockup exists, repeat Phases 1–7 against it at its width.

## Failure modes → what to do

| Symptom | Cause | Fix |
| --- | --- | --- |
| Many elements fail diff at once | upstream cascade | fix ONLY first_fix, re-render |
| Loop oscillates on a text element | chasing glyph pixels | freeze font, compare bbox only, mask in pixel diff |
| snap_bbox returns weak_edges | soft/gradient boundary | re-hypothesize ROI, or accept with wider tolerance |
| Crop looks doubled with HTML text | baked-in text contamination | regenerate text-free via imagegen (+ evidence) / layered asset; if regen can't match → `placeholder` + ask user (never conceal) |
| visual-check fails `images` on below-fold imgs | lazy images unloaded in file render | scripts now force-load them; on MCP/in-app transports scroll to page end before probing |
| 10 refs, unclear what to box-diff against | sectioned comp set treated as one primary comp | multi-frame hybrid: `section-comp` frames + per-section QA scoping (see Fidelity modes) |
| FV looks "cheap" despite passing box diff | photo framed as a card; typography not chased | layer plan: full-bleed `.fv-bg`; apply poster-typography patterns |
| Text unreadable over photo | missing overlay layer | add photo-overlay-gradient to the layer plan |
| Breaks on SP after desktop converged (hybrid) | mobile checked too late | run visual-check with both viewports from the first loop |
| setup_env / render can't find a browser | playwright chromium assumed | CHROME_PATH to system Chrome; or MCP Playwright / in-app browser |
| Python scripts fail on import cv2 | OpenCV missing | Create a project-local `.venv` and install `opencv-python numpy pillow`; Pillow+numpy fallback covers only normalize/sample/crop |
| Colors look off despite matching hex | sampled a textured cluster | re-sample with `--exclude` over photos; only flat clusters are tokens |
| Whole page slightly "cheap" | spacing not normalized | re-derive spacing scale; snap raw gaps to it |
| Box diff passes but the page looks nothing like the comp | manifest back-filled from your own render (tautology) | re-measure FV + section-critical bboxes from the comp frames; tag DOMRect-derived values `implementation-derived` |
| Page reads "tasteful but timid" next to the comp | display-type scale ratio collapsed | measure glyphHeight ÷ frameHeight per frame; make headings hit the comp bbox at canonical width (fix clamp caps) |
| Section layout matches but feels flat / generic | detail devices dropped (underlines, ticks, eyebrow rules, watermark type, frame accents) | walk the detail inventory in section-review.md; implement or explicitly waive each item |
| Replaced photo drags the section down | subject/mood/color-grade mismatch with the comp | judge `replace` like `generated` (subject, mood, grade, aspect); regenerate, or harmonize with a CSS filter grade |
| Sections render much shorter than their frames | density collapsed (cramped type, starved whitespace) | `box_diff.py --section-relative` height check on section roots; restore section paddings/type scale |
| Self-review says 8/10, user says 5/10 | verdict laundering: generic stand-ins graded `present`, losses hidden under `adapted` | re-judge every device from zoomed crop pairs with the Phase 7 verdict definitions; principle 11 |
| Page reads as N stacked slides, no pull to scroll | frames reproduced independently; seams never designed | Phase 4.5 page composition plan (seams, motifs, whitespace rhythm); page-flow review in Phase 7 |
| Specific motif became generic shapes (止 → rectangles, icons dropped) | detail inventory recorded categories, not content | re-inventory with content-level rows (actual glyph/icon/number); rebuild; verdict was `missing`, not `adapted` |
| Added element (ribbon/nav) covers a comp device | addition layered without `mustNotCover` | principle 12: recompose to make room or ask the user; never self-waive the occlusion |
| visual-check copy fail though the text is visibly there | composite copy string interrupted by child labels/icons in DOM | composite-text rule: manifest child elements with short contiguous strings |
| Box loop fights a label's underline/rule/tick | pseudo-element decoration expected inside the DOM box | measurability rule: real element or explicit host size for box-diff targets; else `detail` + section review |
| No OpenCV and installs are approval-gated | dependency-gated environment | No-OpenCV fallback: hand-measured `normalized`/`user` bboxes, one-step wider tolerances, sips/Playwright crops, eyeball contamination check, declared in the report |
| Photo-class visual shipped as vector avatar / CSS "figure" | media-class drop rationalized as `adapted` ("rights", "no generator", "text-free") | principle 13: regenerate with a raster model, or licensed stock `replace`, or placeholder + ask; the verdict is `missing` and the section caps at 4 |
| Layer intent passes desktop, fails mobile (or vice versa) | media query overrides position/inset of a declared full-bleed layer (e.g. `position: relative` on SP) | keep `layerRole`/`backgroundBehavior` invariant across breakpoints — adapt size/focal-point, not the layering; visual-check both viewports every loop |
| Heading size matches but reads flat next to the comp | type spec too shallow: in-line scale steps / 900 weight / serif accents dropped, or the webfont never loaded | Phase 1 type spec + Phase 3 font policy; rebuild the heading with span scale steps; confirm the webfont actually renders |
| Icons look naive / off-brand | bespoke hand-drawn SVG paths instead of a matched icon set | icon policy: established set (Lucide/Tabler/Phosphor/Heroicons/Material Symbols), match stroke weight & corner style, record `iconSource` |
| One section's children all fail box diff by the same offset | manifest bboxes written in an inner container's coordinate space, not frame-local | measure every child against the frame image; `--section-relative` subtracts only the section ROOT's origin |
| Review says `present`, render shows it broken (止 → rectangles again) | verdict taken from code/DOM, not rendered pixels | principle 14: every verdict cites a `crop_pair.py` file under `work/reports/crops/` |
| Entire scene/environment photo silently dropped; review never mentions it | detail inventory had no row for the ground | principle 15: environment row per frame; sweep "what carries the remaining area?" |
| Comp device waived "because the handoff prioritizes X" | self-waiver via paraphrase | `waived` needs the user's verbatim words, cited; otherwise it is `missing` |
| Heading lockup cramped / glyphs colliding though its block bbox passes | no per-line contract; tracking crushed to fit the box | Phase 1 per-line decomposition → span-level manifest entries; FV pixel diff |
| Build reads washed/pastel where the comp is crisp | overlay veils + palette drift nobody measured | sample_color the same ROI on comp AND strip; record hex pairs; fix veils/tints |
| Fallback mode though installs were possible | setup output read as permission | Setup gate: attempt the venv install; fallback only with a recorded failed attempt or explicit prohibition |

## Command reference

| Script | Purpose |
| --- | --- |
| `normalize_image.py in.png --width 1440 --out work/mockup.png` | canonical coordinate space (cv2 or Pillow) |
| `profile.py img --axis y [--roi x,y,w,h]` | section bands / container edges |
| `snap_bbox.py img --bbox x,y,w,h [--bbox …] [--radius 16]` | refine hypothesis bboxes |
| `sample_color.py img --roi x,y,w,h [--exclude x,y,w,h]` | measured color tokens (cv2 or Pillow) |
| `crop_asset.py img --roi x,y,w,h --out f.png` | asset crop + contamination check (check needs cv2) |
| `crop_pair.py --comp f --comp-roi x,y,w,h --build f --build-roi x,y,w,h --out pair.png [--zoom 2]` | labeled side-by-side comp-vs-build crop — the Phase 7 verdict evidence (works on Pillow alone) |
| `render.mjs --html f --viewport WxH --out-png f --out-rects f` | render + DOMRects |
| `box_diff.py manifest.json rects.json --out report.json [--section-relative]` | document-order repair signal (flag: multi-frame frame-local compare + one-sided density floor — REQUIRED for multi-frame; distrust page-global wrapper scripts) |
| `visual-check.mjs --html f --manifest m.json --viewports 1440x900,390x844 --out f.json` | intent verification (hybrid evidence) |
| `pixel_diff.py mockup.png rendered.png --manifest m.json --out-heatmap d.png` | final pixel QA (pixel-clone) |

## Templates & references

- `templates/base.css` — quality defaults, `.text-trim`, container
- `templates/poster-typography.css` — giant JP heading, outline type,
  highlight band, vertical label, EN caption, signature, FV layer scaffolding
- `templates/hypotheses.md` — Phase 1 artifact: per-section role, design
  core, scale ratio, detail inventory, asset plan
- `templates/section-review.md` — Phase 7 artifact: per-frame side-by-side
  review, detail disposition with crop-pair paths, axis-min scores,
  additions table, FV gate record
- `templates/photo-asset-review.md` — per-candidate adoption record for
  generated/stock photo assets (the Phase 3 checklist as a table)
- `references/fv-poster-example.md` — worked hybrid example: AI poster FV →
  layer plan → imagegen regeneration → HTML type → evidence checklist
- `schemas/element_manifest.schema.json` — manifest contract incl. hybrid
  fields (`mode`, `layerRole`, `overlapIntent`, `mustNotCover`,
  `backgroundBehavior`, `textRecreation`, `generatedAsset`, `replacedAsset`,
  `qaPriority`)
