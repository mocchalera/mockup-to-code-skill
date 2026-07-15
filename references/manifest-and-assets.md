# Phases 3 / 3.5 — Element manifest, asset policy, and the pre-CSS gate

Read this before writing the manifest. Companion: `measurement.md` (how the
bboxes were produced), `composition.md` (layer plan fields).

## The manifest is the QA contract

For hybrid multi-frame work, first copy
`templates/manifest.hybrid-multiframe.min.json` to
`"$WORK_ROOT"/manifest.json`, then replace every TODO and example measurement.
Do not improvise the JSON container shapes. The starter makes photo
regeneration, viewport-global chrome, page composition, and FV line-count
contracts first-class instead of discovering them through late gate errors.
Write the result per `schemas/element_manifest.schema.json`.
Every important element gets: `id`, `el` (its `data-el` value), measured
`bbox`, `bboxSource`, `measurementRef`, `priority`, and for text: frozen real
`fontFamily` + `maskInPixelDiff: true`. Set top-level `mode` and the required
Phase 1 declaration `photoLed: true|false`. `photoLed: true` requires at least
one fv/section-critical `mediaClass: photo|illustration` row; `false` is an
explicit assertion that no authoritative comp is photo-led. In hybrid also
set per-element `qaPriority` (`fv-critical` / `section-critical` /
`decorative` / `detail`) and `textRecreation`. Also carry the Phase 1
construction plan:
`placementScope`, `anchorTarget`, `relationshipToPreserve`, and
`responsiveBehavior` for any layered/fixed/decorative element. In a multi-frame
comp set additionally set per-element `sourceImage` — which frame the bbox was
measured in (frame-local coords).

**Multi-frame page composition contract:** two or more `section-comp`
references require top-level `pageComposition`. Set `referenceFrameHeight`,
one `sections[]` row per frame (`section`, `heightStrategy`, `density`,
`minHeightRatio`, `overflowPolicy`, and `clipReason` when clipping), and one
`seams[]` row per adjacent pair (`from`, `to`, `type`, `evidencePath`, plus
`transitionSpacePx`, `bridgeElements`, and `narrative` when applicable).
`bridgeElements` name real manifest `id`/`el` values. A source object crossing
the frame's lower edge is never silently lost: its section row declares
whether the web implementation clips it, lets it bleed, hands it to the next
section, or makes it a cross-section bridge. The optional uniform-height,
all-clipped, and all-hard-cut intent objects require a reason and verbatim user
quote; they are not agent-authored fidelity waivers.

When a verbatim source requests a seamless FV-to-next handoff or stronger
scroll invitation, the affected seam additionally carries
`continuity.required: true`, `sourceRef {path, quote}`, `surfaceOwner`, a
source-backed `geometryPrimitive`, at least three named `layers`,
`previewTargets`, planned desktop/mobile evidence paths, and
`colorSampleReport`. `target-surface` + `incoming-preview` are mandatory; at
least one of `outgoing-environment` or `connective-motif` is also required.
Bind the `seamless-section-waves` output as the hash-bound
`specialistReports.seamContinuity` contract `seam-continuity/v1` (`ready`
before CSS, `pass` at completion). Do not set continuity merely to justify an
invented wave when no source request exists.

**`positioning` (layout law):** every content element defaults to
`positioning: "flow"`. Only elements whose placement ledger + layer-plan entry
justifies true layering may set `positioning: "absolute"`, `"fixed"`, or
`"sticky"` — visual-check audits computed CSS against this field, and an
undeclared absolute/fixed element is a violation. Measured rects are acceptance
targets, never CSS coordinates.

**Frame-local means measured against the frame image.** The section root sits
at 0,0 of its frame, and EVERY descendant's bbox is that element's position
*in the frame image itself*. `box_diff.py --section-relative` subtracts only
the section ROOT's rendered origin — a child written in some inner container's
coordinate space (offsets relative to a card padding box, or CSS values copied
from your implementation) will miss by exactly that container's offset. Field
case: Decision Card children manifested in card-local coordinates failed box
diff by the card shell's offset until re-measured against the frame.

