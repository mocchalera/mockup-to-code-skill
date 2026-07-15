# Conditional specialist routing

Use this matrix to improve fidelity and production readiness without turning
every run into a maximal workflow. Evaluate conditions from the normalized
inputs, the manifest, and explicit handoff requirements. A skipped specialist
is not a missing phase when its condition is false.

## Routing order

| Order | Specialist | Invoke when | Consumes | Produces / binding | Skip when |
| ---: | --- | --- | --- | --- | --- |
| 1 | `visual-device-inventory` | `mode=hybrid` with two or more `section-comp` frames, or the comp contains source-specific devices whose decomposition is not obvious | normalized frames, section ids, source medium | `detail-inventory/v1`; bind as `specialistReports.deviceInventory` and copy its accepted items into manifest `detailInventory` | single simple clone already has complete measured element coverage |
| 2 | `typography` | Japanese or mixed-script display text, vertical text, optical run sizing, punctuation, or a critical wrap/resize contract | normalized text crops, manifest target ids | `typography-report/v1`; bind as `specialistReports.typography` | no critical typography condition exists |
| 3 | `photo-art-direction` | a critical `photo`/`illustration` uses `assetStrategy=generated` or `replace` | source quote/path, source geometry, inventory photo stories, exact prompt receipts and candidates | `photo-art-direction/v1`; bind as `specialistReports.photoArtDirection` before candidate adoption | the provided clean layered source is used unchanged, or the page is not photo-led |
| 4 | `imagegen` | the art-direction report has a source-grounded clean-plate brief, or `renderingCraft` classifies three or more sibling source devices as composite editorial illustrations requiring a style-bound sprite | one story/region brief or one icon-family sprite brief, plus exact prompt | generated candidates plus prompt-generation receipts; photo work records rejection/adoption, icon-family work retains chroma source, transparent master, extracted consumers, and integration review | art direction is blocked, an acceptable clean source exists, or icons are simple deterministic SVG/UI geometry |
| 5 | `design-whitespace` | multi-frame composition, high-finish production work, or measured macro/meso/micro spacing failures | comp bboxes, page-flow, DOMRects after first render | spacing scale, whitespace plan, responsive rules, measured repair evidence | spacing is already measured and within the parent run's tolerance; never replace page-flow/box gates |
| 6 | `seamless-section-waves` | a verbatim source/handoff asks for FV-to-next unity, seamless scrolling, a continuous section handoff, or a section-scale wave/arc repair | adjacent section strategies, outgoing environment, destination surface token, existing motifs, incoming preview targets | `seam-continuity/v1`; bind as `specialistReports.seamContinuity`, copy its layer/geometry plan into seam `continuity`, then prove desktop/mobile crops and `seam-pixel-check/v1` | no explicit continuity request and ordinary `pageComposition` seam evidence is sufficient; do not add waves by default |
| 7 | `design-motion-sequencing` | `motion.required=true` from a verbatim source or handoff requirement | comprehension order, manifest targets, settled-state contract; consume seam cue/preview targets when the continuity specialist created them | one or two motifs copied into manifest `motion`; runtime proof remains `motion-report/v1` from `motion-check.mjs` | motion was not requested; do not invent animation as polish |
| 8 | `responsive-image-delivery` | `productionReadiness.mediaDeliveryRequired=true` after final assets and layout are adopted | shipped asset paths, rendered sizes, HTML integration, LCP designation | `media-delivery-report/v1`; bind as `specialistReports.mediaDelivery` | fidelity-only prototype or no raster delivery asset; it must not change art direction |
| 9 | `lp-interaction-qa` | `productionReadiness.interactionQaRequired=true` and the page has links, CTA, fragment nav, forms, or scripted controls | final manifest, built page, intended destinations/endpoints | `interaction-report/v1`; bind as `specialistReports.interaction` | static visual prototype with no production-readiness claim |
| 10 | `visual-qa-pixel-polish` | fidelity evidence exists and an independent crop-only review or final production visual pass is due | crop pairs, screenshots, scores, parent artifacts | independent scores and `reviewProvenance`; no replacement for box/pixel/page-flow gates | implementation is still blocked before render evidence |
| 11 | `design-copy-structure` | production/hybrid mode and the user explicitly authorizes copy restructuring | approved message, existing copy, section hierarchy | section-to-copy hierarchy and change ledger | pixel-clone, fixed supplied copy, or translation/rewrite is out of scope |

## Machine-bound report rule

Every specialist report entry has exactly this receipt shape:

```json
{
  "contract": "<schemaVersion>",
  "path": "reports/<report>.json",
  "sha256": "<64 lowercase hex>"
}
```

The report file's `schemaVersion` must equal `contract`, the current file hash
must equal `sha256`, and its status must satisfy the phase. A pre-CSS planning
report may use the contract's explicit ready/pending state; completion requires
the specialist's pass state. `blocked`, unreadable, placeholder-filled, stale,
or hash-mismatched reports stop the parent phase. Prose cannot substitute for a
report required by the matrix.

## Ownership boundaries

- `mockup-to-code` owns source normalization, manifest ids, layout law,
  box/pixel/page-flow evidence, artifact audit, and computed completion.
- Inventory identifies devices; it does not decide DOM/CSS implementation.
- Photo direction preserves semantic and spatial intent; image generation makes
  candidates; asset policy decides whether the adopted file is usable.
- Whitespace repairs measured spacing only. Seam continuity owns the
  two-section boundary composition and exact target-surface handoff. Motion
  specifies comprehension order only; it may animate a cue but does not own
  the bridge geometry. None may hide a static fidelity failure.
- Media delivery optimizes copies of adopted assets and verifies markup. It may
  not recrop, recolor, or replace the approved art direction.
- Interaction QA judges operability and fallback states, not pixel fidelity.
- Independent visual QA cannot certify artifacts produced by the same reviewer.

## Efficiency rules

1. Evaluate all trigger conditions once after manifest measurement and again
   after production requirements are known.
2. Run pre-CSS specialists in parallel only when their inputs are independent;
   photo generation always waits for photo direction.
3. Re-run a specialist only when one of its hash-bound inputs changes.
4. Return the first blocking specialist in document/workflow order, repair it,
   then resume the parent pipeline.
5. Preserve `blocked` honestly when a browser, source, prompt receipt, endpoint,
   or codec needed for proof is unavailable.
