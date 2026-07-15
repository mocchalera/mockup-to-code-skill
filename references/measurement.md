# Phases 0–2 — Normalize, Hypothesize, Measure

Read this before starting Phase 0. Companion: `manifest-and-assets.md` (Phase 3).

## Phase 0 — Normalize the coordinate space

```bash
python3 "$SKILL_DIR/scripts/normalize_image.py" raw.png --width 1440 --out "$WORK_ROOT/mockup.png"
```

Everything downstream (hypotheses, measurements, manifest, DOMRects) lives in
this one space. Your vision sees a *downscaled* copy of large images — talking
in two coordinate spaces silently corrupts every number. In a multi-frame comp
set, normalize EVERY frame to the same width.

Ask the user (if unknown): target viewport width, fidelity mode, available
fonts, whether layered source assets exist (background-only, photos-only,
text-free versions — these beat cropping every time), whether an image
generator (imagegen, `cockpit gen-image` …) is available for regenerating
contaminated photos, and whether licensed stock is acceptable.

## Phase 1 — Hypotheses (your job)

Look at the normalized comp and write `"$WORK_ROOT"/reports/hypotheses.md`
(start from `templates/hypotheses.md`). Per section: role, approximate bboxes
of important elements, the **design's core** (the thing that must not be
compromised), and an asset strategy guess per visual.

### Designer decomposition ledger (required in hybrid)

Before measuring or writing CSS, decide what each visible device **belongs
to** and what relationship must survive responsiveness. This is not a CSS
coordinate plan; it is the designer's construction plan.

Use these ownership classes in hypotheses.md and carry them into the manifest:

- `container-content`: main copy, CTA groups, cards, forms, body copy. Built
  in flow/grid/flex inside the responsive container.
- `hero-bound`: background photos, photo overlays, hero-bottom watermarks,
  large section-only decoration. Positioned against the hero section, not the
  document or an inner text column.
- `photo-bound`: callouts, badges, plant sprigs, handwriting, dots, and other
  details whose visual balance depends on a face, product, empty copy space,
  or photo edge. The anchor is the photo/focal region, not the page grid.
- `viewport-fixed` / `viewport-edge`: global nav, fixed vertical logos,
  edge labels, persistent site identity. These may use `positioning:
  "fixed"`/`"sticky"` in the manifest when the comp suggests global UI, but
  they still need `mustNotCover` and mobile behavior.
- `section-bound-decoration`: waves, background type, accent rules, dots,
  blobs, dividers. Usually CSS/SVG and anchored to the section edge or seam.

For each row record: render medium, layer owner, anchor target, relationship
to preserve, and responsive behavior. Examples: "handwritten bubble follows
hero photo, 60px above subject shoulder, may shrink but not cross the face";
"large LISTEN watermark anchors right to viewport edge and bottom to hero
bottom"; "fixed vertical logo stays at left viewport edge until mobile, then
becomes a compact header mark".

### Full-field photo source classification (before any crop)

First set the manifest-level classification: `photoLed: true` when any
authoritative frame contains a photographic/illustrated subject or environment
that must survive decomposition; otherwise explicitly record `photoLed: false`.
Do not infer false from the absence of photo rows—the declaration and the rows
must agree, and `asset_preflight.py` blocks disagreement.

For every fv/section-critical photo or illustration, inspect the entire
photographic field the comp intends, not only a candidate clean subrectangle.
Record `visualRole`, `sourceFrameHasForegroundOverlap`, the exact
`sourceFrameOverlapKinds`, and whether a separate `cleanLayeredSource` exists.

Then compare the candidate crop to the full field: did it preserve subject
count, room/environment, focal relationships, intended aspect, and copy-space
geometry? If it removed overlap by zooming into one face or the lower half of a
room, record `cropPreservesComposition: false`; that candidate cannot ship as
`crop-asset` even when `crop_asset.py` reports no text-like pixels. The pixel
checker answers "is this rectangle contaminated?"; this classification answers
"is this still the design's photograph?" Both must pass.

### Lettering vs structural copy (required in hybrid)

Classify every text-like visual before choosing the medium:

- **Structural copy**: headings, nav, CTA, body text, legal notes, labels,
  prices, dates, and anything needed for SEO, accessibility, interaction, or
  content correctness. These are HTML/CSS text, then tuned with the type spec
  below.
- **Lettering decal**: expressive non-structural lettering such as a
  handwritten speech bubble, signature, margin note, or decorative callout
  whose charm is the drawn artifact. These may be generated as transparent
  raster assets (or hand-traced SVG / handwritten-font DOM when better), but
  must be manifested as `mediaClass: "lettering-decal"` with exact target
  text, readable shipped asset path, `letteringProof {exactText, method,
  pairPath}`, and a 200% crop-pair proof. Never use this classification
  to avoid rebuilding a heading, CTA, nav, legal note, or body copy.