**Measure-first gate (hard rule 9):** FV + `section-critical` bboxes must be
comp-measured (`snap_bbox` / `profile` / `normalized`) BEFORE Phase 5 starts.
Numbers read back from your own DOMRects are tagged
`bboxSource: implementation-derived` and never count as fidelity evidence.
Every FV/section-critical `bbox` carries `measurementRef`: source artifact,
ROI, command/method, and the reason the box was accepted or revised. If you
change a bbox after a render, first write which comp-side measurement justified
the change. "Matched current DOMRect" is a confession that the manifest became
tautological, not a ledger reason. `artifact_check.py` flags missing ledgers
before completion.

**Priorities drive tolerances** (critical ±4px … low ±32px). Hero heading,
container, CTA, first-view image are `critical`. Background decoration,
shadows, grain are `low` — do not spend loop iterations on them, but list them
in the detail inventory (`qaPriority: detail`): the box loop skips them, the
Phase 7 section review does not. A manifest `tolerance` override on an
important element requires `toleranceReason` naming the comp-side reason
(soft/glyph edge, manually measured fallback, intentional density floor).
`box_diff.py` reports `toleranceSource`, defaults, overrides, and overridden
axes for every row; do not accept a report until you have checked whether a
pass was earned by geometry or by widened manifest tolerance.

**Composite-text rule:** a manifest `text.content` is checked by visual-check
as one contiguous DOM text run. Never pack a whole card's copy (label +
heading + date + note) into one element — manifest the child elements
separately, each with its own short contiguous string; give the parent a bbox
but no `text`.

**Span-level contract for display lockups:** each rendered line of an
fv-critical heading is its own manifest element, with the per-line comp bbox
from the Phase 1 decomposition. Inside those lines, every typographic run
that carries a different visual size, script, weight, baseline, tracking, or
accent also gets a manifest entry: Latin acronyms (`AI`), numerals, unit
suffixes, kana/particles, kanji anchor runs, marker-band words, serif
decision words. A lockup contracted only as one block box is a lockup free to
distort; a line contracted without run spans is free to make `AI` optically
too small beside kanji.
Every fv-critical structural text block records
`typeSpec.expectedVisualLineCount` at `manifest.viewport.width`. When
`scriptRuns` exist, record the separate `expectedRunCount`; span count is never
a line count. Measure both from the comp/type ledger, not after implementation.
`visual-check.mjs` compares visual lines at the canonical width.

For Japanese, mixed-script, vertical, or display-critical text, invoke the
`typography` skill during Phase 1 and bind its run-ledger/report evidence paths
into the type spec and measurement references. Japanese critical text also
requires `specialistReports.typography {contract:"typography-report/v1", path,
sha256}`. Pre-CSS accepts a valid pending-review report; completion requires
its independent review and gate status to pass. Report target ids must equal
the manifest ids they audit.

For hybrid multi-frame work, bind the completed `detail-inventory/v1` as
`specialistReports.deviceInventory`; its device ids must exactly equal manifest
`detailInventory` ids. If a critical photo/illustration is generated or
replaced, also bind an adopted `photo-art-direction/v1` as
`specialistReports.photoArtDirection`. At handoff, set
`productionReadiness.mediaDeliveryRequired` and `interactionQaRequired`
explicitly. A true flag makes its passing hash-bound report a completion input;
false keeps fidelity-only prototypes from invoking unrelated production gates.

**Typography integrity fields:** every fv/section-critical display block
records `typeSpec.letterformClass` and `fontBakeoffEvidence`. Record
`lineStartPunctuation` when a line begins with Japanese opening punctuation.
Structural text defaults to no CSS transform. The only exception is
`typeSpec.transformException {allowed, scope, reason, evidencePath}` for a
source-visible decorative-lettering or intentional-display distortion; this
is not a generic bbox escape. `visual-check.mjs` rejects scaled, skewed,
rotated, or visually translated structural text without that evidence and
also rejects substantial undeclared structural-text overlaps.

Every fv/section-critical heading also records `typeSpec.sourceImpression`.
This is the source-derived impression contract, not a CSS wish list: frame
width/height, block width/height ratios, max-line and visible-glyph ratios,
tracking in em, line advance, ink density, viewport maximum-size ratio,
heading-to-lead/body/label jump ratios, desktop/mobile scale bounds, and an
evidence crop. `contract_doctor.py` checks that block ratios agree with the
measured bbox and blocks an identical bbox/type signature copied across three
or more distinct source frames unless each row names `sharedSystemEvidence`.

