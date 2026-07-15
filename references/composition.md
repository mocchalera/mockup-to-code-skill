# Phases 4 / 4.5 / 5.5 — Layers, page composition, and the FV look-and-tune

Read this before any CSS exists. This file owns the three passes that decide
whether the build reads as a designed page or as stacked slabs.

## Phase 4 — Layer plan (hybrid: mandatory before any CSS)

For the FV and every region with overlap, decide **what sits on what and
why** — in the manifest, not in your head. Per element: `layerRole`
(background-photo / photo-overlay-gradient / primary-html-type /
decorative-outline-type / accent-band / vertical-label / foreground-card /
dark-bottom-panel / cta …), `zLayer`, `positioning` (flow unless truly
layered — layout law), `overlapIntent` (what the overlap must look like),
`blendMode` if any, `mustNotCover` (ids this element must never obscure),
`backgroundBehavior` for images (**full-bleed** = seamless background layer;
`framed` only when the comp genuinely shows a card).

The single most quality-deciding call in a poster FV is usually here: the hero
photo is a **full-bleed background layer** (`.fv-bg` scaffolding in
`templates/poster-typography.css`), not an `<img>` card in the flow.
`visual-check.mjs` enforces the declared intent later, so declare it honestly.

Oversized decorative type also declares `mustStayBehind` and integer `zLayer`
values for the decoration and every structural target. Do not rely on DOM
order or low opacity to make an unregistered watermark "feel behind".

**Anchor grammar (required for FV and global UI):** translate the Phase 1
ownership ledger into implementation objects before writing selectors.

- Container content: title, subcopy, CTA, form/card groups. Use grid/flex flow
  inside the responsive container. Tune gaps and type scale to hit measured
  rects.
- Hero-bound layers: clean photo plate, overlay gradients, hero-bottom
  watermark type, section dots/waves. Position relative to the hero section;
  record `placementScope: "hero-bound"` and `anchorTarget: "hero"`.
- Photo-bound decals: handwritten bubbles, generated lettering, plant sprigs,
  badges near a face/product. Position relative to the photo layer or a
  photo-focal wrapper; record the face/product/empty-zone `mustNotCover`
  targets. Preserve visual relationships (distance from face/shoulder, empty
  copy space), not raw left/top.
- Viewport/global UI: fixed header nav, persistent vertical logo/title,
  viewport-edge labels. These are not hero content even if visible in the FV.
  Use `positioning: "fixed"` or `"sticky"` only when the comp/product intent
  suggests persistence; set `placementScope: "viewport-fixed"` or
  `"viewport-edge"`, a viewport `anchorTarget`, and the mobile release
  behavior. They may still carry the FV `sourceImage` that was measured, but
  `box_diff.py --section-relative` evaluates them as `viewport-global`; it
  must not subtract a section root from chrome that lives outside that
  section in the DOM.
- Seam-bound decoration: waves/dividers belong to the section boundary or next
  section, not to the hero content column.

Absolute/fixed positioning is acceptable for declared layers; it is a defect
when used to place normal copy simply because the comp bbox is known. For every
layered element, fill `anchorTarget`, `relationshipToPreserve`, and
`responsiveBehavior` in the manifest.

**Asset-source gate before CSS:** before styling a photo/illustration
background, point the layer plan at a verified asset source: clean layered
source, owned/stock replacement, or a real raster image-generator output
already copied into `"$WORK_ROOT"/assets/`. If the generator only returned a
preview and no local file path has been verified, the asset is not available
yet. Do not draw a substitute background with SVG/CSS/Canvas/Pillow/HTML and
rasterize it; that silently changes a missing photo into an invalid fake
asset. Use a plain `placeholder` entry and report the blocker instead.

This is executable, not a checklist you self-approve:

```bash
python3 "$SKILL_DIR/scripts/asset_preflight.py" "$WORK_ROOT/manifest.json" \
  --work-root "$WORK_ROOT" --out "$WORK_ROOT/reports/asset-preflight.json"
```

