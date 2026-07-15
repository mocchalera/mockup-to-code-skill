---
name: mockup-to-code
description: >
  Convert static web-design mockup images (AI-generated or hand-made
  comp/カンプ, single image or a multi-frame section set) into
  high-fidelity, responsive HTML/CSS. Three modes: pixel-clone,
  production, hybrid (default for AI comps — regenerate photo/background
  rasters text-free and UI-free, rebuild type/UI in HTML/CSS, support
  verified generated lettering decals for non-structural handwritten
  decoration, reconstruct the visual language).
  Measurement-driven (manifest, box-diff repair, crop-pair evidence,
  axis-min review) with a hard LAYOUT LAW: content is built in flow/Grid/Flex
  inside responsive containers — measured rects are acceptance targets, never
  absolute coordinates. Includes multi-frame LP fidelity gradients, page
  composition, FV look-and-tune, and degraded-mode ladders. Trigger when the
  user wants a design image coded into a web page with high visual fidelity:
  「この画像をHTML/CSSにして」「カンプをコーディングして」
  「デザイン画像を再現して」 "code this mockup", "implement this design
  image".
---

# mockup-to-code

Reverse-engineer a static mockup into HTML/CSS through **measurement, not
eyeballing** — and into a **web document, not a screenshot**. You interpret
meaning and form hypotheses; scripts measure pixels; the browser answers with
DOMRects; box diff tells you what to fix; your eyes judge what rendered.

Detailed procedures live in `references/` — each phase below names its file.
**Read the named reference before running that phase**; this file alone is
not enough to execute a phase correctly.

**The few things agents skip — and must not.** The rest of this file is detail
for when you need it; these are the difference between a real run and theater:

- Isolate `WORK_ROOT`; normalize every comp before measuring.
- Photo-led rasters are **regenerated, not faked or dropped**: declare
  `mediaClass: photo`, generate to a file before any fallback, never reclassify a
  subject to svg/UI or ship a contaminated crop (rules 6, 13, 23–25).
- Run `asset_preflight.py` after photo asset decisions and before CSS. A crop
  that avoids fused text/UI by narrowing the scene still fails when it changes
  the comp's environment or focal composition (rule 27).
- Classify each visible device by owner and anchor before CSS: container content,
  hero-bound layers, viewport-fixed/global UI, edge typography, generated
  lettering decal, decoration, or background (rules 7, 16).
- Freeze every display block's source letterform class (gothic/mincho/rounded/
  display) before the font bake-off; never buy a bbox pass by distorting text
  with CSS transform. For Japanese, mixed-script, vertical, or display-critical
  work, invoke the `typography` skill and bind its run ledger/report into the
  manifest before CSS (rules 22, 28).
- Start hybrid multi-frame manifests from
  `templates/manifest.hybrid-multiframe.min.json`, then run
  `contract_doctor.py --phase pre-css` until it passes. This catches bbox
  arrays, missing measurement ledgers, global-header ownership mistakes,
  accidental FV line-wrap freedom, malformed page composition, and incomplete
  generated-photo evidence before CSS exists.
- Ask the pipeline what is legally next: `mockup_pipeline.py --phase next`
  returns one action, detects stale pre-CSS receipts, and caps runs that built
  below-FV DOM before FV convergence.
- `data-el` + manifest on every important element; box_diff, not your eyes, is
  the repair signal (rules 2–4, 8, 9).
- Flow/Grid/Flex only — measured rects are targets, never coordinates (rule 16).
- FV passes before any below-FV CSS (rule 19); the verdict is computed by
  `completion_gate.py` and reported verbatim (rules 18, 20).
- Run `artifact_check.py` before `completion_gate.py`: sparse crop pairs,
  missing bbox ledger, unchecked generated assets, or blended WEB/fidelity
  scoring means `needs_work` even when visual-check passes. The artifact report
  hash-binds the manifest/box/scores it audited; stale or swapped evidence cannot
  reach complete (rule 26).
- A clean `documentElement.scrollWidth` is not responsive proof. The widths
  sweep checks body width, root overflow suppression, meaningful-element visible
  ratios, and same-document fragments; `overflow-x:hidden/clip` cannot conceal
  missing content (rule 31).
- Multi-frame comps require executable `pageComposition` section/seam
  contracts. Run `page_flow_check.py` after rendering; a stack of repeated
  frame-height slabs, undeclared clipping, or unevidenced seams cannot reach
  complete (rule 30).
- When the source explicitly asks for a seamless FV-to-next handoff or scroll
  invitation, route `seamless-section-waves` and declare an
  `art-directed-bridge`: outgoing environment, opaque destination-owned field,
  one connective motif, and an incoming next-section preview. A readable wave
  crop alone is not continuity proof (rule 43).
- Inventory fidelity is machine-shaped: every `detailInventory` row maps to a
  completion disposition, and a different reviewer judges crop pairs without
  seeing implementation rationale. The lower score controls (rules 33–34).
- Generated card/object rasters declare who owns the frame, background, padding,
  radius, and bleed. A raster panel inside a CSS card is a double-frame defect.
- Freeze each critical raster's source topology before generation: a visual that
  owns the section field becomes a copy-space-aware full-field scene plate; an
  object/exploded diagram/collage that floats on the Web field becomes a real
  alpha scene including its shadow. Do not use a framed opaque fallback.
- Large section waves use measured bezier geometry or an off-canvas true-circle
  arc. A convenient stretched ellipse is blocked without source evidence.
- Critical Japanese headings declare viewport-specific line strings and orphan
  fragments; a stranded particle or inflection such as `て` is a hard failure.

## Hard rules (non-negotiable)