### Detail inventory (required in hybrid)

Every small design device you can see — accent underlines / hand-drawn
strokes, generated or hand-traced lettering decals, tick marks, eyebrow labels + rule lines, letterspaced EN captions,
watermark / oversized cropped type, photo frame offsets & accent borders,
tilts, speech bubbles, badges, shadow/radius language, gradient veils,
glass/emboss surface layers, inset section frames, brand lockups, in-photo UI
content (dashboard numbers, status chips) that must be rebuilt as HTML
overlays. Zoom into each frame and sweep corners, under-headings, card edges,
photo edges — AI comps hide half their charm below 100% zoom, and a device you
never listed is a device you will silently drop.

Three granularity rules keep the inventory honest:

- **Record the content, not the category** (hard rule 11). Write "outline
  kanji 「止」, ~560px, upper-left, cropped by frame edge", not "oversized
  outline glyph". Write the actual icon subjects, chip texts, numbers.
- **Open up composite devices.** A card/panel gets one row per internal part
  that carries design (icon, label, status chip, connector, rule) — one row
  saying "workflow cards" hides three drops.
- **Account for the ground (hard rule 15).** The last row per frame is the
  section's environment itself — scene photo, glass mega-panel, colored
  field, gradient wash — with its media class. No row for the background is
  how an entire desk-scene photo vanishes from a build with no verdict ever
  recorded. Sweep once more asking "what carries the remaining area?"
- **Freeze source surface topology before asset prompts (hard rule 38).** For
  each critical raster, decide from the source crop whether it is a
  `section_field`, `floating_scene`, `contained_artwork`,
  `tone_merged_object`, or `source_visible_frame`. Record which edges visually
  bleed, alpha-float, mask, tone-match, or stay framed. Do not infer topology
  from the first generated bitmap: that is how full-field heroes become cards
  and floating paper/collage scenes keep generator-white rectangles.

Also record per device its **rendering craft**: is that connective line a
bezier curve with varying sweep? Is that panel glass (blur + translucency +
edge highlight)? How soft is the shadow? The Phase 7 review judges craft, not
just presence — a straight 1px line standing in for a flowing curve is a drop.

For every `sourceSpecific: true` row, this observation is machine-shaped as
`renderingCraft`: name the source medium, at least two visible
`signatureTraits`, the minimum number of observable atomic parts, an
`atomicParts` list naming those parts, `genericStandInsForbidden: true`, and
the ≥2× source evidence crop. `minimumAtomicParts` is an observation floor,
not a DOM-node or file-count quota. Bind distinct manifest element ids only
when the parts move, recompose, update, interact, layer, or get reused
independently. A static card illustration may bind one `card_artwork_plate`
whose `atomicParts` preserve the icon, badge, connector, screen, shadow, and
other visible craft inside one regenerated image.
Do not write category traits such as “nice icon” or “premium card.” Write
observable construction: “single-weight teal outline gift box,” “yellow bow
overlaps the lid,” “separate circular P medallion in the lower-right.” This
contract exists specifically to stop a complex device from becoming `🎁`,
`♡`, `✓`, or one more copy of a generic white card—not to force a coherent
editorial image into arbitrarily small files.

Mirror this ledger into `manifest.detailInventory`; prose alone is not the
completion operand. Each row has a stable id, section, source-specific flag,
priority, and either bound manifest element ids or `evidenceMode: crop-only`.
Phase 7 dispositions refer back with `inventoryId`, preventing renamed/generic
devices from disappearing between analysis and scoring.

### Type spec (per display-text block; required in hybrid)

The comp's typography is *designed*; decompose it before any font is chosen:

For Japanese, mixed-script, vertical, or FV display-critical work, invoke the
`typography` skill here. Its run ledger and verification report are specialist
inputs to this type spec; they do not replace mockup manifest/box evidence.

- **Letterform class & weight** — gothic / mincho(serif) / rounded / display;
  weight class (900 display vs 700 body are different animals); stroke contrast.
- **In-line scale steps** — JP display headings routinely set kana/particles
  smaller than the kanji (「社長自らが」 with 「らが」 at ~0.6×; measure the
  ratio off the comp) and numbers larger than unit suffixes (「55,000円」,
  dates vs weekday labels). A flat single-size rebuild is a typography drop.