Do not create section CSS while `implementationAllowed` is false. The gate
looks at the source comp's full intended photographic field, so a text-free
crop that merely cuts away overlapped copy/UI and most of the environment is
blocked. An earned placeholder may return `needs_work` with implementation
allowed, but it can never clear completion.

**Clean background plate rule (hard rule 23):** if the comp's hero/photo
raster has text, logos, UI cards, charts, chips, or decorative foreground
matter fused into the image, the layer plan starts by separating the desired
background from those foreground devices. Generate or replace the raster as a
clean background plate with the same subject, mood, lighting, crop, and empty
copy zones. Then rebuild every foreground device above it as HTML/CSS/SVG
according to its media class. Do not use the contaminated crop as a
background and rely on gradients, blur, opacity, or overlapping DOM to hide
the baked-in design; if it remains visible in a crop pair, the background
asset fails and the affected foreground devices are `missing`.

For each such raster, record:

- `backgroundBehavior` and `edgeTreatment` for the clean plate;
- `copySpace` / `mustNotCover` zones for headings, CTA, cards, and faces;
- which foreground items were extracted into DOM layers, with their
  `data-el` ids;
- the adopted asset path plus rejected candidate paths in
  `reports/photo-asset-review.md`.

**Photo integration rule (new in v7 — field data: a hero photo terminated in
a hard rectangle over flat white and the FV read as a brochure, not a
poster):** a photo that is the section's *environment* never terminates in a
hard rectangle edge inside the section. Every photo edge must be one of:
(a) bled to the section/viewport edge, (b) dissolved by a gradient/mask
hand-off into the adjacent field (CSS `mask-image` / an overlay gradient
matched to the background), or (c) a comp-visible framed card — only if the
comp genuinely frames it. Declare the treatment per edge in the layer plan
(`edgeTreatment: {top, right, bottom, left}` note). If the source crop is too
small to bleed, regenerate at a larger aspect or extend with
generative-expand — do not shrink the environment into a box.

### Photo topology and clip ownership (required before CSS)

Do not infer the photo's construction from the part left visible after the
comp's white shape or gradient. Classify the full topology:

- `full-frame-plate`: the environment spans the section and a foreground veil
  hides part of it. Generate the full plate with matching focal placement;
  clip/mask the veil, not the person into a half-width rectangle.
- `contained-photo`: a real framed photograph/card with comp-visible hard
  edges. Preserve its frame and stagger.
- `subject-cutout-over-plate`: subject position must move independently from
  the environment. Generate/source a clean environment and separate cutout.
- `object-detail-tone-merged`: a card object photo shares the card's ground.
  Generate on the measured card tone (or use a clean cutout), place it as an
  `<img>`, and dissolve only the comp-visible edge.

For every veil, mask, photo, or gradient name its `clipOwner`. If the comp
shows a rounded inset frame, apply radius/overflow/mask to that frame and keep
the veil inside it; a page-wide overlay outside the frame is different layer
topology even when contrast is similar. Save a crop pair that includes frame
corners, mask hand-off, and subject.

**Decoration craft rule (new in v7):** decorative devices are rebuilt at the
comp's rendering quality, not as category stand-ins:

- a flowing curve = an SVG path with the comp's sweep, weight and color
  (drawn across the section, `vector-effect: non-scaling-stroke` where
  appropriate) — never a straight 1px border or a rotated div line;
- a glass panel = translucent fill + `backdrop-filter: blur()` + subtle edge
  highlight/shadow — never a flat white card;
- shadows match the comp's softness/offset language; radii match its corner
  language.

A crude stand-in is judged `missing` in the section review even though
"something is there".

### No symbol-sketch implementation

