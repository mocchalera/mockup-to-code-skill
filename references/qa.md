# Phases 6–10 — Box loop, intent QA, section review, pixel QA, responsive, completion gate

Read this before the first render. The evidence this file defines is what
"done" means; a missing artifact is a skipped phase, not a streamlined one.
"Done" itself is computed in Phase 10 — not decided by you.

## Phase 6 — Render → box diff → repair loop

**FV converges before below-FV exists (hard rule 19).** Run this loop on the
FV alone — hero HTML/CSS built, below-FV sections still absent or stubbed —
until every fv-critical element passes (or the stopping criteria fire and the
residual is recorded). Expect 3–5 iterations; one iteration that logs the
failures and moves on is the field-observed failure ("measured but never
repaired" — a run logged its hero lockup/CTA/photo deltas, built four more
sections, and shipped with all eight fv-critical boxes still failing). Only
then implement below the fold and widen the loop to the whole page. The FV
carries the user's judgment of the entire build; iterations spent there are
never wasted, iterations spent below the fold while the FV is off are.

```bash
node "$SKILL_DIR/scripts/render.mjs" --html "$WORK_ROOT/site/index.html" --viewport 1440x900 \
  --out-png "$WORK_ROOT/reports/rendered.png" --out-rects "$WORK_ROOT/reports/rects.json"
python3 "$SKILL_DIR/scripts/box_diff.py" "$WORK_ROOT/manifest.json" "$WORK_ROOT/reports/rects.json" \
  --out "$WORK_ROOT/reports/box-report.json"
```

**Multi-frame comp sets — this exact invocation is the contract:**

```bash
python3 "$SKILL_DIR/scripts/box_diff.py" "$WORK_ROOT/manifest.json" "$WORK_ROOT/reports/rects.json" \
  --section-relative --out "$WORK_ROOT/reports/box-report.json"

python3 "$SKILL_DIR/scripts/page_flow_check.py" "$WORK_ROOT/manifest.json" \
  "$WORK_ROOT/reports/rects.json" --work-root "$WORK_ROOT" \
  --out "$WORK_ROOT/reports/page-flow.json"
```

Do not substitute a page-global wrapper script — it fails everything below
the first section. With the flag: elements with a `sourceImage` are compared
frame-locally; section roots are compared on width/height only — height
against the frame height as a one-sided **density floor** (shorter =
collapsed = fail; taller = legitimate Phase 4.5 composition = pass). When a
section legitimately runs taller than its frame, y-deltas on its
non-fv-critical children are reported as `y_waived_recomposition`, not
failures — the section was recomposed, the children's x/w/h still hold.
fv-critical elements are never waived.

The report names a `first_fix` — the first failing LEAF in document order
(containers failing only because of a child are in `container_chain` and heal
on their own). **Diagnose its cause** (usually spacing/size of that block or
the one above), patch that one thing, re-render, re-diff. Never patch all
deltas at once; never compensate downstream elements for an upstream error.
Reading deltas: a `dy` shared by everything below a point = one spacing error
at that point; `dx` growing per grid column = gap error; `dh` on text =
font-size or line-height (dh / line-count / line-height-ratio ≈ font-size
delta). Text elements: binary-search font-size / line-height through the loop
(2–3 renders converge).

Validated expectation: with 4 planted errors, 3 diagnose-one-fix iterations
reached 13/13 (2/13 → 7/13 → 12/13 → 13/13). If your pass count is not
climbing like this, you are patching symptoms.

**Hybrid: run mobile alongside desktop from the FIRST loop iteration** — big
type, background layers and overlaps break silently on SP.

**Stopping criteria per section:** all `critical`+`high` pass, or 5
iterations, or 2 consecutive iterations without improvement (then flag the
residual instead of thrashing).

**Hybrid-residual rule:** a residual box-diff failure may be closed as
`hybrid-residual` ONLY when all three hold: visual-check passes on both
viewports; the owning section's review score (from crop pairs) is ≥7; and the
cause is named as one of *hand-measured-bbox* / *flow-first-recomposition
(Phase 4.5)* / *recorded intentAdjustment or addition*. Every hybrid-residual
is listed in the completion report with its cause. When choosing where the
next iteration goes, typography and detail devices usually buy more perceived
quality than another box-nudging pass.

Three bounds keep this disposition from becoming an escape hatch:

- **fv-critical elements are never hybrid-residual.** They pass, or the run
  is a `prototype` (gate G1).
- **`flow-first-recomposition` explains y-position and section order ONLY.**
  A width, height, font-size, or internal-layout delta citing recomposition
  is an unclosed failure — moving a section down the page does not change
  what the section looks like.
- **Volume is a verdict.** Residuals on >40% of manifest elements is not a
  disposition list, it is a fidelity failure (gate warning W3); the run
  reports as `prototype` via G2 regardless of how each row is worded.

## Phase 7 — Intent QA: visual-check + section review (FV gate)