- **Script/word-run optical sizing** — split mixed lockups into the runs a
  designer would tune separately: Latin words/acronyms, numerals, kanji,
  hiragana/kana, particles, unit suffixes, and emphasized words. Measure each
  run's visible glyph bbox against an anchor run (usually the kanji body in
  the same line). Example: in 「AI駆動型へ」, if the comp makes `AI` visually
  as tall as or taller than 「駆動型」 but the chosen Latin font renders `AI`
  optically smaller at the same CSS size, record the needed optical ratio
  (e.g. `AI` 1.10× anchor, baseline -0.02em). The implementation must tune
  the span's font-size / baseline / tracking until the rendered crop matches
  the perceived height, not the nominal `font-size`.
- **Per-word accents** — color swaps, marker bands, underline segments bound
  to *specific words*.
- **Character-exact transcription (hard rule 21)** — transcribe every display
  copy string from a ≥2× zoomed crop, not from memory of the frame. Kanji
  substitutions are plausible by nature (field case: comp 実行 → build 実装,
  undetected — every copy check compared against the same wrong
  transcription). The manifest copy string is the contract everything else
  checks against; get it right here, then re-verify glyph-by-glyph at the
  Phase 7 copy proof.
- **Numeral/date treatment** — serif dates or prices over a gothic body must
  survive.
- **Tracking/leading class** per block (tight display vs airy caption).
- **Line-start punctuation** — when a line begins with `「` / `『` / `（`,
  measure the visible ink edge, not only the DOM/glyph advance. Record whether
  the comp hangs the mark into the margin and the flow-safe correction
  (`hanging-punctuation`, negative inline margin, or balanced text-indent).
- **Per-line and per-run decomposition (fv-critical lockups):** split the
  lockup into rendered lines, then into typographic runs inside each line.
  Measure each line bbox and each run bbox in the comp. These become
  span-level manifest elements (`data-el="hero-title-line1"`,
  `data-el="hero-title-ai"`, `data-el="hero-title-kanji"` …) — the only way
  the box loop can SEE crushed tracking, flattened scale steps, or Latin /
  numeral runs that render too small next to Japanese glyphs. Field data: a
  build hit its heading block box while negative tracking crushed the glyphs
  into near-collision, and nothing measured it.
- **Count lines and runs separately:** `expectedVisualLineCount` is the number
  of rendered baselines/visual lines at the canonical width.
  `expectedRunCount` is the number of declared `scriptRuns`. Never set a line
  count from child span count; that false contract made one-line CTA labels
  appear to require multiple lines.

### Font bake-off (JP display roles; required in hybrid)

Render the real heading copy in 2–3 candidate fonts (one scratch HTML file),
crop-pair each against the comp glyphs (`crop_pair.py --label-b "<candidate>"`),
pick by letterform — weight, width, counters, terminal shape — and record the
pair paths + one-line rationale in hypotheses.md. The pick's known residual
(e.g. "narrower 型 than comp") is written down now, not discovered by the user
later. Choosing from a font's *name* is how a poster comp flattens into a
default-looking page.

**Letterform-class gate (before bbox tuning):** first decide the source class
from a ≥2× crop: gothic has near-monoline strokes and no serifs; mincho has
triangular terminals and strong stroke contrast; rounded faces soften corners
and counters. Candidate fonts come from that class unless the comp visibly
switches class for a specific word/run. A gothic source rebuilt in mincho (or
vice versa) is rejected before box diff, even when its width/height are close.
Record `typeSpec.letterformClass` and the candidate pair paths in
`fontBakeoffEvidence`.

**No-transform repair contract:** structural text is not a geometric shape.
Do not plan `scaleX`, `scaleY`, skew, rotate, or transform translation as a
font-fit tool. These operations change stroke contrast/counters and leave the
original flow box behind, so following copy can overlap while DOM geometry
appears repaired. Use this order instead: class-matched family → weight →
font-size → letter-spacing / font-feature settings → line-height → run-level
font-size / vertical-align → container/flow spacing → optical punctuation.
Only a visibly intentional decorative/display distortion in the source may
carry a documented `typeSpec.transformException` with crop evidence.

### Display-type scale ratio

snap_bbox the tallest display-glyph block per frame and record
`glyphHeight / frameHeight`. This one ratio is the strongest "poster vs timid"
signal — a build that collapses it (comp 0.33 → build 0.13) reads cheap even
when every inner box "fits". The implemented heading must hit the comp bbox at
canonical width; `clamp()` caps that flatten the ratio are a defect.

Also record **run optical-height ratios** for fv-critical display text:
`runGlyphHeight / anchorGlyphHeight` plus any baseline offset. Use the comp
crop as the truth, not CSS intuition. A Latin acronym in a Japanese heading,
a price number, or a small particle may need a different font-size and
baseline shift than surrounding kanji even when the line's overall bbox is
already close.