Emoji, dingbats, enclosed alphanumerics, arrows, and miscellaneous Unicode
symbols are text glyphs, not an icon system. They may reproduce a source only
when the source itself visibly uses that exact text glyph and
`renderingCraft.allowTextGlyphStandIn: true` records the exception. Otherwise
source-specific line art, illustrations, badges, UI portraits, gift objects,
and check devices must be rebuilt in the declared medium while preserving the
declared `minimumAtomicParts`. Those parts may live inside one clean
`card_artwork_plate` when the composition is static; use separate assets only
for independently behaving parts. `visual-check.mjs` audits symbol-only leaf nodes
inside the manifested device, so surrounding the emoji with a styled card does
not make it faithful.

### Icon medium decision

Do not turn every source icon into SVG merely because SVG is available. Use
SVG for simple marks, arrows, checks, document outlines, and schematic UI
controls whose quality depends on clean deterministic geometry. Classify an
icon as `illustration` when it includes a human pose or face, emotion,
organic hand-drawn character, three or more coordinated pictorial parts, or
small accent objects whose relationship carries the design. Those devices use
image generation or an owned illustration asset, not improvised path drawing.

For three or more sibling illustrations, generate one style-bound sprite sheet
on a removable chroma background. Ask for a strict equal-cell grid in the
generation prompt, but treat that as art direction rather than geometric proof:
generators can drift away from the requested cell widths. Require one
pre-generation prompt receipt, visibly separated subjects, no labels/card
shells, transparent edge review, and one extracted PNG per semantic consumer.
Preserve the uncut sprite and the transparent master as provenance.

Do not calculate cuts as `image_width / icon_count` by default. Run
`split_sprite.py` on the transparent master with the expected count and semantic
names. The report must contain exactly that many measured alpha clusters and
each extracted asset must have zero alpha pixels on all four cut edges. An
equal-width split is allowed only when pixel inspection first proves the
generated cells coincide with those boundaries; otherwise a clipped subject or
neighbor contamination is a blocked asset, even if the final card hides it at
one viewport. `assetSurfaceContract` keeps card fill, radius, shadow, and
padding in CSS so generated cells cannot create a double frame.

`assetUnit` answers “what belongs in one generated composition.” It does not
answer “how that composition meets the web surface.” Every critical raster
therefore freezes source topology before generation and also declares
`surfaceIntegration`: transparent floating art;
opaque full bleed; opaque masked merge; opaque edge tone-matched to the CSS
surface; or a source-proven intentional frame. The preflight reads real PNG
pixels. If CSS owns card background/padding while an opaque raster contributes
a uniform outer band, stop before CSS and regenerate, mask, or tone-match it.
An isolated asset preview is insufficient; keep the rendered crop-in-use.

### Section field vs floating scene

Do not begin with an `<img>` box. Begin with the source comp relationship.

- `section_field`: the scene creates the whole section world. Generate one
  `full_field_scene_plate`, reserve measured copy space, set responsive focal
  points, let the asset own the section field, and bleed/mask declared edges.
  A right-side framed image is not an acceptable fallback.
- `floating_scene`: a paper object, exploded diagram, device group, collage,
  or object family sits directly on the Web field. Generate one
  `transparent_scene` per coupled consumer, including its local soft/contact
  shadows in alpha and excluding the generator's outer white/paper rectangle.
- `contained_artwork`: only a source-visible card/photo/screen content box may
  contain a hard-edged raster. Fill that content box; let CSS own the shell.

If alpha generation fails, return to asset generation and choose a full-field
scene, a source-evidenced mask, or measured tone merge. Do not change the
source topology to `contained_artwork` merely to make the current bitmap usable.

### Semantic raster unit decision

Do not equate every visible object with an asset. First ask whether a part has
independent motion, responsive recomposition, reuse, interaction, content
updates, or layer-order control. If none apply and the source presents one
static editorial composition, regenerate the whole interior as one
`card_artwork_plate`. Typical examples are a person plus its local background
and light, a laptop plus phone plus their static screens and shadows, a torus
plus plinth and contact shadow, or a complete abstract artwork. The card shell,
structural copy, labels, CTA, and page layout remain HTML/CSS.