```bash
node "$SKILL_DIR/scripts/visual-check.mjs" --html "$WORK_ROOT/site/index.html" \
  --manifest "$WORK_ROOT/manifest.json" --viewports 1440x900,390x844 \
  --out "$WORK_ROOT/reports/visual-check.json"

# Layout-law + responsive-integrity sweep (v7):
node "$SKILL_DIR/scripts/visual-check.mjs" --html "$WORK_ROOT/site/index.html" \
  --manifest "$WORK_ROOT/manifest.json" --widths 320,390,768,1024,1440,1728 \
  --out "$WORK_ROOT/reports/responsive-check.json"
```

For hybrid multi-frame runs, the report also binds the current manifest to
`contract-doctor.json` and `asset-preflight.json`. Missing, stale, or non-pass
pre-CSS receipts add `pipeline-pre-css-contract`; width/overflow diagnostics
remain useful, but the report's overall `ok` stays false. Asset-preflight
freshness includes the adopted raster files themselves: a changed path, size,
or SHA-256 fails even when the manifest hash still matches.

Hard checks: images load, no horizontal scroll, every meaningful element stays
at least 98% horizontally visible (within 8px), root `overflow-x:hidden/clip`
cannot conceal fixed-width content, same-document fragments resolve, every
manifest copy string is present, every `data-el` is present, frozen
structural-text `fontFamily` matches
the computed family, fv-critical structural text keeps its declared
`typeSpec.expectedVisualLineCount` at the canonical manifest viewport, structural
text has no undeclared scale/skew/rotation/
translation transform, structural text blocks do not overlap one another,
`full-bleed` backgrounds really are absolute full-width layers,
the manifested raster owner is visible and non-zero-area (an invisible
measurement proxy fails `surface-visible-owner`),
`mustNotCover` pairs don't intersect, fv-critical headings ≥28px on mobile,
CTA visible on mobile. The `--widths` sweep adds:
no horizontal scroll at any width, **no dead right gutter** (a left-pinned
fixed-width canvas at wide viewports fails), and the **absolute-position
audit** — any `[data-el]` computed `absolute`/`fixed`/`sticky` without the
matching `positioning` declaration (or a sanctioned decorative/overlay
`layerRole`) in the manifest is a `layout-law` violation.

Declared `decorativeCraft.microGeometry` adds pixel-small but hard checks:
circle aspect ratio, exact triangle vertex count, radial-ray count/side/
separation/target overlap, and angular alignment away from the target center.
This deliberately distinguishes “the numeral center defines the outward
direction” from “the rays begin at the numeral center.” Declared
`surfaceIntegration.edgeContact` likewise checks the rendered artwork-to-card
edge gaps so a generic padding utility cannot silently reframe edge-to-edge
illustration. Bind `data-el` to the primitive or artwork layer being judged;
binding a larger connector/card wrapper produces invalid evidence.

For background-removed raster illustrations, the pre-CSS asset report must
include `semantic-pixels-retained`. Review the protected feature crop at 200%
in addition to the whole illustration: hair and clothing surviving does not
compensate for a missing lip, eye, badge, or status dot. If the protected-color
check fails, regenerate/re-key before layout QA.

Critical Japanese headings additionally use
`typeSpec.responsiveLineContracts`. At each audited width, visual-check
clusters real text-node glyph rects into rendered lines, compares the exact
line strings, and rejects `forbiddenOrphanFragments`. This catches an authored
`<br>` followed by an accidental second wrap that strands `て`, `へ`, `が`, a
unit, or another short semantic fragment.

`font-family`, `font-face-load`, `font-weight-face`,
`typography-hierarchy`, `typography-whitespace`,
`typography-extreme-scale`, `typography-transform`, and `text-overlap` are
hard violations, not crop-pair review notes. A source-evidenced display distortion is the only
transform exception: manifest `typeSpec.transformException` must name the
decorative/display intent, reason, and readable evidence crop. Passing the
measured bbox never licenses distorted glyphs or a collision with the next
copy block.

Run browser QA after `document.fonts.ready`, then also inspect a blocked-font
or deliberately disabled-provider state. The selected non-system face must
appear as a loaded `FontFace` at the requested weight; computed CSS that still
lists the family while rendering a fallback is a failure. Capture loaded,
delayed-swap, and fallback crops. Provider failure may not silently become the
accepted geometry baseline.

Both render.mjs and visual-check.mjs force-load lazy images before measuring.
If you verify through another transport (MCP Playwright, in-app browser),
scroll to page end before probing or you will reproduce the false failure.

### Section review (hybrid: required — `reports/section-review.md`)

Geometry passed; now judge each section against its comp with your eyes. Cut
the rendered page into per-section strips (y/h from rects.json):

```bash
python3 "$SKILL_DIR/scripts/crop_asset.py" "$WORK_ROOT/reports/rendered.png" \
  --roi 0,<section.y>,1440,<section.h> --out "$WORK_ROOT/reports/sections/03-value.png" \
  --purpose evidence-crop
```

**Crop-pair evidence (hard rule 14) — the review's currency:**