1. Do not estimate when you can measure (vision-only px only on `priority: low`, tagged `estimated`).
2. Hypothesis first, then measure that ROI — never measure globally.
3. Box diff is the repair signal; pixel diff is final QA only.
4. Every repaired element carries a `data-el` bound in the manifest.
5. Structural copy never ships as generated glyphs — headings, CTA, nav, body, legal and content labels are HTML/CSS text — but non-structural expressive lettering (speech bubbles, signatures, decorative callouts) may ship as a verified transparent raster/SVG `lettering-decal` with exact content proof. DO chase typographic treatment for HTML text (scale steps, tracking, weight, serif accents, mixed-script optical sizing).
6. Never ship a photo with baked-in text/design — regenerate, stock-replace, or placeholder+ask. No concealment.
7. Decide ownership, anchors, and layering before styling (placement ledger + layer plan precede CSS for FV/overlaps).
8. Fix the FIRST failing element in document order, then re-render.
9. Measure the comp BEFORE implementing; DOMRect-derived numbers are never fidelity evidence.
10. The comp's quality lives in its details — every visible device is inventoried and dispositioned.
11. Reproduce the motif, not a category stand-in (an outline 「止」 is that kanji, not "some shapes").
12. Additions never occlude comp devices; no self-granted waivers.
13. A visual's medium is part of the design — photo-class content stays raster; vector drawing only for decorative geometry, flat UI, icons. **Do not synthesize a photo/illustration background by drawing SVG/CSS/Canvas/Pillow/HTML and saving it as PNG; that is a prohibited fake asset, not `generated`.**
14. Verdicts are judged on rendered pixels via saved crop pairs, never on CSS/DOM inspection.
15. Account for the whole frame — the ground/environment is a device with its own inventory row.
16. **LAYOUT LAW: content lives in flow/Grid/Flex; `position:absolute` only for declared decorative/overlay layers.**
17. Degraded modes are earned (recorded failed attempt) and reported — never silently assumed.
18. Self-scores run ~3 points high — back every score with a crop-pair path.
19. **FV FIRST: below-FV implementation starts only after the FV gate passes** (5.5 tune + fv-critical boxes + impression metrics) — measured-but-unrepaired is the skill's central failure.
20. **The completion verdict is computed (`completion_gate.py`), never narrated** — the report headline carries its status; prose may explain a `prototype`, never promote it to 完了/complete.
21. Copy is transcribed character-exact from ≥2× zoomed comp crops and re-verified against the build crop — one wrong glyph (field case: comp 実行 shipped as 実装) is a content bug, verdict `missing`.
22. **Display typography is run-level.** In fv-critical lockups, Latin words, numerals, kana/particles, kanji, units, and emphasized words with different visual size/weight/baseline become span-level manifest elements. Equal CSS `font-size` is not equal optical size; tune by rendered glyph height and crop pairs.
23. **Contaminated raster backgrounds are regenerated by default.** If a raster region has baked-in structural text, logos, functional UI, cards, chips, charts, or foreground elements colliding with copy space, do not crop, blur, mask, or recolor it into service. Regenerate or replace it as a clean background plate first. Rebuild structural copy, controls, live data, and reusable shells as HTML/CSS. Decorative lettering and static screen artwork may stay inside a declared `card_artwork_plate` when they are part of one non-interactive visual composition.
24. **Photo-led regions are declared as photo.** Every manifest explicitly sets top-level `photoLed: true|false`. A photographic/illustration subject the comp shows (person, product, room, environment) requires `photoLed: true` plus an fv/section-critical `mediaClass: "photo"`/`"illustration"` row. You may not reclassify it to `svg`/`ui-mock`/`css`, nor drop it, to slip out of the asset policy — `asset_preflight.py` blocks `photoLed: true` with zero critical photo rows, and a non-photo generated asset never satisfies completion gate G8. Replacing a photographic subject with comp-absent invented UI (a dashboard, a chart panel, an empty card) is a fabrication of the rule-13 family and scores `missing`, never `adapted`.
25. **Generation is attempted before any fallback.** For a photo-led contaminated region, actually invoke the raster image generator and write a file to disk, then verify that path, BEFORE dropping to stock or placeholder. "I couldn't verify a generated asset" is never grounds to skip the attempt — run the generator, then check the file it wrote. Only a recorded, failed generation attempt (tool named, error captured) earns the descent to licensed stock → placeholder+ask.
26. **The artifact checklist is mandatory and content-bound.** Before completion, run `artifact_check.py`, pass its output into `completion_gate.py`, and report its status. It records SHA-256 receipts for the manifest/box/scores/reviews, rejects stale review/score order, and must be rerun after any audited input changes. A crop pair must be a readable non-empty file, not merely an existing path. A `needs_work` checklist (too few crop pairs, FV pixel `needs_work` or insufficient comparison coverage, missing `measurementRef`, tolerance override without reason, unchecked generated asset, or missing separate WEB品質/カンプ再現度 scoring) cannot be narrated as complete; a `blocked` checklist stops the run until evidence exists. Only Y-only recomposition rows are removed from both pass-rate operands; X/W/H failures remain eligible failures.
27. **The asset preflight is a pre-CSS stop.** Every fv/section-critical photo or illustration declares `visualRole`, `sourceFrameHasForegroundOverlap`, and `cleanLayeredSource`; when overlap is true, list `sourceFrameOverlapKinds`. `crop-asset` additionally proves `cropPreservesComposition` with `croppedAsset` evidence. Run `asset_preflight.py`; if `implementationAllowed` is false, do not write CSS for that section. A text-free subcrop of a fused full-field environment is still forbidden when it removes the scene, people, copy-space geometry, or focal relationships that made the comp.
28. **Structural text is not a transformable shape.** Headings, labels, CTA, body, dates, and prices default to `transform: none`: no `scaleX`, `scaleY`, skew, rotation, or visual translation to force a measured bbox. Repair with a class-matched font, weight, size, tracking, leading, run-level sizing, optical punctuation, and flow spacing. Only source-evidenced decorative lettering or unmistakably intentional display distortion may use `typeSpec.transformException`; re-render and prove it does not collide. `visual-check.mjs` blocks undeclared transforms and structural-text overlaps.
29. **Reconstruct the comp's layer topology before styling.** Decide whether a photo is a full-frame plate hidden by a foreground mask, a contained photo, a subject cutout over a clean plate, or an object detail tone-merged into a card. Record `photoCompositionMode`, the mask/frame `clipOwner`, card-photo edge treatment, and decorative-field craft. Do not mistake a visible right-side photo for a half-width background, place a section-wide veil outside the rounded frame that owns it, or replace bezier/gradient fields with flat polygons/straight bands.
30. **Multi-frame comps become one web page, not a stack of slides.** For every `section-comp`, declare `pageComposition.sections` with a content-led height strategy, density role, and bottom-edge/overflow ownership; for every adjacent pair declare an evidenced seam. Run `page_flow_check.py` on rendered section rects. Repeating one fixed height across all sections (especially the source-frame height), clipping every section, or using hard cuts at every seam is `needs_work` unless the user explicitly requested that exact uniform treatment and the manifest records the verbatim quote.
31. **Never hide responsive loss with root overflow.** `html`/`body { overflow-x: hidden|clip }` is not a fix for fixed-width content. At 320/390/768/1024/1440/1728, every non-decorative meaningful element must remain at least 98% horizontally visible (within 8px), or be an explicitly declared scroll region. Missing same-document fragment targets are hard failures.
32. **Masked pixel evidence must retain enough eligible pixels to mean anything.** `pixel_diff.py` reports total/masked/compared pixels and comparison coverage. Default minimum coverage is 50% for pixel-clone and 20% for hybrid/production. In hybrid, generated/replaced FV photo pixels are automatically excluded as intrinsically non-identical and coverage is computed over the remaining eligible pixels. If a verified generated/replaced full-frame plate leaves no pixel-comparable area, the explicit verdict is `not_applicable_generated_media`; it clears G3 only while asset policy G9, impression G6, box, crop-pair, and artifact gates pass. All other low coverage is `insufficient_coverage`, never `good` evidence.
33. **Detail inventory is a completion operand, not prose.** Hybrid multi-frame manifests carry one machine-readable `detailInventory` covering every section. Every row receives exactly one `disposition.inventoryId` plus readable pair or verbatim waiver. Source-specific devices cannot be mass-labeled `adapted`; `reviewPolicy.maxAdaptedSourceSpecificRatio` gates the volume.
34. **Self-review cannot certify itself.** Hybrid multi-frame completion requires a different human or agent to review crop pairs only. Record both reviewers, every section score, page score, top gaps, and reviewed pair paths in `section-scores.json.reviewProvenance`; the lower score controls and material score deltas return to implementation.
35. **Generated plates do not erase foreground QA.** A full-frame generated photo is masked, but opaque source-comparable FV surfaces such as CTA shells may opt into `pixelDiffForeground: true` with a reason. Their boxes are carved back into comparison; structural glyphs stay masked.
    Model an opaque shell and its text label as separate manifest/DOM rows; a text-bearing bbox cannot serve as a foreground carve-out because the text mask would erase it again.