For large blue/green wave fields, dotted orbits, or multi-path diagrams, write
`decorativeCraft` before choosing the medium: path/node count, curvature,
gradient stops, color overlap, softness, and clipping. Use SVG/CSS gradients
when topology is controllable; use a clean generated decorative raster when
the field's organic texture cannot be reproduced economically. Flat polygons,
straight bands, or one line do not satisfy a bezier-gradient field.

For section-scale arcs, choose and record one primitive. A `bezier` records
the measured endpoints, tangents, bulge, and sweep. A `circle-arc` uses a true
circle (`width == height`) with its diameter and usually off-canvas center
recorded in `circleArcGeometry`. `ellipse` is allowed only when the comp visibly
uses elliptical curvature and `ellipseException` binds the source crop and
reason. `width:80%; height:320px; border-radius:50%` is a convenience ellipse,
not a designed circle arc.

For staggered card stacks, record each card shell's flow offset, z-order,
width, and photo integration. Margin/translation may move the non-text shell;
do not align every shell and shift only the internal images—the composition is
the staggered card stack, not identical rows containing different crops.

**Additions** (elements the comp does not have) are layered here too, per
hard rule 12: each gets a layer-plan entry with `mustNotCover` naming every
comp element near it. If the addition doesn't fit without covering a comp
device, recompose the region or ask the user which wins — never ship the
occlusion with a self-granted waiver.

See `fv-poster-example.md` for a complete worked example.

## Phase 4.5 — Page composition plan (multi-frame: mandatory)

The frames tell you what each section says; **nobody has yet designed the
page**. Before implementing, write a page-flow block in hypotheses.md that
composes the frames into ONE scrolling LP, then copy the decision into the
manifest's executable `pageComposition` contract:

- **One section strategy per `section-comp`**: `heightStrategy`
  (`content-led`, `breathing`, `immersive`, or `viewport-chapter`), `density`
  (`dense`, `balanced`, or `airy`), `minHeightRatio`, and `overflowPolicy`
  (`visible`, `clip`, `bleed-to-next`, `next-section-owned`, or
  `cross-section-bridge`). `clip` additionally requires `clipReason`.
- **Bottom-edge ownership is a design decision**: every source device that
  touches or extends past the bottom of a frame is explicitly clipped,
  allowed to bleed, assigned to the next section, or made a cross-section
  bridge. Do not add `overflow:hidden` to every section as a reflex. A frame
  crop is evidence of the generator canvas edge, not proof that the web page
  must cut the object there.
- **One seam contract per adjacent pair**: `from`, `to`, `type`, optional
  `transitionSpacePx`, any manifest `bridgeElements`, the scroll-narrative
  hand-off, and a readable `evidencePath`. The transition area may be the
  previous section's bottom padding, the next section's top padding, an
  overlap, or a shared field; it does not need a decorative wrapper element.

### Explicit seamless-scroll request: art-directed bridge

When the source says the FV and next section should feel more integrated,
seamless, or inviting to scroll, ordinary seam coverage is not enough. Invoke
`seamless-section-waves`, preserve the verbatim source in
`seam.continuity.sourceRef`, and set `continuity.required: true`. Before CSS,
compose both sections in one boundary system:

1. `outgoing-environment`: preserve the last meaningful hero/photo context;
2. `target-surface`: an opaque field owned by the destination section and
   painted with its exact surface token;
3. `connective-motif`: one existing type/line/dot/numbering motif crosses or
   visually continues through the boundary;
4. `incoming-preview`: at least one next-section eyebrow, title, portrait, or
   narrative anchor is visible in the same seam crop.

`target-surface` and `incoming-preview` are mandatory; require at least one of
`outgoing-environment` or `connective-motif`, so the bridge has at least three
layers. A haze is not the opaque field: keep photo fade and destination-color
ownership separate. A generic centered wave, one decorative line, or a crop
showing only a few pixels above/below the boundary is still a divider.