```bash
python3 "$SKILL_DIR/scripts/crop_pair.py" \
  --comp "$WORK_ROOT/mockups/section-01-hero.png" --comp-roi 40,90,760,440 \
  --build "$WORK_ROOT/reports/rendered.png"      --build-roi 24,70,700,400 \
  --out "$WORK_ROOT/reports/crops/01-hero-lockup-pair.png" --zoom 2
```

Required pairs under `reports/crops/`, cited by path in the review: the FV
type lockup at ≥2× zoom, each measured line/run in an fv-critical mixed
lockup, every detail-inventory verdict, every adopted photo asset vs its comp
region, every clean background plate vs its contaminated/source reference
region, every generated/cropped lettering decal at 200% with exact text proof,
the rebuilt foreground layers that replaced baked-in raster UI/text, the CTA +
key numerals/dates/prices. A verdict row without a pair path is not a verdict.
"The CSS has it" is not evidence — judge what rendered
(`crop_pair.py` runs on Pillow alone; fallback mode never excuses skipping
this).

For every `card_artwork_plate`, review both the isolated plate and its final
crop-in-use. Confirm that the declared members still read as one coherent
composition, that structural copy/controls were not baked into it, and that
the outer CSS shell does not duplicate the plate's interior surface. If two or
more same-card rasters were split without independent-behavior evidence, mark
`asset-overdecomposition-risk` and return to pre-CSS planning.

For every critical raster, read the `surface-integration-valid` row from
`asset-preflight.json` and inspect its final crop-in-use. The pixel metrics
must agree with the declared mode: meaningful alpha for `alpha_floating`,
asset-owned edges for `opaque_full_bleed`, a named mask for
`opaque_masked_merge`, edge RGB within tolerance for `opaque_tone_matched`, or
source evidence for `intentional_frame`. An opaque uniform outer band inside a
CSS-owned card surface is a failure even when the subject itself is clean.

Also compare `sourceTopology`, `assetUnit.kind`, and all four `edgePolicy`
values against the source crop. A `section_field` must still read as a field in
the rendered section, not a right-side image card. A `floating_scene` must have
meaningful alpha and place its object(s) plus shadow directly on the Web field,
without a generator-white rectangle. Any mismatch returns to pre-CSS image
generation; CSS masking of an accidental panel is not a completion repair.
If feedback changes the topology itself, invalidate the affected crop, asset
receipt, expected bbox, box report, section review, and pixel evidence. Rebase
geometry from the source comp or newly approved reference, never from the
current DOMRect, then rerun downstream QA for that revision.

**Raster contamination proof (hard rule 23):** for each adopted raster asset,
save at least one 200% crop pair or zoom crop showing that the shipped asset
contains no baked-in text, logo, pseudo-text, signage, chart, card/chip, app
UI, or CTA-like foreground design. If the comp needed those foreground
devices, their DOM rebuilds need their own crop pairs and manifest elements.
Any visible contamination in the shipped raster caps `palette_photo` at 4 and
sets the corresponding foreground device disposition to `missing` unless the
user explicitly waived it verbatim.

**Lettering decal proof (hard rule 5):** for every `mediaClass:
"lettering-decal"` element, cite a 200% crop pair that proves the exact phrase
and glyph quality. Wrong kana/kanji, missing punctuation, added marks, clipped
ink, opaque boxes, or a generated note used for structural copy are `missing`.
Lettering decals are scored in detail devices, not in copy-presence, but their
target text must still be recorded in the manifest for review. The manifest
must carry `letteringProof {exactText, method, pairPath}`; `exactText` equals
`text.content`, the pair is a readable non-empty file, and raster strategies
must point to a readable shipped asset. `artifact_check.py` blocks otherwise.

### FV impression metrics (hybrid: required — `reports/impression-metrics.json`)

Box tolerances happily pass an FV whose *impression* has drifted. Four
numbers, all from existing scripts, make the drift measurable. Record each as
`{"metric", "comp", "build", "delta_pct", "tolerance_pct", "pass"}`:

1. **Lockup scale ratio** — `glyphHeight / frameHeight` of the tallest
   display block (Phase 1 already measured the comp side; snap_bbox or
   rects.json gives the build side at canonical width). Tolerance ±15%
   relative. This is the "poster vs timid" number.
2. **Type-run optical ratios** — for every fv-critical mixed-script run from
   Phase 1 (`AI`, numerals, kanji anchor, kana/particles, unit suffixes,
   emphasized words), record `runGlyphHeight / anchorGlyphHeight` and
   baseline offset vs the comp. Tolerance ±10% relative for height; baseline
   should be within the same visual band (record px or em residual). This is
   the "AI feels a size too small" number.
3. **Photo tone** — `sample_color.py` on the same photo ROI in comp and
   rendered FV; record the dominant hex pair and mean luminance delta.
   Tolerance: ΔL ≤ 20% relative (out of tolerance = the swapped/regraded
   photo changed the FV's mood — bright high-key comp shipped as a dark
   moody build is the field case). Palette axis caps at 5 while failing.
4. **Repeated-device scale** — width of one repeated device (card, chip,
   date tile) vs comp, ±15% relative, PLUS clip parity: a device the comp
   shows fully inside the frame may not be clipped by the viewport in the
   build (and vice versa). Composition axis caps at 5 while failing.