**Business-requirement additions:** an element the comp does not have but the
handoff requires (decision rail, sticky CTA, legal note) is manifested with
`addition: true` + `additionReason` naming the requirement. Additions are
excluded from fidelity evidence — they appear in the section review's separate
additions table, never as detail-inventory verdicts — and always carry
`mustNotCover` (hard rule 12).

**Background/foreground decomposition (hard rule 23):** when a raster region
contains both a desired background (person, room, product, environment) and
foreground design matter (copy, logos, cards, chips, charts, app UI, glowing
badges, decorative text), split the contract into separate elements before
assets are chosen:

- the raster becomes a `photo` / `illustration` background plate with
  `assetStrategy: "generated"` or `"replace"` unless a clean text-free/UI-free
  source exists;
- each visible foreground item becomes `html-text`, `ui-mock`, `icon`, or
  `decorative-geometry`/`lettering-decal` with its own `data-el`, bbox,
  `zLayer`, and `mustNotCover`;
- copy-space requirements are recorded on the background plate
  (`copySpace: [{"for": "hero.heading", "roi": {x,y,w,h},
  "minClearance": 24}]`); prose in `generatedAsset.matchRationale` does not
  replace geometry. Also record focal `subjectZones` and 390/canonical-width
  `responsiveFocalPoints`;
- the contaminated source crop is allowed only as a visual reference in
  `reports/photo-asset-review.md`, never as a shipped asset.

Judge contamination against the **full intended photographic field**, not the
subrectangle an agent hopes to ship. A crop can contain zero text/UI and still
be invalid because it escaped the overlap by deleting half the room, people,
copy-space geometry, or focal relationships. For every fv/section-critical
photo or illustration, manifest these decisions before asset selection:

- `visualRole`: `background-environment`, `contained-photo`, `object-detail`,
  or `subject-cutout`;
- `photoCompositionMode`: `full-frame-plate`, `contained-photo`,
  `subject-cutout-over-plate`, or `object-detail-tone-merged`. Decide from the
  complete comp, not the visible unmasked portion;
- `clipOwner`: the rounded frame/card/shape that owns the photo or veil clip;
- photo cards record `cardPhotoIntegration` (shared sampled tone, edge
  treatment, and pair path) when the image dissolves into the card ground;
- contained/object-detail rasters record `assetSurfaceContract` before
  generation. Name every consumer and decide whether CSS or the bitmap owns
  the frame, background, padding, radius, shadow, and bleed. When CSS owns the
  card surface, set `assetMustNotContainPanel` and
  `assetMustNotContainPadding` true and prompt for an edge-to-edge photo or
  transparent cutout—not a finished card mockup. Review both the isolated
  asset and its final crop-in-use. A multi-zone bitmap does not waive this
  per-consumer contract;
- every critical raster with an `assetUnit` also records
  `surfaceIntegration`. First freeze `sourceTopology` from source evidence:
  `section_field`, `floating_scene`, `contained_artwork`,
  `tone_merged_object`, or `source_visible_frame`; this cannot be relabeled
  merely because an image generator returned an opaque rectangle. Record a
  readable source crop and `edgePolicy` for top/right/bottom/left. Then choose
  exactly one mode independently of the generation unit: `alpha_floating`, `opaque_full_bleed`,
  `opaque_masked_merge`, `opaque_tone_matched`, or `intentional_frame`.
  Declare whether CSS, the asset, or both own the surface; who owns outer
  whitespace; the mask owner or consumer background color when applicable;
  and a final `cropInUsePath`. `asset_preflight.py` decodes 8-bit RGB/RGBA PNG
  pixels with no optional imaging dependency and reports alpha fraction, edge
  RGB/deviation, uniform outer-band depth, and estimated content bounds. An
  opaque uniform border plus CSS-owned background/padding is blocked as
  double-padding risk; tone matching is checked by RGB distance;
- the preflight receipt binds both the manifest and every adopted raster byte.
  `inputs.assets[]` contains `elementId`, original workspace path, size, and
  SHA-256. Replacing or post-processing an image after preflight invalidates
  the gate even when manifest JSON did not change;