36. **Requested motion is a contract, not polish prose.** When the source asks for motion, set `motion.required: true`, preserve the verbatim source quote, limit the plan to one or two comprehension motifs, and run `motion-check.mjs` in normal, reduced-motion, and JavaScript-disabled states. Static fidelity is judged in the settled state; motion never hides missing devices or broken CTA destinations.
37. **Specialists are conditionally routed and hash-bound.** Hybrid multi-frame work requires a completed `detail-inventory/v1`; generated/replaced critical photos also require adopted `photo-art-direction/v1`. Production-only media delivery and interaction QA run only when their explicit `productionReadiness` flags are true. Every required report is bound through `specialistReports`; a missing, stale, blocked, or non-passing report stops its parent phase.
38. **Source topology, generation boundaries, and web-surface integration are three separate contracts.** Before the raster prompt, classify the source as `section_field`, `floating_scene`, `contained_artwork`, `tone_merged_object`, or `source_visible_frame`, bind a source crop, and declare all four edge policies. Then choose `assetUnit` (`full_field_scene_plate`, `transparent_scene`, `card_artwork_plate`, etc.) and exactly one `surfaceIntegration.mode`: `alpha_floating`, `opaque_full_bleed`, `opaque_masked_merge`, `opaque_tone_matched`, or `intentional_frame`. A section field cannot be demoted into a centered image card; a floating scene cannot keep an opaque generator background. If CSS owns the card frame/background/padding, the raster must not duplicate them. `asset_preflight.py` reads the actual PNG alpha, edge color, uniform outer bands, and estimated content bounds; contradictory pixels return to image generation before CSS.
39. **Large curves have geometry, not just mood.** Section-scale waves and seam fields declare `decorativeCraft.geometryPrimitive`. Prefer measured bezier paths or an off-canvas true circle with recorded diameter and center. An ellipse requires a source-evidenced exception; `width != height` plus `border-radius:50%` is not a designed arc by default.
40. **Large decorative lettering is manifested and ordered.** Oversized kanji/watermarks need `data-el`, inventory binding, `zLayer`, and `mustStayBehind` targets. Unmanifested absolute display glyphs or foreground decoration crossing structural copy fail visual-check.
41. **Japanese line strings are responsive contracts.** Critical Japanese headings declare `typeSpec.responsiveLineContracts` with expected line strings and forbidden orphan fragments per width range. Validate rendered text-node line clusters, not `<br>` or span counts.
42. **A hybrid QA pass is pipeline-bound.** For multi-frame hybrid work, `visual-check.mjs` cannot report overall pass unless hash-bound pre-CSS contract-doctor and asset-preflight reports authorize implementation. Responsive integrity may be clean while the fidelity pipeline remains blocked; report both states.
43. **Explicit seamless-scroll intent becomes a cross-section contract.** Preserve the verbatim request in `pageComposition.seams[].continuity.sourceRef`, invoke `seamless-section-waves`, and bind `specialistReports.seamContinuity`. The bridge must include an opaque destination-owned surface and an incoming next-section preview plus at least one outgoing environment or connective motif layer. Completion requires desktop/mobile seam crops and a passing, image-hash-bound `seam-pixel-check/v1`; a generic divider, centered ellipse, or boundary-only crop cannot satisfy the request.
44. **A critical heading is an impression geometry, not merely a font label or line count.** Every fv/section-critical heading records `typeSpec.sourceImpression`: source-frame/block/line/glyph ratios, tracking, line advance, ink density, heading-to-lead/body/label jump ratios, desktop/mobile scale bounds, and evidence crop. Three distinct source frames may not reuse one identical bbox/type signature without `sharedSystemEvidence`. FV multi-line headings additionally record `typeSpec.posterGeometry`. The browser pass compares these metrics before the section can pass; correct strings with compressed air, extreme weight, timid viewport scale, weak hierarchy, or wrong line widths fail.
45. **Source-specific craft is frozen before CSS.** Every `sourceSpecific: true` inventory row carries `renderingCraft {medium, signatureTraits[>=2], minimumAtomicParts, atomicParts, genericStandInsForbidden:true, evidencePath}`. `minimumAtomicParts` describes the visible internal craft that must survive; it does **not** automatically require that many DOM nodes or image files. Bind separate manifest rows only when parts behave independently. For one static editorial composition, bind one `card_artwork_plate`, list its observed `atomicParts`, and keep the source-specific relationships inside that clean regenerated plate. A gift-box illustration is not `🎁`; a listener scene is not repeated `👩`; a composed device scene is not a Unicode glyph inside a generic white card. `contract_doctor.py` blocks missing craft, unexplained raster over-decomposition, and plates that hide their internal craft; `visual-check.mjs` still emits `generic-symbol-standin` when sensitive craft collapses into emoji/dingbat-only leaves.
46. **Icon medium follows complexity, not developer convenience.** Keep SVG for simple symbolic geometry and native UI controls. A source icon containing a person/pose, facial emotion, organic line character, three or more coordinated subparts, or illustration-specific accents is an `illustration`, not a cheap SVG challenge. Generate/adopt a transparent raster in the source style. When three or more icons share one visual family, prefer one receipt-bound chroma-key sprite sheet, verify cell separation and style consistency, remove the key, then extract one transparent PNG per semantic consumer. **Never divide a generated sprite by `image_width / expected_count` unless pixel evidence proves its cells really follow that grid.** Default to `split_sprite.py`: it measures occupied alpha-column clusters, reconciles them to the expected count, crops their real bounds, and blocks when any output cut edge contains alpha. CSS owns the card/frame/padding; generated cells contain only the artwork.
47. **The manifested surface owner must paint visible pixels.** Bind `data-el` to the `<img>`, `<picture>`, or background owner that actually renders a critical raster. An `opacity:0`, hidden, or zero-area duplicate cannot stand in for box measurement while another element paints the asset; `visual-check.mjs` blocks `surface-visible-owner`.
48. **Preflight binds asset bytes, not only manifest prose.** `asset-preflight.json.inputs.assets` records every adopted raster path, size, and SHA-256. Changing a PNG without rerunning preflight makes pipeline QA stale. After the first valid pre-CSS pass, an asset revision may re-enter pre-CSS with existing implementation files; never touch/delete files to game chronology.
49. **Topology feedback is a revision, not a CSS exception.** Record affected ids, old/new topology, source evidence, invalidated artifacts, and `remeasure_from_source`. Regenerate the affected asset and rebaseline its expected bbox from the comp or newly approved reference—never from the current DOMRect.