These feed gate G6. A failing metric is a Phase 5.5/6 work item, not a
review footnote.

### Copy proof (hard rule 21)

Manifest copy strings are only as good as your transcription — a comp that
says 実行 shipped as 実装 and every downstream check (copy-presence included)
passed, because they all compared against the same wrong transcription. So:
transcribe display copy from a ≥2× zoomed crop at Phase 1, and here re-read
every fv-critical + section-critical text off its crop pair, comp side vs
build side, glyph by glyph — kanji substitutions survive casual reading
precisely because they are plausible. One wrong glyph = verdict `missing`
(content bug), fixed before completion; it cannot be `adapted`.
This proof applies to structural HTML/CSS text. For lettering decals, use the
lettering decal proof above; do not let image text replace required HTML copy.

### Typography proof (hard rule 22)

For fv-critical display lockups, re-read the line/run crop pairs against the
Phase 1 type spec. The typography axis is capped at 5 while any required
run-level optical ratio is missing, or while a visible run such as Latin
`AI`, a date number, a unit suffix, kana particle, or emphasized word has
been flattened to the surrounding text. A run may be `adapted` only if the
review names both the preserved effect and the lost residual; "same CSS
font-size" is not a rationale.

The same cap applies when the chosen font crosses the source's frozen
letterform class (for example source gothic rebuilt as mincho), when an
fv/section-critical structural block lacks a 2–3 candidate same-class font
bake-off, or when glyph proportions are changed with CSS transforms. Review
the lockup together with the following copy block so a taller heading cannot
pass while colliding below. When a line begins with `「`, `『`, or comparable
opening punctuation, judge the visible ink edge, not the DOM box; record the
optical-hanging method and crop pair in `lineStartPunctuation`.

For every section-critical heading, compare the browser measurement to
`typeSpec.sourceImpression`: block width/height, max-line and glyph-height
ratios, tracking, line advance, ink density, viewport maximum-size ratio, and
heading-to-lead/body/label jump ratios. Judge desktop maximum scale and mobile
minimum scale separately. A heading fails when it is materially more timid,
more packed, or more ink-dense than the source even if its DOM bbox and text
content pass. Identical type measurements repeated across unrelated source
frames are a measurement defect, not a reusable design token.

Also compare every `typographyComposition` edge. Size ratios and signed weight
deltas must stay within their declared tolerances. Measure each vertical
text-block gap and divide it by the dominant block height; this catches both
crowding and generic excess padding. When `extremeScale.required` is true, the
canonical render must preserve the minimum dominant-block/frame ratio. A
smaller heading surrounded by more empty canvas is not equivalent composition.

Per section record:

1. Layout & composition — macro placement right?
2. Display-type scale ratio vs hypotheses.md — poster or timid?
3. Multi-line poster geometry — do line bboxes, block-height ratio,
   line-advance ratio, and signed interline gap match the source, or did the
   heading collapse into a dense/timid block despite the correct line count?
4. Letterform class + run-level optical ratios vs hypotheses.md — did the
   selected family stay gothic/mincho/rounded/display as observed, and are
   Latin/numerals/kana/kanji and emphasized words visually balanced like the
   comp?
5. Palette & photo mood — **measure the palette, don't vibe it**: run
   `sample_color.py` on a comp ROI and the same ROI of your strip; record the
   hex pairs. A washed/pastel build against a crisp comp is measurable drift.
6. **Detail disposition** — walk the Phase 1 inventory item by item, judged
   from zoomed crop pairs. Verdicts are defined, not vibes:
   - `present` — the device's *specific content* (glyph, icon subject, chip
     text, number) AND its rendering craft survive. A generic stand-in (a
     straight line for a curve, a flat card for glass) is NOT present.
   - `adapted` — states BOTH what was preserved AND what was lost, and why
     the loss is acceptable. "Adapted" with no named loss is `missing` in a
     costume. For a photo/illustration device, `adapted` requires the same
     media class to have survived — a real raster shipped, re-cropped or
     re-graded. A photographic subject that was dropped, or reclassified to
     `svg`/`ui-mock`/`css` and replaced with comp-absent UI, is `missing`, never
     `adapted` (rules 24–25): losing the human the comp was built around is not
     an acceptable adaptation of a portrait, and gate G8 rejects the `adapted`
     label for a photo device that shipped no raster.
   - `missing` — fix before completion, or escalate to `waived`.
   - `waived` — only with the user's verbatim words, cited. Paraphrases of
     their priorities are self-waivers and don't count.
   - Before crop judgment, inspect `generic-symbol-standin` findings. Any
     emoji/dingbat-only leaf inside a source-specific line-art, illustration,
     UI, composite-card, or decorative-geometry device is `missing` unless the
     source-evidenced craft contract explicitly permits that exact text glyph.
6. **Raster decomposition disposition** — for every photo/illustration used
   behind copy or UI, state whether the shipped raster is clean. If a source
   comp fused background + foreground, list the generated/replaced clean
   plate and the DOM/SVG ids that now carry the foreground type/UI. A fused
   crop reused as-is is not `adapted`; it is `missing` plus an asset failure.
