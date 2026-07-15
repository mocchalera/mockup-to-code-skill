# Phase 7 section review — <project>

<!--
Required hybrid evidence (work/reports/section-review.md). One block per
frame, FV first. Cut the rendered page into per-section strips first
(crop_asset.py with y/h from rects.json; or sips/Playwright clip in
fallback environments) and view strip vs frame side by side at the same
width — do not judge from the full-page screenshot.

Judge each detail device from a SAVED CROP PAIR (principle 14):
`scripts/crop_pair.py --comp <frame> --comp-roi … --build <strip|render>
--build-roi … --out work/reports/crops/<NN>-<device>-pair.png` — never
from the section thumbnail, the CSS, or memory. At section scale every
drop looks fine, and "the DOM has it" is not evidence that it rendered.
A verdict row without a pair path is not a verdict.

Verdict definitions (principle 11/12 — these are defined, not vibes):
- present: the device's SPECIFIC content (glyph, icon subject, chip text,
  number) and treatment survive IN THE PAIR IMAGE. A generic stand-in is
  NOT present.
- adapted: state BOTH what was preserved AND what was lost, and why the
  loss is acceptable. No named loss = it's `missing` wearing a costume.
  An addition covering a comp device is never "adapted".
- missing: fix before completion, or escalate to waived.
- waived: only with the USER'S VERBATIM WORDS (quote their instruction /
  handoff line, cite where it's from). Your paraphrase of their
  priorities ("the handoff prioritizes conversion") is a self-waiver —
  those don't exist.

Calibration: implementing agents self-score ~3 points high (field: self
8+/user 5; self 7.8/user 3; self 7.5–8/user 3.7). If possible, have a
different agent / fresh session run this review from the crop pairs.

Media-class rule (principle 13): a photo-class visual replaced by a
vector/CSS/flat-avatar stand-in is `missing` BY DEFINITION — never
`adapted`, whatever the rationale (rights, no generator, "text-free") —
and caps its section score at 4. Typography rule: a display block whose
source letterform class, in-line scale steps / weight class / serif accents
were flattened or whose glyph proportions were changed with CSS transforms
is at best `adapted` with the loss named. An undeclared transform or visible
structural-text overlap fails the automated visual check and returns to
implementation.

Lettering-decal rule (principle 5): generated/cropped image text is allowed
only for non-structural expressive lettering (speech bubbles, signatures,
decorative notes). It needs exact-text proof at 200% and clean transparent
edges. A heading, CTA, nav, body label, price/date, or legal note hidden in an
image is `missing`, not an adaptation.

Scores are vs the comp frame, 0–10, as the frame's designer would score
it, on FOUR axes: composition / typography / palette&photo / details.
THE SECTION SCORE IS THE MINIMUM OF THE FOUR AXES, never the average — a
9-composition/4-typography section IS a 4. Typography is capped at 5 when
fv-critical run-level optical sizing is missing or flattened (e.g. `AI`
renders a size too small beside kanji). Anchors (per axis): 8+ =
designer recognizes their work, devices intact; 6–7 = structure right,
some treatment diluted; 4–5 = layout right, devices dropped/genericized
(the classic inflated self-review sits here while calling itself 8);
≤3 = structure broken. A section below 7 goes back to implementation
before completion is reported.
-->

**Overall**: FV <n>/10 · page average <n>/10 · **page-flow <n>/10**
(target: FV ≥ 7, average ≥ 7, page-flow ≥ 7)
**Final self-scores (separate, never averaged into one claim)**:
- **WEB品質 / Web quality**: <n>/100 — backed by responsive, accessibility,
  information architecture, and production-readiness evidence
- **カンプ再現度 / Comp fidelity**: <n>/100 — backed by box diff, FV pixel diff,
  crop pairs, section scores, and top visible gaps
**Computed status lead**: <copy `reports/completion-verdict.json.status`
verbatim: complete / prototype / blocked>
**Fix list carried back to implementation**: <items or "none">

---

## FV — `work/references/01-<name>.png` vs `work/reports/sections/01-<name>.png`

**FV QA gate** (your eyes, desktop AND mobile):

- [ ] Photo reads as a seamless background — not a framed card that cheapens
      it; no photo edge terminates in a hard rectangle (each edge bleeds,
      masks into the field, or is comp-framed — per the layer plan's
      edgeTreatment)