- every generated/replaced raster records `assetUnit`. Choose
  `full_field_scene_plate`, `clean_background_plate`, `transparent_foreground`,
  `transparent_scene`, `card_artwork_plate`, `atomic_raster`, or `code_native`;
  list its semantic `members`; and record
  `splitPolicy`. `separate` requires at least one true independent behavior
  (motion, responsive recomposition, reuse, interaction, content update, or
  layering) plus concrete `splitEvidence`. `keep-together` records why the
  parts form one static composition. A card artwork plate may own its complete
  interior scene while CSS owns the outer card shell and structural copy;
- `full_field_scene_plate` owns a whole section visual field, includes coupled
  hero/environment objects, and requires measured `copySpace` plus responsive
  focal points unless no structural copy exists and a reason is recorded.
  `transparent_scene` keeps coupled floating objects and soft shadows in one
  alpha asset while excluding every outer white/paper rectangle;
- complex curves/fields/diagrams record `decorativeCraft` (field type,
  medium, complexity target, evidence path) so category stand-ins are visible;
- `sourceFrameHasForegroundOverlap`: boolean, assessed on the whole intended
  photo field in the comp;
- `sourceFrameOverlapKinds`: required when true; list the actual text/nav/CTA/
  watermark/UI devices;
- `cleanLayeredSource`: true only for a separate clean source layer, never for
  a clean-looking subcrop of the flattened comp;
- for `crop-asset`, `cropPreservesComposition: true` plus `croppedAsset`
  evidence (`workspacePath`, `sourceRoi`, clean contamination check, review
  path, and a pair proving composition retention).

A manifest that treats a fused raster as one acceptable `photo` while its
baked-in UI/text remains visible has skipped decomposition; Phase 7 marks the
affected foreground devices `missing`.

### Asset/topology revision re-entry

The chronology guard answers one question: did implementation begin before the
first hash-bound pre-CSS pass? Once that pass exists, later user feedback may
return to asset planning without deleting, renaming, or touching existing
HTML/CSS. Rerun contract doctor and asset preflight against the new manifest
and asset bytes; their current receipts determine freshness.

When feedback changes `sourceTopology` or its surface owner, record a revision
ledger with affected element ids, previous/new topology, verbatim reason,
source evidence, and invalidated artifacts (`prompt receipt`, `asset preflight`,
`cropInUsePath`, bbox/box report, section review, FV pixel evidence). Regenerate
the affected asset. Remeasure its expected bbox from the comp crop or newly
approved reference and set measurement provenance accordingly. Never copy the
current DOMRect into the manifest to clear the old box failure.

**The background plate keeps `mediaClass: "photo"`/`"illustration"` (hard rule
24).** Decomposition splits OFF the foreground UI/text — it never dissolves the
photographic subject itself into `svg`/`ui-mock`/`css`. If the comp shows a
person, product, room, or environment, that plate is a photo element with a
`generated`/`replace`/`crop-asset` strategy (or an honest `placeholder` after a
recorded, failed generation attempt). Reclassifying the subject to a
vector/UI/CSS element, or dropping it and free-styling comp-absent UI in its
place, is the **reclassification escape**: the asset policy, the contamination
gate, and completion gate G8 all bind to `mediaClass: photo`, so a photo-led comp
with zero photo elements has silently switched them off. Field case: a
photo-led hero (executive portrait) and a testimonial (participant portrait) were
each re-declared as `svg`/`css` and shipped as an invented decision dashboard and
an empty panel — box diff still passed 31/31, but the human the comp was built
around was gone. Gate G8 flags an fv/section-critical photo element that ships no
raster, and a section-review disposition that calls a photo/portrait device
`adapted`/`present` while no raster was shipped.

**Box-diff measurability rule:** the box loop measures real DOM boxes.
Pseudo-elements (`::before`/`::after` underlines, rules, ticks) do not
contribute — if a device's extent must be verified by box diff, make it a real
element or give the host an explicit size; otherwise leave it
`qaPriority: detail` and let the section review judge it.

## Font policy

Pick real fonts NOW, **per text role from the Phase 1 type spec**, judged
against a zoomed crop of the comp's actual glyphs — weight, width, stroke
contrast, terminal shape, counter openness — not from a font's name. Loadable
candidates (Google Fonts etc.): JP gothic — Noto Sans JP (has 900), Zen Kaku
Gothic New, M PLUS 1p/2; JP mincho — Shippori Mincho (B1 for display), Zen Old
Mincho, Noto Serif JP; latin — Inter, Poppins, Montserrat, Playfair Display.