7. **Generated lettering disposition** — for every lettering decal, list the
   generated/replaced/cropped asset, exact text, transparent/edge quality,
   anchor relationship, and crop-pair path. A generated lettering image with
   wrong Japanese is `missing`, even if the mood is close.
8. Score 0–10 on FOUR axes — composition, typography, palette & photo,
   detail devices. **The section score is the MINIMUM of the four axes.**
   Anchors: 8+ = the designer recognizes their work; 6–7 = structure right,
   treatment diluted; 4–5 = layout right, devices dropped/genericized (the
   classic inflated self-review sits here calling itself 8); ≤3 = broken.

For the final review bundle, keep lossless PNG only for pixel/measurement
evidence. Store visual crop pairs as WebP or high-quality JPEG when no numeric
pixel operation consumes them, and build a section contact sheet as an index
to the original-size pairs. Move discarded iterations to `reports/debug/`;
artifact gates need final evidence, not every exploratory screenshot.

**A section below 7 goes back to implementation before the job is done.**

**Calibration & independence:** implementing agents grade their own work high.
For hybrid multi-frame work, invoke `visual-qa-pixel-polish` after fidelity QA
and require a different agent/session or human to review crop pairs only—no CSS,
implementation rationale, or self-score. Record both identities, reviewed
pairs, per-section/page scores, and top gaps. The lower score controls; a delta
above `reviewPolicy.maxIndependentScoreDelta` returns to implementation.

Two structural checks on your own scoring:

- **Uniform-threshold scoring**: a review where every section lands exactly
  on the pass bar is the signature of scoring backwards from the gate (field
  run: all sections 7/7/7/7… in the review, 46/100 reproduction when the
  same agent was asked frankly afterwards). The gate flags it (W1); when you
  see yourself writing the third 7 in a row, stop and re-judge from the
  pairs with the impression metrics in hand.
- **Top-5 visible gaps (required table)**: name the five most visible
  differences between comp and build — each with its crop-pair path, the
  axis it hurts, and either the planned fix or the recorded residual cause.
  If you cannot fill five rows, say so explicitly. This forces the honest
  retro INTO the artifact instead of leaving it for the user to extract.

Scores are also serialized to `reports/section-scores.json` for Phase 10:
`{"sections": [{"id", "axes": {composition, typography, palette_photo,
detail_devices}, "pairs": [paths]}], "page": {"score" | "axes"},
"dispositions": [{"inventoryId", "device", "verdict", "pairPath" | "waiverQuote"}],
"webQualityScore": n, "compFidelityScore": n,
"reviewProvenance": {implementer, independent}}`. `webQualityScore` and
`compFidelityScore` are final-report scores; they do not replace the
section/page axis-min fidelity gates.

**Additions table (separate):** every `addition: true` element with its
`additionReason` and `mustNotCover` outcome. Additions never raise fidelity
scores.

**Page-flow review (multi-frame: required):** start from the computed
`reports/page-flow.json`, not a prose impression. It must cover every section
strategy and every adjacent seam, compare actual heights with the normalized
reference-frame height, audit computed clipping against `overflowPolicy`, and
point to a readable crop/screenshot for every seam. Then judge connective
motifs and the scroll narrative against Phase 4.5. Score the page-as-a-page
0–10 (axis-min anchors); either a `needs_work` page-flow report or a below-7
flow score goes back to implementation. Four 8/10 sections can compose a 5/10
page.

For every seam with `continuity.required: true`, the crop must show meaningful
content from both sections: outgoing environment/field and at least one
manifested incoming preview target. Review both desktop and mobile crops, not a
thin boundary strip. `page_flow_check.py` additionally requires the two image
paths plus a passing `seam-pixel-check/v1` whose image hash still matches the
sampled screenshot and whose `from`/`to` pair matches the seam. Judge the
four-layer handoff (outgoing environment, opaque target surface, connective
motif, incoming preview) and fail a generic centered ellipse or divider-only
crop even when its pixels are technically continuous.

### FV QA gate (record in section-review.md)

- [ ] Photo reads as seamless environment — no hard-rectangle termination
- [ ] Every photo/background raster is clean: no baked-in text, logos, UI,
      chips, charts, CTA-like marks, or pseudo-text at 200% zoom
- [ ] Every photo-led comp region ships a real raster (`generated`/`replace`/
      `crop-asset`) or an honest `placeholder` after a recorded failed
      generation attempt — none silently reclassified to `svg`/`css`/`ui-mock`
      or dropped for invented UI (rules 24–25)
- [ ] Foreground copy/UI that existed in the raster comp has been rebuilt as
      DOM/SVG layers with crop-pair proof
- [ ] Main heading unmistakably the protagonist (size, contrast)
- [ ] Type does not collide with the subject's face / key photo detail
- [ ] Overlay gradient guarantees copy legibility at every breakpoint
- [ ] Fixed/sticky global UI (nav, vertical logo/title, edge labels) is
      intentionally declared and does not cover FV content; mobile release
      behavior is defined