Choose `bezier`, `circle-arc`, or `freeform-path` from measured/source-backed
geometry. Prefer an asymmetric crest/shoulder composition; never default to a
stretched ellipse. Name `previewTargets`, optional `cueTarget`, planned desktop
and mobile crop paths, and `colorSampleReport`. Bind the specialist's
`seam-continuity/v1` receipt as `specialistReports.seamContinuity`.

The destination field owns exact color continuity; the previous section may
own the outgoing photo/haze; a shared seam layer may own the connector. Record
those ownership boundaries and z-order. Bridge decoration declares
`mustStayBehind`; cues declare `mustNotCover`; structural incoming content
stays in normal next-section flow.

- **Seam plan — one line per adjacent pair** (01→02, 02→03, …): how does the
  eye cross the boundary? Background continuity (shared white, a color band
  ending, a photo edge), contrast cut vs smooth hand-off, spacing at the seam
  (a seam is allowed to breathe — stacked 16:9 full-bleeds with zero rhythm
  read as a slideshow), and any device that *bridges* it (a motif line
  crossing the boundary, a heading pulled up over the previous section's
  edge, an overlapping card).
- **Connective motifs**: recurring devices from the essence ledgers (accent
  lines, label style, numbering, palette accents) and where each recurs so
  the page reads as one hand. A motif appearing once per frame because each
  frame was generated separately often *wants* to be a single continuous
  system on the page — e.g. one SVG curve flowing through several sections.
- **Whitespace & density rhythm**: which sections are dense, which are air;
  where the reader gets a pause before the next push (especially before/after
  CTA sections). Section heights follow content + rhythm with the frame
  height as the density floor — a below-FV section may (often should) run
  taller than its 16:9 frame.
- **Scroll narrative**: one sentence per boundary on what the reader should
  feel/expect next.

Phase 7 binds the plan to rendered section rects with `page_flow_check.py` and
reviews the seam crops. Repeating the normalized frame height for every
section, clipping every section, or giving every boundary an unevidenced hard
cut is not fidelity; it is a stacked-slide implementation. The only exception
is a verbatim, recorded user request for that exact uniform treatment.
Skipping this phase and reproducing frames independently is how a build ends
up "every section 8/10, the page 5/10".

## Phase 4.75 — Motion plan (only when the source requests motion)

Set `motion.required: true` only from a user/handoff requirement and preserve
the verbatim quote in `motion.sourceRef`. Choose at most two reusable motifs:
normally one reading-order entrance and one low-amplitude ambient/interaction
motif. Bind targets to manifest ids, animate only opacity/transform or SVG
stroke dash, and keep the static fidelity target as `visualQaState: settled`.

For a cross-section bridge, the comprehension order is normally hero promise
or CTA → static seam field → directional cue → incoming preview. Do not animate
all four. One low-amplitude `translateY(4px–8px)` cue at 1400–2200ms may repeat
when its meaning is “continue below”; this is the narrow exception to avoiding
infinite decorative loops. It remains subordinate to the CTA, points to a real
fragment when clickable, and becomes a visible, motionless settled cue under
reduced motion.

The reduced state is `settled-static`: critical copy and controls are visible
without waiting, scrolling, or JavaScript. Do not replace missing particles,
photo props, lines, or hierarchy with motion. Generic hover lift on a
non-interactive card is not a motif and creates false affordance.

## Phase 5 — Implementation order & rules (summary; layout law in SKILL.md)