- [ ] Main heading is unmistakably the visual protagonist — scale ratio: comp <0.NN> vs build <0.NN>
- [ ] Type does not collide with the subject's face / key photo detail
- [ ] Overlay gradient guarantees copy legibility at every breakpoint
- [ ] Fixed/sticky global UI (nav, vertical logo/title, edge labels) is
      intentionally declared and does not cover FV content; mobile release
      behavior is defined
- [ ] The FV works *as a poster* including CTA, signature, year, vertical label
- [ ] On SP the heading has not shrunk into a caption; FV height is sane
- [ ] Typographic treatment matches the comp: tightness, leading, band,
      outline, in-line scale steps, weight class, serif accents (type
      spec) — pair: `work/reports/crops/01-fv-lockup-pair.png` (≥2× zoom)
- [ ] Source letterform class matches the chosen family, supported by 2–3
      same-class candidate crop pairs (no gothic↔mincho substitution)
- [ ] Structural text uses untransformed glyph proportions unless the source
      visibly requires a documented display exception; no heading collides
      with the following copy at desktop or mobile
- [ ] Line-start opening punctuation is optically aligned by visible ink edge
      and documented in `lineStartPunctuation`
- [ ] Mixed-script runs match the comp's optical balance — Latin/numerals
      not too small beside kanji, kana/particles keep measured scale,
      baseline offsets intentional — pair(s): `work/reports/crops/01-fv-type-runs-pair.png`
- [ ] Per-line lockup boxes hit their comp bboxes (no crushed tracking /
      flattened steps) — from the box report's line-span entries
- [ ] Every photo-class visual is a real raster (generated / stock /
      layered) — no vector, CSS or flat-avatar stand-in (principle 13)
- [ ] Every lettering decal has exact text, clean transparency, correct
      hand/mood, and crop-pair proof; no structural copy is hidden in an image
- [ ] No addition (ribbon/nav/badge) covers or crops a comp device (principle 12)
- [ ] FV masked pixel-diff heatmap read (no veils/washes/band shifts) —
      or the failed OpenCV install attempt is recorded verbatim
- [ ] Decorative devices at comp craft — curves are SVG beziers with the
      comp's sweep, glass panels have blur/translucency, shadows match the
      comp's softness (pair paths; a straight line standing in for a curve
      is `missing`)
- [ ] Layer topology matches the comp: `photoCompositionMode`, rounded
      `clipOwner`, and mask/gradient ownership are visible in the pair
- [ ] Staggered card SHELL offsets match; photo/card joins use the recorded
      tone-merge, mask, cutout, or hard-edge method rather than pasted images
- [ ] Layout law holds: no undeclared `position:absolute` on content
      elements; `--widths` sweep (390–1728) clean — no horizontal scroll,
      no dead right gutter (`work/reports/responsive-check.json`)

**Palette — measured, not vibed** (sample_color on the same ROI, comp frame vs strip):

| ROI (what) | comp hex | build hex | verdict |
| --- | --- | --- | --- |

**Photo mood** (each replace/generated asset vs comp: subject / mood / grade / aspect — pair path each):

**Typography proof** (fv-critical display lockup; crop-pair and metrics):

| run/block | source class | chosen family / bake-off pair | comp optical ratio | build optical ratio | transform / punctuation / overlap verdict |
| --- | --- | --- | --- | --- | --- |
| e.g. `AI` vs kanji anchor | gothic | Noto Sans JP / crops/font-noto-pair.png | 1.10× | 1.08× | none / n/a / clear — present |
| e.g. `「聴ける」` | gothic | Noto Sans JP / crops/font-noto-pair.png | 1.00× | 1.02× | none / opening bracket hung / clear — present |

**Layer topology proof** (photos, masks, staggered cards, decorative fields):

| device | composition mode / craft | clip owner | shell/card-photo behavior | pair | verdict / residual |
| --- | --- | --- | --- | --- | --- |
| e.g. CTA portrait | full-frame-plate | rounded CTA frame | left mask hides plate; subject remains full-scale | crops/cta-topology-pair.png | present |

**Lettering decal proof** (non-structural generated/cropped image text):

| decal | target text | pair (`work/reports/crops/…`) | transparency/edge | anchor relationship | verdict / residual |
| --- | --- | --- | --- | --- | --- |
| e.g. handwritten bubble | 「聴くから、つながる。」 | crops/01-fv-bubble-pair.png | clean | follows photo shoulder, avoids face | present |

**Detail disposition** (from hypotheses.md inventory — every row, incl. the environment/ground row, judged from its pair):