- [ ] FV works *as a poster* incl. CTA, signature, year, vertical label
- [ ] On SP the heading has not shrunk into a caption; FV height sane
- [ ] Typographic treatment matches the comp: tightness, leading, band,
      outline, in-line scale steps, weight class, serif accents
- [ ] Source letterform class matches the selected font; the real copy was
      compared in 2–3 same-class candidates at zoomed glyph scale
- [ ] Structural text has untransformed glyph proportions (`transform:none`)
      unless a source-evidenced display exception is declared; it does not
      overlap the following structural copy at desktop or mobile
- [ ] A line-start opening bracket is optically hung so its visible ink edge,
      not its advance-width box, aligns with the intended text edge
- [ ] Mixed-script type runs match the comp's optical balance: Latin
      acronyms/numerals are not a size too small next to kanji, kana/particles
      keep their measured scale, baselines look intentional
- [ ] Every photo-class visual is a real raster — no vector/CSS stand-in
- [ ] Generated lettering decals have exact text, clean transparency, and
      crop-pair proof; no structural copy is hidden in an image
- [ ] Decorative devices at comp craft (curves are curves, gradients retain
      their topology, glass is glass); `decorativeCraft` medium and evidence
      match the source rather than flattening an organic field to bands
- [ ] Staggered card SHELLS preserve the comp offsets; photo placement was not
      shifted inside aligned cards as a substitute, and photo/card edges use
      the recorded tone-merge, mask, cutout, or hard-edge treatment
- [ ] Gradient/mask ownership is correct and clipped by the recorded rounded
      frame when applicable; no page-wide veil substitutes for a frame-local
      field
- [ ] Photo topology matches the source (`full-frame-plate`, contained,
      subject cutout over plate, or object-detail tone-merged); a full-frame
      CTA plate is not misread as a right-half background

Each box is answered from a crop pair, path cited. Any "no" → back to the
layer plan or typography, not to pixel-nudging.

## Phase 7.5 — Motion runtime QA (conditional)

When `motion.required` is true, run:

```bash
node "$SKILL_DIR/scripts/motion-check.mjs" \
  --html "$WORK_ROOT/site/index.html" --manifest "$WORK_ROOT/manifest.json" \
  --viewports 1440x900,390x844 --out "$WORK_ROOT/reports/motion-check.json"
```

The report samples normal motion, `prefers-reduced-motion: reduce`, and a
JavaScript-disabled mobile page. It requires real runtime events on contracted
targets, settled visibility for critical content, valid CTA/fragment
destinations, and a manifest SHA receipt. Missing/non-pass evidence activates
completion gate G13. Static projects (`motion.required: false`) return
`not_required` without launching a browser.

If the standard motion runner fails after its bounded browser retries, do not
retry it repeatedly. Follow the browser transport ladder and write one
`motion-report/v1` fallback artifact that records the failed command/error and
equivalent normal, reduced-motion, and JavaScript-disabled measurements. A
cross-section cue passes only when the cue and seam are visible normally, the
animation is absent under reduced motion, the same-document fragment resolves,
and the incoming heading remains visible without JavaScript. A handwritten
prose note without those state rows does not clear G13.

## Phase 8 — Pixel QA: masked pixel diff (pixel-clone; hybrid: FV frame)

```bash
python3 "$SKILL_DIR/scripts/pixel_diff.py" "$WORK_ROOT/mockup.png" "$WORK_ROOT/reports/rendered.png" \
  --manifest "$WORK_ROOT/manifest.json" --out-heatmap "$WORK_ROOT/reports/diff.png" \
  --out "$WORK_ROOT/reports/pixel-report.json"
```

Text auto-masks. In hybrid, FV photo/illustration rows with
`assetStrategy: generated|replace` also auto-exclude because pixel identity is
impossible by construction. Opaque source-comparable foreground surfaces marked
`pixelDiffForeground: true` are carved back into comparison; their structural
glyphs remain masked. Split button/card shells and text labels into separate
manifest rows; a text-bearing carve-out is blocked. Only rows belonging to the primary FV source are
used, so below-FV frame-local bboxes cannot mask unrelated FV pixels. The
report includes `total_px`, `masked_px`, `compared_px`, total
`comparison_coverage`, `generated_media_coverage`, and
`eligible_comparison_coverage`. Default minimum coverage is 0.50 for
pixel-clone and 0.20 for hybrid/production, applied to the eligible
non-generated area when present. Below the floor the verdict is
`insufficient_coverage`, even if every remaining pixel matches.

A verified generated/replaced full-frame hybrid plate can leave zero eligible
pixels. That produces `not_applicable_generated_media`, not `good`; G3 accepts
it only when the report's media ids bind to real critical manifest rows and
asset policy G9, impression G6, box, crop-pair, artifact, and other gates pass.
This is not a manual mask waiver. A giant ad-hoc/text mask that leaves only a
small corner remains insufficient; reduce it or use an earned
`--no-pixel-evidence` reason at completion.
Read the heatmap yourself: concentrated red = object-fit cropping, gradient
direction, shadow/radius issues. Scattered speckle = anti-aliasing, ignore.
Multi-frame hybrid: run on the FV frame (photo+text masked) — box tolerances
happily pass an FV where *everything* is slightly off; the heatmap catches a
washed or subtly distorted first view. Skippable only with a recorded failed
OpenCV install attempt.