### Section-critical source impression profile (all headings; required)

Do not stop at a family/weight label. For every fv-critical and
section-critical heading, record `typeSpec.sourceImpression` from the source
crop: frame dimensions; block width/height ratios; maximum line width and
visible glyph-height ratios; tracking in em; line advance; signed interline
gap where relevant; ink density; viewport maximum-size ratio; heading-to-lead,
body, and label jump ratios; and desktop/mobile scale bounds. Keep the crop as
`evidencePath`.

These measurements distinguish “bold but airy” from “ultra-black and packed.”
The former can have a large viewport footprint with moderate ink density,
neutral or slightly open tracking, and generous line advance. A categorical
note such as `display gothic 900` cannot encode that distinction. Measure each
source frame independently. If three or more section headings produce an
identical bbox/type signature, treat it as template-copy risk unless the comps
visibly share one lockup system and `sharedSystemEvidence` records that proof.

### Poster lockup geometry (multi-line FV headings; required)

`expectedVisualLineCount` proves only how many lines exist. It does not prove
that the lockup has the source's scale or breathing room. For every
fv-critical heading with two or more lines, measure and bind
`typeSpec.posterGeometry` before CSS:

- one glyph-tight source bbox per visual line in frame-local coordinates;
- `sourceBlockHeightRatio = union(line bboxes).height / frameHeight`;
- `sourceLineAdvanceRatio = adjacent line-start distance / anchor glyph height`;
- signed `sourceInterlineGapPx` (negative only when the source visibly overlaps);
- a readable ≥2× source crop in `evidencePath`.

The first hero render repeats the same measurements. Correct line strings with
a smaller block-height ratio, compressed advance, or unintended negative gap
are a stop condition before below-FV DOM/CSS.

### Essence ledger (multi-frame, per frame)

3–5 bullets naming what must survive translation to the scrolling page — the
frame's core statement, its 1–2 signature devices, its palette/mood — plus,
explicitly, the **frame artifacts to translate, not copy** (16:9 letterbox
height, slide-style full-bleed edges, per-frame background resets). Phase 4.5
composes the page from these ledgers; Phase 7 judges below-FV sections
against them.

### Verify section boundaries cheaply

```bash
python3 "$SKILL_DIR/scripts/profile.py" "$WORK_ROOT/mockup.png" --axis y
python3 "$SKILL_DIR/scripts/profile.py" "$WORK_ROOT/mockup.png" --axis x --roi 0,760,1440,480
```

## Phase 2 — Measure (scripts' job)

Refine every important bbox — your guesses are input, not truth:

```bash
python3 "$SKILL_DIR/scripts/snap_bbox.py" "$WORK_ROOT/mockup.png" \
  --bbox 118,178,684,158 --bbox 122,782,370,416 --radius 16
```

- Choose `--radius` larger than your expected hypothesis error (default 16;
  24–32 if unsure). `weak_edges` = no reliable gradient in the window: either
  your guess was off by more than the radius (re-hypothesize, or re-run that
  one box with a bigger radius) or the boundary is genuinely soft (accept with
  wider tolerance). The tool never widens silently.
- Edges at the canvas boundary (full-bleed sections) snap automatically.
- **Text bboxes are glyph-tight.** snap_bbox returns the visual glyph box,
  SMALLER than a DOM box (half-leading, side bearing; measured ~29px top
  offset on an 88px heading). Implement measured text with the `.text-trim`
  utility (text-box-trim, Chrome 133+; in `templates/base.css`) so DOMRects
  match glyph boxes within ~3px. If unavailable, compare x/width strictly but
  y via center with slack ≈ half-leading.
- Colors — never eyeball hex values:

```bash
python3 "$SKILL_DIR/scripts/sample_color.py" "$WORK_ROOT/mockup.png" --roi 0,0,1440,120 --k 4
```

Only `kind: flat` clusters become CSS tokens. `textured` = photo/gradient —
re-sample with `--exclude` over photos if a token ROI is contaminated.

- Normalize measurements into intent: cluster measured gaps into a spacing
  scale (snap values within ±3px to the nearest step; 4/8/10px systems all
  occur). Record both raw and normalized.
- Write a **bbox ledger row** for every FV/section-critical measurement before
  implementation. The manifest field is `measurementRef`; hypotheses.md keeps
  the human-readable table. Each row names the normalized frame, ROI, command
  or manual zoom method, accepted bbox, confidence, and any later revision.
  Revisions require another comp-side measurement. Do not update manifest
  bboxes because the current DOMRect happens to be closer; `artifact_check.py`
  flags missing ledgers and `bboxSource: implementation-derived` on critical
  elements before the completion gate.