- Defaulting every role to one family at 700 is font-selection laziness.
  Display roles in AI comps usually need 800–900, and a serif/mincho accent
  role (dates, prices, decision words) is common — honor it.
- Display type never ships on a system-ui fallback: load the webfont and
  confirm it actually rendered (a fallback font shifts every glyph box — treat
  a suspiciously-off text bbox as a font-load failure before retuning
  font-size). If external font loading stalls rendering, self-host or subset —
  do not silently drop to system fonts.
- Record `fontFamily` per role in the manifest plus a one-line rationale in
  hypotheses.md.

Structural copy is never shipped as generated glyphs — but its typographic
*treatment* is faithfully rebuilt in CSS (hard rule 5). Font-size is found by
the render loop (render → compare bbox → adjust), never by reading pixel heights
(cap-height ≠ font-size). For mixed-script display runs, the manifest's
`typeSpec` records the comp's optical ratios and baseline offsets;
implementation may use different CSS sizes for Latin, kana, kanji, and numerals
to make the rendered glyphs look the same height as the comp. Non-structural
handwritten notes and decorative callouts may be manifested separately as
`mediaClass: "lettering-decal"`; they do not replace this font policy for real
content.

## Asset policy — media class first (hard rule 13)

Set `mediaClass` per visual in the manifest, then use the matching path:

- `decorative-geometry` (lines, bands, blobs, gradient fields, abstract
  shapes) → CSS/SVG. The ONLY class where free-hand vector drawing is right.
  Craft matters: a comp's flowing curve is an SVG bezier path with the comp's
  sweep and weight, not a straight border line (see `composition.md`,
  decoration craft).
- `ui-mock` (flat app panels, charts, status chips the comp presents as flat
  UI) → HTML/CSS rebuild with the comp's specific content (hard rule 11).
  Never a license to flatten photographic content into flat UI.
- `icon` → an established open icon set FIRST (Lucide, Tabler, Phosphor,
  Heroicons, Material Symbols): pick the glyph whose subject matches, inline
  the SVG, match stroke weight / corner style / size, record `iconSource`
  (e.g. `"lucide:trending-up"`). Hand-drawing a bespoke path is a last resort
  — and then it reproduces the comp's specific subject.
- `lettering-decal` → expressive non-structural lettering (handwritten speech
  bubble, signature, margin note, decorative callout). It may be a generated
  transparent PNG, a hand-traced SVG, or a carefully matched hand-font DOM
  element. Requirements: not SEO/accessibility/interaction/legal content; exact
  target text recorded in `text.content`; transparent/clean asset path recorded
  when raster; `letteringProof {exactText, method, pairPath}` whose `exactText`
  equals `text.content`; 200% crop-pair proof that the Japanese/Latin glyphs are correct;
  `mustNotCover` for nearby faces, headings, and CTAs. A heading, CTA, nav item,
  body copy, label, price/date, or legal note misclassified as `lettering-decal`
  is a hard rule 5 failure.
- `photo` / `illustration` → the decision tree below. **Never SVG/CSS**, and
  never an HTML/CSS/Canvas/Pillow/SVG scene rendered to PNG. Programmatic
  drawing is still drawing, even if the file extension is `.png`; it may only
  satisfy `decorative-geometry` / `ui-mock`, not photo-class content.

### Decision tree per lettering decal visual

1. If the comp provides a clean transparent/source lettering asset, use it
   (`crop-asset` or `replace`) after exact content proof.
2. If the lettering is small, expressive, and non-structural, generate a
   transparent raster asset. Prompt for the exact text, tone (handwritten,
   casual, brush, neat pencil), ink color, transparent background, and no extra
   marks. Save to `"$WORK_ROOT"/assets/`, set `assetStrategy: "generated"` +
   `generatedAsset` + `letteringProof`, and record the candidate in `reports/photo-asset-review.md`
   (the file also covers lettering assets).
3. If generation changes a glyph, adds stray text, changes the phrase, or loses
   the comp's hand, reject and regenerate or switch to hand-traced SVG /
   hand-font DOM. A lettering candidate with wrong Japanese is `missing`, not
   `adapted`.
4. If the text is structural after all, reclassify it to HTML/CSS text and tune
   typography; do not force it into an image.

### Decision tree per photo/illustration visual