## Phase 9 — Responsive

- pixel-clone / production: after desktop matches.
- hybrid: SP has been checked since Phase 6; this phase *finishes* it.

Derive SP behavior from structure when no SP comp exists: grid → stack; true
overlap → release or re-anchor (vertical label → horizontal eyebrow);
oversized type → `clamp()` with a floor that keeps the poster feel (28px
mobile-heading check); full-bleed background → keep full-bleed, move focal
point with `object-position`; dark bottom panel → sticks or flows per content
length. Keep `layerRole`/`backgroundBehavior` invariant across breakpoints —
adapt size/focal-point, not the layering. If an SP mockup exists, repeat
Phases 1–7 against it at its width. The `--widths` sweep is the exit check:
320/390/768/1024/1440/1728 all hold. `overflow-x:hidden/clip` on the root is
never an acceptable way to make a fixed canvas pass; use the per-element
visible-ratio details to find the clipped grid/card/copy.

## Phase 9.5 — Artifact checklist (pre-completion evidence audit)

First validate the machine shape of the completion inputs. Start scores from
`templates/section-scores.min.json`; `sections` and `dispositions` are JSON
arrays, never objects keyed by id.

```bash
python3 "$SKILL_DIR/scripts/contract_doctor.py" "$WORK_ROOT" \
  --phase completion --out "$WORK_ROOT/reports/contract-doctor-completion.json"
```

This must pass before the artifact checklist. It turns malformed inputs into
targeted JSON findings instead of Python tracebacks. It does not score the page
and cannot replace the evidence-density or completion gates.

Run the checklist before `completion_gate.py`. This is not another visual
score; it is an evidence-density audit for the exact failures that create a
presentable page with weak reproduction proof: too few crop pairs, generated
assets without prompt/path/contamination evidence, bbox edits without a
measurement ledger, FV `needs_work` buried below a visual-check pass, and
single blended "overall" scores. It also reruns the Phase 3.5 source policy so
a clean subcrop of a fused, compositionally larger photo field cannot slip
through late. In a multi-frame run it also requires the computed page-flow
artifact; a missing or failing report is not replaced by a prose review.

```bash
python3 "$SKILL_DIR/scripts/artifact_check.py" "$WORK_ROOT" \
  --page-flow "$WORK_ROOT/reports/page-flow.json" \
  --out "$WORK_ROOT/reports/artifact-check.json"
```

Status meanings:

- `pass` — the evidence bundle is dense enough for Phase 10.
- `needs_work` — the build can still report as a `prototype`, but the final
  report must lead with the checklist findings; do not call the run complete.
- `blocked` — evidence is missing/invalid (unreadable generated asset, missing
  section review, critical `bboxSource: implementation-derived`, etc.). Fix the
  artifact before running the completion gate, or report blocked.

Required checks:

- **Crop-pair coverage**: at least one declared, readable pair per scored
  section, and every detail disposition has a pair path or a verbatim user
  waiver. A detail inventory row without either is unjudged.
- **Detail inventory identity**: every `manifest.detailInventory.id` has exactly
  one `disposition.inventoryId`. Source-specific adapted volume above
  `reviewPolicy.maxAdaptedSourceSpecificRatio` is `needs_work`.
- **Independent crop review**: a different human/session reviews crop pairs
  only, covers every section, records page/section scores and top gaps in
  `reviewProvenance`, and uses the lower score. A delta above
  `maxIndependentScoreDelta` returns to implementation.
- **FV-first warning**: fv-critical box failures block below-FV polish; FV pixel
  `needs_work` triggers a red warning that the final status must lead
  `prototype`/`needs_work` even when visual-check passes. The only non-pixel
  path is machine-issued `not_applicable_generated_media` for a manifest-bound
  full-frame generated/replaced hybrid plate; asset and impression gates remain
  mandatory.
- **Critical boxes**: every fv-critical, section-critical, and manifest
  priority critical/high row passes. Y-only recomposition rows are excluded;
  X/W/H failures on a y-waived row remain failures.
- **Evidence identity/freshness**: manifest, box report, scores, review, and FV
  pixel inputs receive SHA-256/size/mtime receipts. Scores/reviews older than
  the latest box report, a pixel report older than the manifest, or any input
  changed after artifact-check require a rerun.
- **BBox ledger**: every FV/section-critical bbox has `measurementRef`;
  tolerance overrides have `toleranceReason`; critical
  `implementation-derived` bboxes are invalid evidence.
- **Generated asset completeness**: generated assets include prompt,
  generator, local `workspacePath`, and contamination proof or
  `photo-asset-review.md` row.
- **Source/composition policy**: every critical photo declares the full-field
  overlap state and visual role. Fused-source `crop-asset`, unproven
  `cropPreservesComposition`, missing crop/generated/replacement evidence, and
  unearned stock/placeholder fallback are blocked.