Order: header → hero → down the page — and "lock it first" is a gate, not a
mood (hard rule 19). The FV milestone: Phase 5.5 look-and-tune passed, the
FV-scoped box loop converged (every fv-critical element passing, or its
stopping-criteria residual recorded), and the FV impression metrics (qa.md)
recorded in tolerance. **No below-FV CSS before this milestone is evidenced**
(`reports/fv-tune/` + an FV box report). Field data: a run that logged its
hero deltas and moved on shipped with all eight fv-critical boxes failing —
the first view decides perceived quality, and below-FV work cannot buy it
back. Start from `templates/base.css`; for poster/hero
typography include `templates/poster-typography.css` and bind its custom
properties to manifest tokens. Put measured/normalized values into CSS custom
properties. Every manifest element carries its `data-el`. Dimensions that
carry the design — type scale, container, section paddings, photo boxes, CTA —
trace to the manifest or a token; small decorative px literals are fine.

For every critical section heading, the first section render must match
`typeSpec.sourceImpression`: viewport/block/line/glyph scale, tracking, line
advance, ink density, and jump ratios. A shared generic weight/leading rule is
not fidelity. For a multi-line poster heading, also match
`typeSpec.posterGeometry`: line bboxes, block-height ratio, line-advance ratio,
and interline gap. `expectedVisualLineCount: 2` is not convergence. If the ink
regions overlap unexpectedly or the total block is timid/dense versus the
source, repair family, font-size, tracking, leading, and run sizes, then render
again before creating any below-FV section DOM.

For display lockups, implement the Phase 1 line/run decomposition literally:
each line and each measured typographic run is a real span with its own
`data-el`. Use `templates/poster-typography.css` run utilities to tune
`--run-size`, `--run-y`, `--run-tracking`, and per-run family/weight until
the rendered glyph crop matches the comp's optical height and baseline. Do
not keep Latin acronyms, numbers, kana particles, and kanji at one nominal
CSS size when the comp tuned them separately; same `font-size` is an
implementation convenience, not fidelity.

Structural type remains untransformed by default. The template uses font-size
and `vertical-align` for optical run balance; do not add `scaleX`, `scaleY`,
skew, rotate, or translate to force DOMRects onto glyph bboxes. Fix a remaining
miss through class-matched font metrics and flow spacing. Only the narrow,
source-evidenced `typeSpec.transformException` may opt out. After every type
repair, render the heading together with the next text block so line-box
clearance is visually verified, not inferred.

Do not "improve" the design. **Reproduce first; adjust second, on the
record.** Readability/CVR/brand adjustments come only after the section
survives its Phase 7 review in the comp's own terms, and each one is recorded
as `intentAdjustment`. "It reads better as a B2B LP" is the characteristic
drift that flattens a poster comp into a generic web page.

## Phase 5.5 — FV look-and-tune (new in v7; hybrid: required)

Before entering the box-diff loop, iterate the FV **visually**: render (or
in-app/MCP preview) at 1440 and 390, look at the screenshot, and tune until
the FV passes a poster-impression check with your eyes:

- photo reads as environment (integration rule above), not a pasted box;
- clean background plate has no baked-in text/logos/UI/design matter at 200%
  zoom, and DOM foreground layers recreate the comp devices;
- viewport-fixed/global elements (nav, vertical logo, edge labels) read as site
  chrome, not accidental hero children, and they do not cover the FV content;
- generated lettering decals have correct text, transparent/clean edges, and
  preserve their relationship to the photo or copy block;
- heading is unmistakably the protagonist; scale ratio ≈ comp's;
- mixed-script heading runs feel balanced: Latin/numerals are not optically
  small beside kanji, particles/kana keep the comp's intended smaller/larger
  role, and baselines match the crop;
- glass/curve/shadow devices read at comp craft level;
- palette is crisp (no unintended washes/veils);
- nothing collides with the subject's face / key photo detail.

2–4 iterations, screenshots kept in `reports/fv-tune/`. THEN run the box loop
to true up geometry. Rationale (field data): the box loop converges geometry
but cannot see beauty; runs that went straight to box-diff shipped FVs that
passed 29/43 boxes and still read as 30/100 web design. Look first, measure
second.