1. Layered / text-free source asset exists → use it.
2. **A text-free asset you already own matches → `replace`** — judged exactly
   like a generated candidate: same subject type, mood & lighting, compatible
   color grade, right aspect/focal for the crop. Record
   `replacedAsset {sourcePath, matchRationale, usedBy}` and re-judge in the
   section review. When close-but-off in tone, harmonize with a CSS `filter`
   grade and note it in `replacedAsset.grading`.
3. Clean, **composition-preserving** photo region → `crop_asset.py`; check the
   contamination report. This path is for a contained photo/object region or a
   real clean source layer. It is not an escape hatch for fused full-field
   environments. "Clean" means no readable or pseudo-readable text, logo,
   signage, chart, app UI, card/chip decoration, or foreground design matter in
   the crop, including blurred or tiny marks that become visible at 200% zoom.
   Also prove that subject count, environment, focal relationships, intended
   aspect, and copy-space geometry remain intact. Record
   `sourceFrameHasForegroundOverlap: false` (or `cleanLayeredSource: true`),
   `cropPreservesComposition: true`, and the complete `croppedAsset` block.
4. **Contaminated crop (text/design/UI baked into the photo — the NORM in AI
   comps): do NOT ship it.** The default is to generate or replace a clean
   background plate, then rebuild foreground type/UI as DOM layers. Escalate
   in order, record the outcome:
   1. **Regenerate** text-free with the available raster image generator — the
      default, and an action, not a note (hard rule 25). Actually invoke a raster
      image model (e.g. `cockpit gen-image`, a Codex/Firefly image tool, or the
      user's stock/image account) and write an output file; "I could not verify a
      generated asset" is not grounds to skip the attempt — generate first, then
      verify. Only a recorded, failed attempt (tool named, error captured) earns
      the descent to 4.2/4.3. Before adoption, verify the generated image exists
      as a readable file on disk, then copy that file into `"$WORK_ROOT"/assets/`.
      A chat-visible preview, image tool response, or URL without a local copied
      file is not an asset. Adoption checklist per candidate, before it enters
      `"$WORK_ROOT"/assets/`:
      - [ ] zero text/logos/signage/readable UI anywhere (≥200% zoom sweep)
      - [ ] zero baked-in cards/chips/charts/app panels/CTA-like UI; any such
            device needed by the comp is rebuilt as HTML/CSS
      - [ ] subject type & identity match (age, build, wardrobe; faces are
            the highest bar — "different person" fails)
      - [ ] mood & lighting match (warm/cool, high/low-key, candid/formal)
      - [ ] color grade compatible with the section palette
      - [ ] aspect & focal placement fit the manifest bbox and crop
      - [ ] the layer plan's empty zones are actually empty (copy space where
            HTML type/UI sits; face/key product detail clear of headings,
            cards, chips, and CTA per `mustNotCover`)
      - [ ] in-photo props that carry design are absent or planned as HTML
            overlays
      Set `assetStrategy: "generated"` + `generatedAsset {prompt, sourceImage,
      workspacePath, generator, usedBy, contaminationCheck, reviewPath,
      pairPath}`; save the prompt to `reports/imagegen-prompt.md`; record
      per-candidate verdicts (adopted AND rejected) in
      `reports/photo-asset-review.md`. `workspacePath` must exist on disk
      before Phase 5 uses it, and `contaminationCheck` or the review row must
      prove the bitmap is text/UI-free. The generator must be a raster image
      model — rendering your own HTML/CSS/SVG/Canvas/Pillow scene to PNG is
      not generation (hard rule 13). If you produced the bitmap with a drawing
      API or browser screenshot under your control, reject it as a fake asset
      and choose stock/owned asset/placeholder instead.
   2. **Licensed stock photo** (Unsplash / Pexels / user's account) after a
      recorded failed generation attempt. Same adoption checklist; adopt as
      `replace` with `replacedAsset {sourcePath, workspacePath,
      replacementKind: "licensed-stock", matchRationale, license,
      contaminationCheck, reviewPath, pairPath}` and keep the failed
      `generationAttempts` row on the element. A clean asset already provided
      by the user or already owned is `replacementKind: "provided"` / `"owned"`
      and is not a degraded fallback.
   3. **Placeholder + ask.** A solid/gradient block or clearly-labeled
      stand-in sized by the manifest bbox — never a blurred/overlay-masked
      copy of the contaminated crop, never a vector/programmatic redraw of the
      photo subject. Set `assetStrategy: "placeholder"`, record
      `generationAttempts [{generator, prompt, status: "failed", error}]`, ask
      the user for the real asset, and list every placeholder in the completion
      report. A
      hand-drawn/Pillow/SVG pseudo-photo is worse than a placeholder because it
      hides the missing asset.

   No further option exists: no "low-risk" background text, no hiding under
   gradients, no blurring, no tiny pseudo-text, no deferred inpaint, no vector
   redraw of a photo subject, and no "we will cover it with HTML later".
   Re-run the contamination check on every crop that ends up in `assets/`.
5. All structural copy — headings, body, years, CTA labels, nav, legal notes,
   vertical identity labels, band phrases, outline display type — is
   `html-text`, never part of an image. Only declared non-structural
   `lettering-decal` rows may be generated/cropped as image text.

```bash
python3 "$SKILL_DIR/scripts/crop_asset.py" "$WORK_ROOT/mockup.png" \
  --roi 720,120,520,640 --out "$WORK_ROOT/assets/hero-photo.png"
```

## Phase 3.25 — Run the contract doctor before CSS

After measurements, ownership, page composition, and photo decisions are in
the manifest—but before section CSS—run:

```bash
python3 "$SKILL_DIR/scripts/contract_doctor.py" "$WORK_ROOT" \
  --phase pre-css --out "$WORK_ROOT/reports/contract-doctor.json"
```

It is stdlib-only and must return `implementationAllowed: true` (`status: pass`
normally; `needs_work` only for an asset-policy-earned placeholder). It catches the field errors
that should not consume a browser loop: bbox arrays instead of `{x,y,w,h}`;
FV/section-critical rows without comp-side measurement provenance; conflated
visual-line/run counts; incomplete machine-readable detail inventory; fixed or
sticky chrome without viewport ownership; fv-critical text without an
expected canonical line count; unordered/malformed multi-frame section and
seam contracts; and generated photos that only name a path without prompt,
generator, source, contamination review, crop pair, and readable files. It
reuses the real asset policy below, so this is not a weaker schema-only lint.

Hybrid multi-frame manifests set `reviewPolicy` and `detailInventory` before
CSS. Inventory rows cover every section and either bind to manifest element ids
or declare `evidenceMode: crop-only`; free-form prose cannot be reconciled at
completion.

When two or more `kind: photo`, source-specific inventory rows bind to one
manifest photo element, `contract_doctor.py` treats that as semantic collapse
unless the element declares `multiZoneAsset.zones`. Every zone maps one
`inventoryId` to a non-identical `cropRoi`, names the focal
`subjectSignature` and consumer, and cites the final crop-in-use `pairPath`.
Prefer distinct generated assets when the source depicts distinct stories.

For critical generated assets, `reviewPolicy.exactPromptProvenanceRequired`
binds `generatedAsset.prompt` to an exact UTF-8 prompt file through
`promptRef {path,sha256,kind:"exact-prompt"}`. `inputRefs` separately records
every consulted/sent image with path, hash, role, and
`includedInGeneration`; `sourceImage` must appear there. A summary prompt or a
reference merely named after generation is blocked before CSS.

The doctor report does not replace `asset-preflight.json`; keep the explicit
Phase 3.5 artifact for later evidence gates.

## Phase 3.5 — Run the asset preflight before CSS

After all critical photo/illustration rows are declared, run:

```bash
python3 "$SKILL_DIR/scripts/asset_preflight.py" "$WORK_ROOT/manifest.json" \
  --work-root "$WORK_ROOT" --out "$WORK_ROOT/reports/asset-preflight.json"
```

- `pass`: real clean raster decisions and their files/evidence are ready.
- `needs_work`: only an earned placeholder remains. CSS may proceed with that
  explicit stand-in, but completion is unavailable.
- `blocked`: stop before CSS. Typical causes are an undecided source overlap,
  a fused source paired with `crop-asset`, a crop that does not preserve the
  environment, a missing generated file, or stock/placeholder fallback without
  a recorded failed generation attempt.

Do not hand-edit the report. `artifact_check.py` and completion gate G9 run the
same policy again, so deleting `asset-preflight.json` or narrating a crop as
"clean enough" cannot bypass the contract.