- **Two-track scoring**: final review separates WEB品質/Web quality from
  カンプ再現度/comp fidelity. Hybrid prototypes must not hide fidelity failure
  inside a usable-LP score.
- **Web-native page flow**: every section has a height/density/overflow
  strategy, every adjacent seam has readable evidence, and the rendered page
  is not a repeated frame-height stack unless a verbatim user intent permits
  it.

## Phase 10 — Completion gate (all modes; the verdict is computed)

```bash
python3 "$SKILL_DIR/scripts/asset_preflight.py" "$WORK_ROOT/manifest.json" \
  --work-root "$WORK_ROOT" --out "$WORK_ROOT/reports/asset-preflight.json"
python3 "$SKILL_DIR/scripts/contract_doctor.py" "$WORK_ROOT" \
  --phase completion --out "$WORK_ROOT/reports/contract-doctor-completion.json"
python3 "$SKILL_DIR/scripts/page_flow_check.py" "$WORK_ROOT/manifest.json" \
  "$WORK_ROOT/reports/rects.json" --work-root "$WORK_ROOT" \
  --out "$WORK_ROOT/reports/page-flow.json"
python3 "$SKILL_DIR/scripts/artifact_check.py" "$WORK_ROOT" \
  --page-flow "$WORK_ROOT/reports/page-flow.json" \
  --out "$WORK_ROOT/reports/artifact-check.json"
python3 "$SKILL_DIR/scripts/completion_gate.py" "$WORK_ROOT/manifest.json" \
  "$WORK_ROOT/reports/box-report.json" \
  --visual-check "$WORK_ROOT/reports/visual-check.json" \
  --widths-check "$WORK_ROOT/reports/responsive-check.json" \
  --scores "$WORK_ROOT/reports/section-scores.json" \
  --artifact-check "$WORK_ROOT/reports/artifact-check.json" \
  --fv-pixel "$WORK_ROOT/reports/fv-pixel-report.json" \
  --impression "$WORK_ROOT/reports/impression-metrics.json" \
  --page-flow "$WORK_ROOT/reports/page-flow.json" \
  --out "$WORK_ROOT/reports/completion-verdict.json"
```

Gates: G1 fv-critical + section-critical + priority critical/high boxes 100%;
G2 overall box pass rate (Y-only waived rows excluded from both operands)
≥ 0.90 pixel-clone / 0.70 production / 0.80 hybrid; G3 FV pixel
verdict good/acceptable, or machine-issued `not_applicable_generated_media`
for a manifest-bound full-frame hybrid plate while G6/G9 pass; G4 visual-check + widths sweep clean; G5 every
section and the page ≥ 7; G6 impression metrics in tolerance; G7 no
`missing` dispositions; G8 photo-class asset reality — an fv/section-critical
`mediaClass: photo`/`illustration` element that ships no raster
(`generated`/`replace`/`crop-asset`), and a section-review disposition that
calls a photo/portrait device `adapted`/`present` while the build ships no
raster at all, are both `prototype` (the reclassify-to-svg / drop-the-photo
escape that the self-scored G5/G7 miss); G9 reruns Phase 3.5 and returns
`blocked` for invalid source decisions such as a fused full-field environment
shipped as a narrower clean crop, missing on-disk proof, or an unearned
fallback. Fidelity failures → `prototype`; invalid policy or missing/unreadable
evidence → `blocked` (in genuine degraded modes, pass
`--no-pixel-evidence` / `--no-impression-evidence` with the recorded
reason — earned, per fallbacks.md, not asserted).

G10 binds multi-frame completion to `page-flow.json`: missing section/seam
contracts, repeated source-frame-height slabs, blanket clipping, flat
unevidenced seams, or missing seam files make the verdict `prototype` or
`blocked`. W4 names the repeated-frame-height pattern in the warnings. Only
an explicit `uniformHeightIntent`, `allSectionsClipIntent`, or
`allHardCutIntent` containing a reason and the user's verbatim quote may waive
the corresponding pattern.

G11 binds completion to `artifact-check.json`: `needs_work` makes the verdict
`prototype`; missing/blocked/internally inconsistent reports are `blocked`.
The manifest, box-report, and section-scores SHA receipts must still match the
files passed to completion_gate, preventing an audit from being reused after
inputs changed.

G12 applies `reviewPolicy`: independent crop-only section/page scores and the
lower comp-fidelity score control completion. Missing independence, incomplete
section coverage, a below-7 independent score, or material self/blind delta is
`prototype`/`needs_work`, never a self-certified complete.

The contract (hard rule 20): **the completion report's headline status is
the script's status.** `prototype` is an honorable outcome — report it as
"usable prototype; not yet a faithful implementation", cite the
`prototype_reasons` verbatim, and let the user decide whether to iterate.
What is not honorable is prose that upgrades it: the run that motivated
this gate had box 4/23, FV pixel `needs_work`, and a completion message
that led with 完了しました. Warnings (W1 uniform scoring, W2 pair-less
scores, W3 residual volume) go into the report unedited.