## Generated background gate

Before implementing any section whose comp uses a photo/illustration background,
write its asset plan into the manifest and follow rules 23–25. The default for a
contaminated raster is **regenerate a clean plate** (full decision tree in
`manifest-and-assets.md`):

- **Classify the full intended photo field before cropping.** Do not inspect only
  the rectangle you hope to ship. Set `sourceFrameHasForegroundOverlap` against
  the whole environment shown by the comp. If true, a narrower clean crop is not
  a clean source; use a separate clean layer, regenerate, or replace.
- **Attempt generation first.** A raster generator is usually reachable here
  (`cockpit gen-image`, a Codex/Firefly image tool, the user's stock account) —
  invoke one to a file. "I couldn't verify the output" is not grounds to skip the
  attempt: generate, then verify the file on disk and copy it into
  `"$WORK_ROOT"/assets/` with `generatedAsset {generator, prompt, workspacePath}`.
  A chat preview or tool response is not an asset until the path exists.
- **Issue the receipt before generation.** Save the exact prompt, then run
  `prompt_receipt.py issue`; it refuses an already-existing output. After the
  generator writes the asset, run `prompt_receipt.py adopt` and bind that
  receipt in `generatedAsset.generationReceipt`. A prompt file newer than the
  output, or a changed prompt/output hash, blocks pre-CSS.
- **Bind the exact prompt and inputs.** Store one UTF-8 exact-prompt file per
  adopted critical asset and record its SHA-256. `generatedAsset.prompt` must
  equal that file, not a retrospective summary. Every reference records path,
  hash, semantic role, and whether it was actually sent to the generator.
- **Make copy space measurable.** A full-frame FV plate declares canonical
  `copySpace` ROIs, `subjectZones`, and desktop/mobile
  `responsiveFocalPoints`. Prompt prose such as "left 40% clear" is not proof;
  the ROIs must stay in bounds and copy space may not intersect focal subjects.
- **Choose full-field scene vs transparent scene before generation.** A coupled
  hero scene that creates the section world uses `full_field_scene_plate` and
  owns the section edges. A paper object, exploded-layer diagram, device group,
  or collage that floats on the Web field uses `transparent_scene`, preserving
  coupled objects and soft shadows inside alpha while excluding the generator's
  outer white/paper rectangle.
- **Only a recorded, failed attempt earns `placeholder`** (a plain neutral block +
  blocker note). Never draw a "photo-like" scene in SVG/CSS/Canvas/Pillow and call
  it generated, and never reclassify the subject to `svg`/`ui-mock`/`css` with
  invented foreground UI (rule 24) — the field escape that shipped a hero as a
  fake "decision dashboard" and a testimonial as an empty panel. Gate G8 catches
  missing/reclassified photo media; G9 catches invalid source/crop decisions.
- **One semantic photo story per source device.** If the comp has separate
  phone/notebook/recorder scenes, create separate photo rows/assets. A shared
  panorama is allowed only with `multiZoneAsset.zones`: non-identical crop ROIs,
  subject signatures, consumers, and final crop-in-use pairs for every
  `detailInventory` photo id. A raw whole-plate pair is not integration proof.

```bash
python3 "$SKILL_DIR/scripts/asset_preflight.py" "$WORK_ROOT/manifest.json" \
  --work-root "$WORK_ROOT" --out "$WORK_ROOT/reports/asset-preflight.json"
```

## Layout law (rule 16, expanded)

Measured rects tempt you to copy `left/top/width` into absolute positioning: the
numbers match at 1440 and the build still fails at every other width (dead
gutter, no reflow). A run that did this scored 30/100 as web design at 29/29 boxes.

- Text, headings, buttons, cards, forms, in-section navigation, CTA groups →
  normal document flow, CSS Grid, or Flexbox. Two-column areas are grid/flex
  with breakpoints, never fixed left/right coordinates. Global site chrome
  (fixed header nav, persistent vertical logo/title, viewport-edge labels) may
  be `fixed`/`sticky` only when the Phase 1 ownership ledger declares it as
  viewport/global UI and the mobile release behavior is written down.
- Sections use a responsive container: `width: min(var(--content-max), 100% - 2*var(--gutter)); margin-inline: auto;`.
- `position: absolute`/`fixed`/`sticky` is allowed only for:
  layer-plan-declared overlays (background photo layers, overlay gradients),
  decorative layers (outline watermark type, accent bands, curves), badges
  pinned to a parent, viewport/global chrome, and true comp overlaps — each
  declared in the manifest with matching `positioning` and a `layerRole`.
  visual-check audits computed CSS against this (`layout-law` violation).
- **Measured rects are acceptance targets, not implementation instructions.**
  Reach the target bbox at 1440 by flow means (container width, grid tracks,
  gaps, paddings, font metrics). If it matches at 1440 but creates dead
  space, overflow, or broken reflow at 320/390/768/1024/1440/1728, it fails the
  `--widths` sweep (Phase 7).
- Text bboxes follow the same law: do not apply CSS transforms because a glyph
  bbox is tall/narrow. A transformed glyph can pass DOMRect geometry while its
  strokes, counters, baseline, and following-flow clearance are visibly wrong.

## Fidelity modes (decide first, record in manifest `mode`)

| mode | goal | primary signal | typical input |
| --- | --- | --- | --- |
| `pixel-clone` | reproduce ONE authoritative comp exactly | box diff → masked pixel diff | hand-made comp, site screenshot |
| `production` | clean production code informed by the comp | box diff on key elements, relaxed | comp + real content/CMS reality |
| `hybrid` | **reconstruct the comp's visual language** | layer plan + box diff + visual-check + section review | **AI-generated comp** (the usual case) |

**Hybrid is the default for AI comps**: photo, type and decoration are fused
into one raster — you *decompose*: background plates are regenerated,
replaced, or extracted text-free/UI-free; ALL type and UI are rebuilt in
HTML/CSS; stacking is designed explicitly. When text or UI overlaps the
photo, the clean background plate comes first, then the foreground DOM
layers. Success is judged on FV impression, typographic hierarchy, photo use,
layering, responsive integrity, and whether the comp's small devices
survived.

**Hybrid changes the medium, never the bar.** It licenses *rebuilding* in
different material (HTML type, regenerated photos), not a looser resemblance.
Flow-first recomposition (reordering / taller sections) waives **cross-section
y-position only**; every element's scale, density, tone, and internal layout are
judged at full strictness. "Hybrid residual" prose is not a license to narrate a
box-4/23 build as complete — `completion_gate.py` computes the verdict.

**Multiple reference images — which case are you in?**

- **Mood boards / alt comps** = visual-language sources: sample from them,
  register with `use: "visual-language"`, reproduce only the primary comp.
- **A sectioned comp set** (ref-01…NN, one image per section of ONE page) =
  **multi-frame hybrid**: register each with `use: "section-comp"` +
  `section`, normalize ALL frames to one width, set per-element
  `sourceImage`. QA is scoped per frame with the **fidelity gradient**:
  - **FV frame: near-pixel-strict** — judged like a poster comp, full
    box-diff depth, masked pixel diff.
  - **Below-FV frames: essence-first, flow-first** — reproduce each frame's
    essence ledger and internal hierarchy; heights, margins and seams belong
    to the executable `pageComposition` plan (Phase 4.5). Frame height is a
    one-sided **density floor** (shorter = collapsed = fail; taller = fine),
    not a target copied into every section. The frames
    are separately-generated 16:9 slides — their letterbox geometry is a
    generator artifact, not a design decision. Chasing it yields "half-
    faithful everywhere, compelling nowhere".

## Pipeline (phases × modes × required artifacts)

Environment first: `bash "$SKILL_DIR/scripts/setup_env.sh"` → prints
`SKILL_DIR`, script inventory, browser/python status, RECOMMENDED MODE.
`$SKILL_DIR` = this skill's directory (scripts are NOT in your project).
`$WORK_ROOT` = output root, default `work/`; isolate fresh runs
(`references/fallbacks.md`).

For hybrid multi-frame work, initialize once with the unified runner; it refuses
to overwrite an existing run and copies all machine-shaped starters:

```bash
python3 "$SKILL_DIR/scripts/mockup_pipeline.py" "$WORK_ROOT" --phase init
# at every hand-off between phases:
python3 "$SKILL_DIR/scripts/mockup_pipeline.py" "$WORK_ROOT" --phase next
# after measurements, asset decisions, inventory, and specialist reports:
python3 "$SKILL_DIR/scripts/mockup_pipeline.py" "$WORK_ROOT" --phase pre-css
```

`pre-css` must report `implementationAllowed: true` before Phase 5 (`pass`
normally; `needs_work` only for an asset-policy-earned placeholder). Run the
doctor again with `--phase completion` after scores exist; it is a shape/policy
gate before, not a replacement for, `artifact_check.py` and
`completion_gate.py`.

| # | phase | reference | pixel-clone | production | hybrid |
| --- | --- | --- | --- | --- | --- |
| 0 | normalize frames | measurement.md | req | req | req (every frame) |
| 1 | hypotheses: ownership/anchor ledger, essence, machine-readable detail inventory (+ground row), lettering-vs-HTML copy split, type spec with separate visual-line/run counts, typography specialist report, bake-off | measurement.md | important els | key els | **req** |
| 2 | measure bboxes/colors | measurement.md | every important el | key els | FV + section-critical |
| 3 | manifest (+`positioning`, media class, asset strategy) | manifest-and-assets.md | full | full | full (sparse bboxes OK) |
| 3.25 | contract doctor (shape, ownership, FV line counts, page/photo contract) | manifest-and-assets.md | req | req | **req before CSS** |
| 3.5 | asset preflight (source overlap, composition, on-disk proof) | manifest-and-assets.md | req for photo/illustration | req | **req before CSS** |
| 4 | layer plan (+photo edges, decoration craft) | composition.md | where overlap | where overlap | **req for FV + overlaps** |
| 4.5 | executable page composition plan (`pageComposition`: section strategies, edge ownership, seams; art-directed continuity when requested) | composition.md | — | — | **req multi-frame** |
| 4.75 | conditional motion plan (`motion.required`, max two motifs, settled/reduced/JS-off contract) | composition.md | when requested | when requested | when requested |
| 5 | implement (layout law; FV first) | composition.md | — | — | — |
| 5.5 | FV look-and-tune (eyes before boxes) | composition.md | optional | recommended | **req** |
| 6 | box loop, desktop+mobile (**FV converges before below-FV is built** — rule 19) | qa.md | full | critical+high | FV full; below-FV section-critical |
| 7 | visual-check + `--widths` sweep + computed page flow + inventory dispositions + independent crop-only review (+impression metrics, copy proof, top-5 gaps) + FV gate | qa.md | recommended | required | **req — this is the bar** |
| 7.5 | motion runtime QA (`motion-check.mjs`) | qa.md | when requested | when requested | when requested |
| 8 | masked pixel diff | qa.md | req | optional | FV frame req |
| 9 | responsive finish | qa.md | after 8 | after 8 | continuous since 6 |
| 9.25 | completion-shape doctor (`section-scores` arrays/rows) | qa.md | req | req | req |
| 9.5 | artifact checklist (crop-pair/FV/asset/bbox/report audit) | qa.md | req | req | req |
| 10 | completion gate (computed verdict) | qa.md | req | req | req |

**Minimum artifact checklist (hybrid multi-frame)** — a missing artifact is a
skipped phase: normalized frames in `$WORK_ROOT/mockups/`;
`reports/hypotheses.md` (ownership/anchor ledger, asset plan, lettering-vs-HTML
copy split, essence ledgers, detail inventories ending in the ground row, type
specs with separate visual-line + script/word-run counts, optical-size ratios,
bake-off record, and typography specialist report);
`manifest.json`; `reports/contract-doctor.json` with `status: pass`;
`reports/asset-preflight.json` with
`implementationAllowed: true`; background/foreground decomposition +
clean-raster asset review + lettering-decal asset review; layer-plan +
page-composition blocks;
`reports/fv-tune/` screenshots;
desktop+mobile renders from the first loop iteration;
`--section-relative` box report; visual-check + widths-sweep JSON (including
320px and semantic visible-ratio metrics);
`reports/page-flow.json` plus a readable crop/screenshot for every seam;
hash-bound `seam-continuity/v1` plus desktop/mobile crops and
`seam-pixel-check/v1` for every explicitly requested art-directed bridge;
`reports/crops/` pairs; `reports/section-review.md` (FV gate, dispositions
with pair paths, hex pairs, axis-min scores, additions table, page-flow
review, **impression-metrics table, copy proof, top-5 visible gaps, separate
WEB品質 and カンプ再現度 self-scores**); machine-bound `detailInventory`
dispositions; `reviewProvenance` with a different crop-only reviewer;
FV masked pixel diff with comparison coverage; `reports/artifact-check.json`
with input hash receipts and freshness checks; `reports/section-scores.json` +
`reports/completion-verdict.json` (Phase 10).

### Specialist routing (invoke only when the condition is present)

Run the deterministic routing matrix in `references/specialist-routing.md`.
The default specialist chain is inventory → typography/photo direction →
implementation → whitespace/motion → media delivery/interaction → independent
visual QA, but every step is conditional. Hash-bind machine reports through
`specialistReports`; do not invoke a specialist merely because it exists.

**When the environment caps you**, spend verification in the evidence-ladder
order (`references/fallbacks.md`): FV crop pairs → FV box diff + pixel diff →
mobile FV → per-section screenshots + crop pairs → full box loop → widths
sweep. Honest partial evidence + a blocked note beats retrying a dead browser.

## The design-quality bar (why Phase 5.5 and 7 exist)

Box convergence cannot see beauty. The rules that carry the "as a website" score
live in `composition.md` (device craft) and `qa.md` (impression metrics); the
flags to remember:

- **Photo integration** — an environment photo never ends in a hard rectangle:
  bleed / mask-gradient it into the adjacent field, or frame it only if the comp
  does. Declare each edge.
- **Ownership and anchors** — fixed headers, viewport-edge vertical logos,
  hero-bottom watermarks, photo-bound callouts and container content are different
  implementation objects; preserve the relationship, not just the 1440px rect.
- **Decoration craft** — a curve is an SVG bezier with the comp's sweep, glass is
  blur+translucency+edge light. A straight line for a curve is `missing`.
- **Typography integrity** — the source letterform class wins before bbox size;
  a gothic comp rebuilt in mincho or a non-uniformly scaled heading fails even
  when box diff is 100%.
- **Layer topology** — masks/veils clip to the frame that owns them; staggered
  cards keep their offsets; object photos tone-merge with card fields; CTA
  portraits use a full plate or plate+cutout when the comp does.
- **Look first, measure second** — Phase 5.5 tunes the FV visually (2–4 iterations)
  before the box loop trues up geometry.
- **Impression is measured, not vibed** — four FV numbers (lockup scale, mixed-
  script optical ratios, photo-tone luminance, repeated-device scale+clip) feed
  `impression-metrics.json` and gate G6, catching a lockup that shrank, `AI` gone
  optically small, a photo gone dark, cards grown 1.4× and clipped.
- **The page is judged as a page** — seams, motif continuity, whitespace rhythm
  (Phase 4.5 contract, Phase 7 computed page-flow review). Four 8/10 sections
  can compose a 5/10 page; G10 prevents that page from being called complete.
- **A bridge is not a divider** — for explicit continuity requests, judge the
  outgoing field, opaque destination surface, connective motif, and incoming
  preview in one desktop and one mobile crop. Exact destination color is a
  pixel contract; the feeling of continuation is a two-section composition.

## Browser discipline

ONE browser at a time — parallel launches SIGKILL each other under memory
pressure. render/visual-check hold a launch lock and retry; if they still fail,
walk the transport ladder (do NOT loop retries) and earn any degraded mode with a
recorded failure. Full ladder + no-OpenCV policy: `references/fallbacks.md`.

## Command reference

All scripts under `$SKILL_DIR/scripts/`; outputs under `$WORK_ROOT`.

| Script | Purpose |
| --- | --- |
| `setup_env.sh` | preflight: SKILL_DIR, script inventory, browser/python, recommended mode |
| `normalize_image.py in.png --width 1440 --out $WORK_ROOT/mockup.png` | canonical coordinate space |
| `profile.py img --axis y [--roi x,y,w,h]` | section bands / container edges |
| `snap_bbox.py img --bbox x,y,w,h [--radius 16]` | refine hypothesis bboxes (cv2) |
| `sample_color.py img --roi x,y,w,h [--exclude …]` | measured color tokens |
| `crop_asset.py img --roi x,y,w,h --out f.png` | candidate crop + pixel contamination check; never authorizes adoption; use `--purpose evidence-crop` only for rendered QA strips |
| `crop_pair.py --comp f --comp-roi … --build f --build-roi … --out pair.png [--zoom 2]` | side-by-side verdict evidence (Pillow-only OK) |
| `mockup_pipeline.py $WORK_ROOT --phase init\|pre-css\|completion` | non-overwriting setup and ordered gate orchestration; writes `reports/pipeline-summary.json` |
| `mockup_pipeline.py $WORK_ROOT --phase next` | return one allowed action; reject stale receipts, premature below-FV DOM, missing FV tune/impression, and non-pass completion artifacts |
| `prompt_receipt.py issue\|adopt …` | prove the exact prompt existed before generator output and bind prompt/output hashes |
| `split_sprite.py <transparent-master> --count N --names … --out-dir … --report …` | split generated icon sheets by measured alpha clusters; do not assume equal-width cells; block clipped/mixed cut edges |
| `contract_doctor.py $WORK_ROOT --phase pre-css\|completion --out report` | stdlib contract preflight: blocks malformed bbox/score containers, global ownership drift, FV line-count freedom, incomplete page/photo contracts before downstream tracebacks |
| `asset_preflight.py manifest --work-root $WORK_ROOT --out report` | pre-CSS gate: rejects fused-source crop reuse, changed composition, missing generation/fallback evidence, invalid alpha/edge-band/color/mask surface integration |
| `render.mjs --html f --viewport WxH --out-png f --out-rects f` | render + DOMRects (locked, retrying) |
| `box_diff.py manifest rects --out report [--section-relative]` | document-order repair signal; reports default vs manifest tolerance provenance; multi-frame REQUIRES the flag |
| `visual-check.mjs --html f --manifest m --viewports 1440x900,390x844 --out f` | intent + typography-transform/overlap verification |
| `visual-check.mjs … --widths 320,390,768,1024,1440,1728 --out f` | responsive integrity + layout-law + visible-ratio + fragment audit |
| `motion-check.mjs --html f --manifest m --out reports/motion-check.json` | conditional normal/reduced/JS-off motion, target, CTA, and manifest-receipt QA |
| `page_flow_check.py manifest rects --work-root $WORK_ROOT --out reports/page-flow.json` | multi-frame Web-native flow gate: height rhythm, section overflow ownership, adjacent seam evidence |
| `pixel_diff.py mockup rendered --manifest m --out-heatmap d.png` | final pixel QA (cv2), including comparison-coverage sufficiency |
| `artifact_check.py $WORK_ROOT --out reports/artifact-check.json` | pre-completion evidence audit: crop pairs, FV coverage, bbox ledger, generated assets, input SHA/freshness, two-track scoring |
| `completion_gate.py manifest box-report --visual-check … --widths-check … --scores … --artifact-check … --fv-pixel … --impression … --out verdict.json` | hash-bound computed completion verdict: complete / prototype / blocked (stdlib-only) |

## Failure modes (top; more in each reference)

| Symptom | Fix |
| --- | --- |
| Content absolutely-positioned to match rects; dead right gutter off-1440 | Layout law: rebuild in flow/grid; rects are targets, not coordinates; run `--widths` sweep |
| `responsive-check` passes only after adding `overflow-x:hidden/clip` | root overflow is concealing content; inspect `responsive-visible-ratio`, fix fixed tracks/breakpoints, and rerun 320–1728 widths |
| FV "cheap" despite passing boxes | photo framed as card / typography not chased → layer plan `.fv-bg`, poster-typography, Phase 5.5 |
| Text/UI-contaminated raster crop reused as a background | rule 23: regenerate or replace a clean background plate; rebuild text/cards/charts as DOM layers; crop reuse is `missing` |
| Adopted crop is text-free only because it excludes the overlapped half of the room/scene | rule 27: set `sourceFrameHasForegroundOverlap: true`; the crop is forbidden unless a separate clean layered source exists. Regenerate/replace the full composition; G9 blocks completion. |
| Structural copy shipped as a generated lettering image | rule 5: only non-structural decorative callouts/signatures can be `lettering-decal`; headings/CTA/nav/body/legal stay HTML/CSS |
| Fixed header or vertical logo stuffed into hero flow to match the FV | Phase 1 ownership ledger: classify as `viewport-fixed`/global UI, manifest `positioning: "fixed"` or `sticky`, then preserve responsive behavior |
| Photo-led region reclassified to svg/UI or dropped, then scored "adapted" | rules 24–25: declare it `mediaClass: photo`, attempt generation to a file first; a removed/reclassified photographic subject is `missing`, not `adapted`; gate G8 catches it |
| Generator available but never invoked ("couldn't verify output" → skipped) | rule 25: run the raster generator to a file, then verify; only a recorded failed attempt earns stock/placeholder |
| Prompt file was written after image generation | run `prompt_receipt.py issue` before the generator and `adopt` after output; retrospective summaries and stale receipts block pre-CSS |
| Agent draws a photo/illustration with SVG/CSS/Canvas/Pillow and saves PNG | invalid fake asset — delete/reject it; use image generator / licensed stock / owned clean asset / placeholder+ask |
| Many elements fail diff at once | cascade — fix ONLY first_fix, re-render |
| `box_diff.py` crashes because `bbox` was written as `[x,y,w,h]` | Start from the hybrid manifest template and run `contract_doctor.py --phase pre-css`; bbox is always an object `{x,y,w,h}`. Direct box_diff now emits a blocked JSON report instead of a traceback. |
| Sticky/fixed header outside a section gets a fake section-relative y delta | Declare `placementScope: viewport-fixed\|viewport-edge`, `positioning: sticky\|fixed`, viewport anchor, and mobile behavior; box_diff compares it in `viewport-global` coordinates. |
| FV heading block suddenly grows after its container narrows | Record `typeSpec.expectedVisualLineCount`; record `expectedRunCount` separately when script runs exist. visual-check raises `typography-line-count` when wrapping changes. |
| FV heading has the right two lines but reads as a dense black lump | Line count is insufficient: measure `posterGeometry` from the source, compare line bboxes, block-height ratio, line-advance ratio, and signed interline gap on the first render; do not author below-FV DOM until these pass. |
| Box diff passes but page looks nothing like comp | manifest back-filled from own render (rule 9) — re-measure from comp |
| Page reads as stacked slides | Declare `pageComposition` section strategies + every adjacent seam, make bottom-edge ownership explicit, capture seam evidence, then run `page_flow_check.py`; equal frame-height slabs trigger W4/G10 |
| FV and next section are separated by a smooth wave but still feel like two slides | source requested continuity → route `seamless-section-waves`, set seam `continuity.required:true`, compose outgoing environment + opaque target surface + connective motif + incoming preview, then prove desktop/mobile crops and destination-color samples |
| Specific motif became generic shapes | rule 11; inventory content-level rows; verdict `missing` |
| Detailed line art/UI/card composites became emoji, dingbats, or one repeated white-card shell | rule 45: freeze `renderingCraft` traits and atomic parts before CSS; bind the real device rows; `generic-symbol-standin` is a hard visual-check failure unless the source itself evidences a text glyph |
| Static card art was split into laptop, phone, screens, torus, plinth, and shadows with no independent behavior | rules 38/45: use one `card_artwork_plate`; keep the outer shell/label in CSS and record observed `atomicParts` plus `keepTogetherReason` |
| Hero scene that owns the whole visual field was reduced to a right-side image card and cropped | rule 38: sourceTopology=`section_field`, generate one `full_field_scene_plate` with measured copy space, asset-owned bleed and four-edge policy; do not proceed to CSS with the framed asset |
| Paper object, exploded layers, or audience collage sits inside a generator-white rectangle | rule 38: sourceTopology=`floating_scene`, regenerate one `transparent_scene` including coupled objects and soft shadow; opaque output returns to image generation |
| Complex people/emotion/object icons look amateurish after hand-authored SVG tracing | rule 46: reclassify composite editorial icons as illustration; generate one style-bound chroma sprite for the family, remove the key, extract transparent consumer PNGs, and keep CSS surface ownership outside the raster |
| A generated sprite was divided into equal widths and an icon is clipped or contains part of its neighbor | rule 46: reject arithmetic slicing unless verified against pixels; run `split_sprite.py` with the expected count, inspect its measured clusters, and require zero alpha on every output cut edge |
| Review says `present`, render shows it broken | rule 14: crop-pair evidence for every verdict |
| Self 8/10, user 5/10 | rule 18 calibration; re-judge from pairs; independent review if possible |
| Every section scored exactly 7 (the pass bar) | uniform-threshold scoring — gate warning W1; re-judge from pairs with impression metrics in hand |
| box 4/23 + pixel needs_work narrated as "hybrid residual", reported 完了 | rule 20: run `completion_gate.py`; headline = its status (`prototype`), list the top-5 visible gaps |
| Comp copy 実行 shipped as 実装; no check fired | rule 21 copy proof: transcribe from ≥2× zoom crop, re-verify glyph-by-glyph against the build crop |
| Mixed heading like `AI駆動型へ` feels wrong though bbox is close | rule 22: split into span-level runs, measure optical height ratios vs anchor kanji, tune size/baseline/tracking |
| Heading passes bbox but looks stretched/condensed and collides below | rule 28: remove structural-text transforms; repeat class-matched font bake-off, then tune size/weight/tracking/leading and flow clearance |
| Source is gothic but build uses mincho | Phase 1 letterform class was not frozen; reject the candidate before geometry repair and re-run the class-matched bake-off |
| Line begins with `「` and looks indented though its DOM x matches | use optical punctuation alignment (`hanging-punctuation` or a flow-safe inline-start correction) and prove the ink edge with a crop pair |
| Organic blue/green field became flat bands or a polygon | record `decorativeCraft` and reproduce the curve/gradient topology with SVG/CSS gradient or a clean generated decorative raster |
| Staggered photo cards look like identical rows with pasted photos | preserve per-card offsets and `cardPhotoIntegration`; match card/photo ground tone and dissolve only the comp-visible edges |
| Generated object image already contains a rounded panel, then CSS wraps it in another card | declare `assetSurfaceContract`; generate one semantic asset per consumer with no baked panel/padding/radius when CSS owns the surface; prove isolated asset + crop-in-use |
| Opaque artwork looks clean alone but creates double padding or a paper-color seam in the card | declare `surfaceIntegration`; inspect real PNG alpha/outer bands/content bounds/edge RGB. Regenerate as `alpha_floating`, bleed or mask the plate, tone-match the edge, or preserve a frame only when the source visibly has one |
| Manifest calls a source-floating scene `contained_artwork` after generation because alpha was difficult | source topology is frozen from the comp, not chosen from output convenience; asset preflight blocks the mismatch and returns to generation |
| Below-FV headings all became the same dense ultra-bold style | measure `typeSpec.sourceImpression` per section; reject repeated generic bbox/type signatures, compare viewport-scale and jump ratios, then tune weight/tracking/leading against glyph ink rather than the category label |
| Footer/section wave is a stretched `border-radius:50%` oval | replace it with measured bezier geometry or a true off-canvas circle; an ellipse needs source crop + `ellipseException` |
| Oversized background 「聴」 paints over the heading | manifest the glyph with `data-el`, `zLayer`, and `mustStayBehind`; unregistered large absolute text fails visual-check |
| Japanese heading strands 「て」/「へ」/unit on its own line | declare `responsiveLineContracts`; compare actual rendered line strings and forbidden orphan fragments at each width |
| Rounded framed photo section has a page-wide veil | assign the veil/photo to the frame `clipOwner`; apply radius/overflow/mask at that owner, not the section root |
| CTA person is cramped into the right half | reclassify the source topology: generate a full-frame plate with copy space, or separate environment + subject cutout when the comp requires independent placement |
| FV measured, residuals logged, below-FV built anyway | rule 19: FV converges first — 3–5 FV-scoped box iterations before any below-FV CSS |
| Requested reveal/flow motion became hover lifts or smooth scroll only | rule 36: record one or two source-backed motifs, test real runtime events, reduced motion and JS-off visibility; broken/placeholder CTA destinations fail motion QA |
| visual-check passes but crop pairs / asset proof / bbox ledger are thin | rule 26: run `artifact_check.py`; `needs_work` leads the report, `blocked` stops completion |
| `section-scores.json` was keyed by section and artifact_check crashed | Copy `templates/section-scores.min.json`; `sections` and `dispositions` are arrays. The completion doctor and downstream gates now return blocked evidence instead of a traceback. |
| FV pixel diff says `good` after masking most of the frame | rule 32: check `comparison_coverage`; reduce masks or honestly report pixel evidence unavailable |
| Regenerated full-frame hybrid photo yields a meaningless high pixel diff | rerun current `pixel_diff.py --manifest`; generated/replaced FV photo regions are auto-excluded. A fully regenerated plate reports `not_applicable_generated_media` and remains bound to asset, impression, crop-pair, box, and artifact gates. |
| Full-frame generated photo makes every foreground device disappear from pixel QA | Mark only opaque source-comparable foreground shells `pixelDiffForeground: true`; text remains masked. The contract doctor blocks a full-frame generated FV with foreground devices but no carve-out. |
| Distinctive dots, icons, arrows, or micro-props all become `adapted` while the page completes | Bind every Phase 1 row through `detailInventory` → `disposition.inventoryId`; the source-specific adaptation ratio and independent crop review prevent blanket simplification. |
| Comp device waived "because the handoff prioritizes X" | self-waiver: `waived` needs the user's verbatim words |

Per-phase failure modes (hard-rectangle photos, curves→lines, y-waived children,
device-scale clip, mood shift, no-OpenCV, dirty `work/`, webfont stalls) live in
the reference file for their phase — `composition.md`, `qa.md`, `fallbacks.md`.

## Files

- `references/measurement.md` — Phases 0–2 (normalize, hypotheses, inventory, type spec, bake-off, measuring)
- `references/manifest-and-assets.md` — Phases 3/3.5 (manifest contract, fonts, media-class asset policy, pre-CSS gate)
- `references/composition.md` — Phases 4/4.5/5/5.5 (layers, photo edges, decoration craft, page plan, FV tune)
- `references/qa.md` — Phases 6–9 (box loop, visual-check, section review, verdicts & scoring, pixel diff, responsive)
- `references/fallbacks.md` — setup, WORK_ROOT isolation, no-OpenCV, browser ladder, evidence ladder, completion report
- `references/specialist-routing.md` — conditional specialist triggers, ordering, report contracts, and skip rules
- `references/fv-poster-example.md` — worked hybrid FV example
- `templates/` — base.css, poster-typography.css, hypotheses.md, section-review.md, photo-asset-review.md, `manifest.hybrid-multiframe.min.json`, `section-scores.min.json`
- `schemas/element_manifest.schema.json` — manifest contract (incl. `positioning`, `layerRole`, `qaPriority`, asset fields)
- `VALIDATION.md` — per-version field feedback and test evidence