| # | device (specific content) | pair (`work/reports/crops/…`) OR waiver quote | verdict | preserved / lost (required for adapted) |
| --- | --- | --- | --- | --- |

**Axis scores**: composition <n> · typography <n> · palette&photo <n> · details <n>
**Score (= min of axes)**: <n>/10 — top gaps: 1) … 2) … 3) …

---

## <NN>. <section name> — `<frame>` vs `<strip>`

1. **Layout & composition**:
2. **Display-type scale** (comp <0.NN> vs build <0.NN>):
3. **Typography proof** (source class, family bake-off, line/run crop pairs,
   optical ratios, transform/punctuation/overlap residuals):
4. **Palette & photo mood** (sampled hex pairs + photo pair paths):

| ROI (what) | comp hex | build hex | verdict |
| --- | --- | --- | --- |

5. **Essence ledger check** (each must-survive bullet: survived? how?):
6. **Lettering decal proof** (if any: exact text, transparency, anchor relationship, pair path):
7. **Layer topology** (photo mode, clip owner, staggered shells, card-photo
   edge treatment, decorative-field craft — each from its pair):
8. **Detail disposition** (every row, incl. environment/ground, from its pair):

| # | device (specific content) | pair (`work/reports/crops/…`) OR waiver quote | verdict | preserved / lost (required for adapted) |
| --- | --- | --- | --- | --- |

**Axis scores**: composition <n> · typography <n> · palette&photo <n> · details <n>
**Score (= min of axes)**: <n>/10 — top gaps:

---

## Additions (business-requirement elements — NOT comp devices)

<!-- Every manifest element with addition: true. Additions never appear
in detail dispositions and never raise a fidelity score; they are
audited for occlusion (principle 12). -->

| element | additionReason (quote the requirement) | mustNotCover outcome |
| --- | --- | --- |

---

## Page-flow review (multi-frame: REQUIRED)

<!-- Judge the assembled page against the Phase 4.5 plan. Scroll the real
page or read the full-page screenshot top-to-bottom. Per-frame scores do
NOT average into this — four 8/10 sections can compose a 5/10 page. A
below-7 flow score goes back to implementation like a failing section. -->

**Seams** (one line per boundary — as designed in the seam plan?):

**Computed page-flow**: pass / needs_work / blocked — `work/reports/page-flow.json`

**Rendered height rhythm**:

| section | strategy / density | actual px | reference ratio | overflowPolicy | computed overflow | note |
| --- | --- | ---: | ---: | --- | --- | --- |
| 01 | | | | | | |

**Seams** (one line per boundary — as designed in the seam contract?):

| seam | type / transition space | bridge element | evidence path | verdict / note |
| --- | --- | --- | --- | --- |
| 01→02 | | | `work/reports/crops/seam-01-02.png` | |

**Connective motifs actually recur?** (one system, or one appearance per frame?):

**Whitespace & density rhythm** (breathing page, or a stack of 16:9 slabs?):

**Scroll narrative holds?** (does each boundary pull the reader onward?):

**Page-flow score**: <n>/10 — top gaps:

---

## Artifact checklist handoff (Phase 9.5)

<!-- Run asset_preflight.py before CSS and again before artifact_check.py;
then run artifact_check.py before completion_gate.py. Paste both headlines.
If either is needs_work, the final report must lead with that limitation even
if the page looks presentable. If blocked, do not claim completion. -->

**Asset preflight**: pass / needs_work / blocked — `work/reports/asset-preflight.json`
**Source overlap decisions**: all critical photos classified? yes/no; any fused-source crop reuse? yes/no
**Artifact check**: pass / needs_work / blocked — `work/reports/artifact-check.json`
**Page flow**: pass / needs_work / blocked — `work/reports/page-flow.json`; repeated-frame lock? yes/no; seam evidence complete? yes/no
**Crop-pair count**: <n> declared; <n> readable
**Box diff**: <pass>/<total> pass; manifest tolerance overrides: <n> (reviewed? yes/no)
**FV pixel**: good / acceptable / needs_work / missing
**Generated assets**: <n> adopted; prompt/path/generator/contamination proof complete? yes/no
**BBox ledger**: all FV/section-critical elements have `measurementRef`? yes/no
**Top-5 visible gaps**:

| rank | gap | evidence pair | axis hurt | fix or residual cause |
| ---: | --- | --- | --- | --- |
| 1 | | | | |
