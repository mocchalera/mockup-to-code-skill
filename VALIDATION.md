# mockup-to-code — Validation Report

## v27 addendum (2026-07-15, macOS arm64)

v27 closes three workflow gaps exposed by the full-page surface-integration dogfood pass.

| Field failure | New executable guard | Verified result |
| --- | --- | --- |
| A hidden full-screen `<img>` carried `data-el` only to satisfy geometry while CSS painted the real hero | `visual-check.mjs` audits every manifested raster surface owner for visibility and non-zero area | opacity-zero proxy fixture fails `surface-visible-owner` |
| Regenerated PNG bytes could change while old preflight stayed valid because only manifest JSON was hashed | `asset-preflight.json.inputs.assets[]` binds adopted path, size, and SHA-256; pipeline runner and browser QA verify live bytes | mutation regression returns `run-pre-css` with `staleEvidence.assetFiles:true` |
| Re-entering pre-CSS after user topology feedback required touching or hiding existing implementation files | chronology is established by the first hash-bound pass; later revisions re-enter while current manifest/asset receipts enforce freshness | three consecutive pre-CSS runs with an existing site pass, while implementation before the first pass remains blocked |

The documentation also adds a topology-revision ledger and requires bbox rebaselining from source evidence rather than current DOMRect.
Validation evidence: full `npm test` passes all 154 component tests, including
the new chronology, raster-byte mutation, and visible-surface-owner regressions.

## v26 addendum (2026-07-15, macOS arm64)

v26 turns the second LP review into a source-surface-first generation and
handoff contract. A clean bitmap is no longer sufficient when it expresses the
wrong relationship to the Web field.

| Field failure | New executable guard | Verified result |
| --- | --- | --- |
| Hero visual that owned the whole section was reduced to a cropped right-side image card | `sourceTopology=section_field` requires `full_field_scene_plate`, asset-owned bleed, four-edge policy, and measured copy space | an intentional/framed substitute blocks with topology-mode, invented-frame, and must-bleed findings |
| Paper object, exploded layers, or audience collage kept the generator's white/paper rectangle | `sourceTopology=floating_scene` requires `transparent_foreground` or `transparent_scene` plus `alpha_floating` | opaque fixture blocks; coupled-object + shadow RGBA fixture passes |
| Generation output convenience silently changed source topology | every generated/replaced critical raster now requires `assetUnit`, `assetSurfaceContract`, `surfaceIntegration.sourceTopology`, source crop, and four-edge policy before CSS | missing contracts and incompatible topology/unit/mode combinations block pre-CSS and completion G9 |
| Static card interiors were at risk of being overcorrected into separate alpha parts | `contained_artwork` remains compatible with one `card_artwork_plate`; CSS still owns the outer shell | existing static-composite positive control remains green |

Validation evidence: full `npm test` passes all 150 component tests, including
35 contract-doctor, 18 asset-preflight, 22 artifact-check, and 22 completion-
gate tests. Template/schema JSON parse, Python compilation, diff checks, and
Skill Creator validation are run with the paired skill package checks.

## v25 addendum (2026-07-15, macOS arm64)

v25 turns the Web Visual Section Mock LP feedback into two executable handoff
gates: source-measured typography impression and real-pixel raster surface
integration.

| Field failure | New executable guard | Verified result |
| --- | --- | --- |
| “Bold gothic” became ultra-black, tightly tracked type and below-FV headings reused generic geometry | every critical heading requires `typeSpec.sourceImpression`; doctor checks bbox agreement and repeated signatures across distinct source frames | missing/timid profiles and three-frame generic copies fail before CSS |
| Correct copy and line count still shipped at a timid viewport scale with weak hierarchy | typography reports bind source-impression tolerances and completion states report block/line/glyph, tracking, advance, ink-density, and jump-ratio measurements | out-of-tolerance browser states cannot pass typography completion |
| Opaque generated art carried its own paper/white margin into a CSS-owned card | `surfaceIntegration` is independent from `assetUnit`; stdlib PNG inspection measures alpha, edge RGB, uniform outer bands, and estimated content bounds | opaque uniform-band fixture reports both alpha failure and double-padding risk; transparent fixture passes |
| Asset and Web backgrounds were visually similar but not seamless | `opaque_tone_matched` compares measured edge RGB to the declared consumer color; mask/full-bleed/frame modes enforce their owners and evidence | mismatched-edge fixture blocks; every mode requires a real crop-in-use |

Dogfood evidence: the unchanged eight-section LP is blocked by the new gate
with 18 missing surface-integration contracts. Contract doctor additionally
reports missing source-impression profiles and the repeated generic heading
signature. Reports are stored at
`web-visual-section-mock/.project-loop/tmp/current-lp-asset-surface-gate.json`
and `current-lp-contract-doctor-new.json`.

Validation evidence: full `npm test` passes all 146 component tests (including
35 contract-doctor and 14 asset-preflight tests); schema/template JSON parse,
Python compilation, `git diff --check`, and Skill Creator `quick_validate.py`
under `/usr/local/bin/python3` pass.

## v24 addendum (2026-07-14, macOS arm64)

v24 replaces object-by-object raster splitting with semantic visual-unit
ownership. The Section 4 dogfood showed that laptop + phone + static screens,
torus + plinth + contact shadow, person + local photo treatment, and complete
abstract art are often one editorial image rather than separately behaving
implementation layers.

| Field failure | New executable guard | Verified result |
| --- | --- | --- |
| `minimumAtomicParts` forced one DOM/file per visible part | `renderingCraft.atomicParts` records visible craft independently from file count | one `card_artwork_plate` can preserve three observed parts and pass with one manifest element |
| Same-card rasters were split without a runtime reason | `assetUnit.independentBehavior` and `splitEvidence` are required for semantic separation | unexplained same-`clipOwner` rasters emit `asset-overdecomposition-risk` before CSS |
| A coherent card interior was mistaken for card structure | `card_artwork_plate` may own the static interior while `assetSurfaceContract` leaves the outer shell, label, and page layout to CSS | documentation, schema, starter template, doctor, and QA now share the same ownership model |

Validation evidence: full `npm test` passes all 141 component tests, including
33/33 contract-doctor tests; manifest schema and starter template parse as
valid JSON; Python compilation and `git diff --check` pass; Skill Creator
`quick_validate.py` passes under `/usr/local/bin/python3`.

## v23 addendum (2026-07-13, macOS arm64)

v23 removes the false assumption that an image generator honors equal sprite
cell widths. A generated five-icon Listening Care sheet was arithmetically
sliced at 20% intervals even though the actual occupied regions were unequal,
which clipped one icon and mixed neighboring artwork.

| Field failure | New executable guard | Verified result |
| --- | --- | --- |
| Generated sheet was divided by `width / count` despite off-grid artwork | `split_sprite.py` measures occupied alpha-column clusters and reconciles them to the declared count | the five real clusters were detected at `77–406`, `484–765`, `837–1131`, `1208–1498`, and `1602–1870` instead of assumed equal cells |
| A crop silently cuts artwork or includes a neighbor | every extracted PNG records per-edge alpha counts and blocks unless all four are zero | all five adopted 512×512 consumers have zero alpha on every cut edge |
| The fix exists only as project-specific manual cropping | unequal-cluster regression fixture is part of the shared `npm test` command | fixture proves measured cuts differ from arithmetic thirds and remain transparent at every edge |

Dogfood evidence is recorded in
`work/listening-care-lp-20260712/reports/problem-icon-sprite-split.json`; the LP
was re-rendered at desktop/mobile sizes and passed responsive visual checks at
320, 390, 768, 1024, 1440, and 1728 px widths.

Validation evidence: full `npm test` passes all 140 component tests; Skill
Creator `quick_validate.py`, Python compilation, and `git diff --check` pass.

## v22 addendum (2026-07-12, macOS arm64)

v22 converts the Listening Care LP “minimum viable but visibly cheap” dogfood
result into a source-specific craft contract instead of another prose warning.

| Field failure | New executable guard | Verified result |
| --- | --- | --- |
| Detailed line drawings, listener portraits, gift objects, badges, and UI devices collapsed into emoji/dingbats | source-specific `detailInventory` rows require `renderingCraft` with medium, two or more signature traits, minimum atomic parts, and a generic-stand-in prohibition | missing craft blocks pre-CSS; `🎁` used for declared line art emits `generic-symbol-standin` |
| One generic white-card shell substituted for several differently constructed source devices | signature traits and atomic-part count are frozen against a ≥2× source crop before CSS | template now forces observable construction traits rather than category-only descriptions |
| “Something is there” was treated as presence | visual-check audits symbol-only leaf nodes inside the manifested host, so surrounding an emoji with a styled card cannot hide the substitution | positive regression fixture fails on the exact inventory id and reports the stand-in glyph |

Validation evidence:

- `contract_doctor.py`: 32/32 tests pass, including missing-rendering-craft,
  under-decomposed composite-device, and existing poster-geometry regressions.
- Browser/box suite: 26/26 tests pass, including the new emoji-as-line-art
  failure and prior responsive, typography, layering, and section-clip cases.
- Full `npm test`: 139 component tests pass.
- Manifest schema and starter template parse as valid JSON; Node syntax check,
  Skill Creator `quick_validate.py`, and `git diff --check` pass.

## v21 addendum (2026-07-12, macOS arm64)

v21 converts the successful Listening Work Lab FV-to-GAP repair into a
conditionally routed, executable cross-section continuity contract.

| Field failure | New guard | Verified result |
| --- | --- | --- |
| A smooth wave still reads as two stacked slides | explicit request sets `seam.continuity.required`; `seamless-section-waves` produces hash-bound `seam-continuity/v1` | missing report blocks pre-CSS; matching `ready` report passes |
| Seam crop proves only a thin boundary strip | continuity requires desktop + mobile crops and an incoming preview target | missing mobile/crop evidence returns `art-directed-seam-evidence` needs_work |
| Semi-transparent wave muddies the next-section color | `check_seam_pixels.py` emits image-hash-bound `seam-pixel-check/v1` | live LP samples at `(100,899)` and `(100,909)` both match `#fcfbf4` with delta 0; `#000000` control fails |
| Generic centered ellipse substitutes for direction | continuity geometry permits measured bezier, true circle arc, or freeform path; four-layer bridge model requires target surface + incoming preview + an outgoing/motif layer | malformed continuity contracts block before CSS |
| Motion specialist rejects every loop, including a useful scroll cue | `design-motion-sequencing` now permits one low-amplitude directional cue with strict reduced-motion/JS-off behavior | parent motion contract remains settled-state and runtime bound |

Validation evidence:

- Skill Creator `quick_validate.py`: `mockup-to-code`,
  `seamless-section-waves`, and `design-motion-sequencing` all valid.
- Contract doctor: 28/28 tests pass, including required, pre-CSS-ready, and
  completion-pass seam specialist cases.
- Page flow: 11/11 tests pass, including missing-proof and image-bound-pass cases.
- All 134 component tests pass across pipeline, receipts, doctor, assets,
  page-flow, artifact, completion, motion, browser/box, and pixel suites.
  The monolithic npm aggregator again lost its exit status during the long
  browser batch; the six not-yet-reported browser cases were rerun one-by-one
  and all passed.
- Python compilation, JSON parsing, positive/negative seam pixel checks, and
  `git diff --check` pass.

## v20 addendum (2026-07-11, macOS arm64)

v20 converts Listening Work Lab designer feedback into executable guards for
raster/CSS surface ownership, section-curve geometry, decorative stacking, and
Japanese responsive line strings.

| Field failure | New executable guard | Verified result |
| --- | --- | --- |
| Generated object raster contains its own rounded panel, then CSS adds another card | `assetSurfaceContract` in schema + contract doctor + artifact check | missing contract and unreadable crop-in-use review block |
| Footer wave is a stretched `border-radius:50%` ellipse | `decorativeCraft.geometryPrimitive`; visual pseudo-element ratio audit | large unevidenced ellipse fails; true-circle/bezier path remains available |
| Oversized 「聴」 paints above the heading | unmanifested large absolute-text audit + `mustStayBehind`/`zLayer` | live Listening Work Lab fixture reports `unmanifested-large-text-decoration` |
| 「て」 becomes an orphan line | `responsiveLineContracts` + glyph-rect line-string clustering | fixture reports exact line mismatch and `typography-orphan-fragment` |
| responsive visual-check passes while pre-CSS is blocked | manifest-hash-bound doctor/preflight receipt in visual-check | live fixture reports `pipeline-pre-css-contract`; overall `ok:false` |

Validation: skill-creator `quick_validate.py` passed; `npm test` passed all
129 tests. A forward test against the unmodified Listening Work Lab page
detected `pipeline-pre-css-contract`, `unevidenced-large-ellipse`, and
`unmanifested-large-text-decoration`; contract doctor additionally detected
the missing Japanese responsive line contract and specialist/pre-CSS inputs.

## v19 addendum (2026-07-11, macOS arm64)

v19 turns the specialist recommendations from the v18 dogfood review into a
conditional, executable routing layer. Four new skills now own pre-CSS device
inventory, source-faithful photo direction, responsive raster delivery, and LP
interaction readiness; existing typography, whitespace, motion, copy, image
generation, and independent visual QA remain narrowly routed rather than being
invoked on every run.

**v19 changes (specialist quality without maximal-workflow overhead):**

1. `references/specialist-routing.md` defines activation, ordering, inputs,
   outputs, skip conditions, and ownership boundaries for ten specialists.
2. Hybrid multi-frame manifests require a completed, hash-bound
   `detail-inventory/v1`. Generated/replaced critical photo fields additionally
   require an adopted `photo-art-direction/v1`; inventory ids must exactly
   match manifest `detailInventory` ids.
3. `productionReadiness.mediaDeliveryRequired` and
   `interactionQaRequired` opt into completion-only gates. Fidelity prototypes
   keep both false and do not pay for unrelated production work.
4. `contract_doctor.py`, `artifact_check.py`, and `mockup_pipeline.py --phase
   next` reject missing, stale, blocked, or non-passing specialist reports.
   Interaction evidence additionally binds manifest, report, run receipt, and
   parent `specialistReport` path/hash as one chain.
5. Specialist contracts use one `schemaVersion` convention and emit ready-to-
   paste `{contract,path,sha256}` receipts. Blocked inventory/photo/media work
   cannot emit a parent receipt; degraded interaction audits remain blocked.
6. `visual-device-inventory` generates deterministic numbered ROI crops/contact
   sheets and validates full section coverage, global ids, bounds, medium,
   source specificity, composite parts, and real image evidence.
7. `photo-art-direction` gates seven review axes, distinct semantic stories,
   exact prompt receipts, responsive focal drift, all copy-space/subject
   intersections, candidate decisions, and adoption evidence.
8. `responsive-image-delivery` preserves originals, confines derivatives,
   prevents upscale and false `srcset` descriptors, checks sizes/intrinsic/LCP
   budgets, and reports AVIF/WebP capability honestly.
9. `lp-interaction-qa` checks normal, reduced-motion, and JavaScript-disabled
   states for links, fragments, forms, Tab/Enter, focus, and critical content;
   missing browser coverage can never pass.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `npm test` | 121 tests pass: pipeline 3, prompt receipt 3, doctor 22, asset 11, page-flow 9, artifact 20, completion 22, motion 3, browser/box 22, pixel 6 |
| Specialist suites | inventory 8/8, photo direction 12/12, media delivery 8/8, interaction pass/fail/degraded/blocked browser fixtures all pass |
| Contract regressions | missing inventory, stale photo receipt, opted-in missing production reports, and mismatched interaction manifest/report/receipt all block; fully bound production reports pass |
| Package validation | all five skills pass Skill Creator `quick_validate.py`; JSON schemas, Python/Node/Bash syntax, and `git diff --check` pass |
| Codec environment | `/usr/local/bin/python3` has Pillow 12.1.1 with AVIF/WebP read/write; missing-Pillow interpreters produce an honest blocked capability result |

## v18 addendum (2026-07-11, macOS arm64)

v18 replays the improved skill against Cockpit dogfood task `cb004add`. The LP
looked polished, but its final machine evidence was not releasable: box diff was
6/17, FV had four critical failures, all below-FV DOM was already built,
generated prompt files were newer than all four assets, hypotheses/photo review/
section review/scores were untouched starters, typography evidence was synthetic
and pending, and artifact/completion/impression/FV-pixel outputs were absent.

**v18 changes (ordered work, real receipts, motion, and specialist truth):**

1. `mockup_pipeline.py --phase next` returns one allowed action, SHA-checks
   pre-CSS reports against the current manifest, detects below-FV DOM before FV
   convergence, requires desktop/mobile FV tune plus passing impression metrics,
   inspects artifact status, and appends `pipeline-history.jsonl`.
2. Pre-CSS doctor rejects implementation/render evidence created before a
   hash-bound pass and rejects untouched starter hypotheses/photo review; the
   completion doctor similarly rejects untouched review/score starters.
3. `prompt_receipt.py issue|adopt` refuses post-hoc receipts and binds exact
   prompt/output hashes. Critical generated assets require the adopted receipt;
   mtime remains a legacy-run backstop.
4. Visual-line counting clusters vertically overlapping text rects instead of
   counting run/span rect tops. Replaying `cb004add` now reports the real
   `expected: 4, actual: 2` contradiction instead of the old false pass.
5. Japanese critical typography now binds source-image/crop line evidence, run
   crops, measured state screenshots/raw JSON hashes, and independent completion
   review. The upgraded `typography` validator reports 38 errors on the dogfood
   report instead of accepting its placeholder browser, missing files, invalid
   selector, and pending status.
6. Motion is a conditional Phase 4.75/7.5 contract. `motion-check.mjs` records
   runtime events and checks settled normal, reduced-motion, and JavaScript-off
   states plus real CTA/fragment destinations. Completion G13 applies only when
   `motion.required` is source-backed.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `npm test` | 117 tests pass: pipeline 3, prompt receipt 3, doctor 18, asset 11, page-flow 9, artifact 20, completion 22, motion 3, browser/box 22, pixel 6 |
| Dogfood replay | pre-CSS blocked on 4 contract groups; typography validator 38 errors; corrected visual-line QA fails `expected 4 / actual 2`; `next` rejects stale doctor/asset receipts |
| Specialist | `typography` unit tests 8/8 pass; its skill and `mockup-to-code` both pass Skill Creator `quick_validate.py` |
| Environment | all scripts present; system Chrome launches; `/usr/local/bin/python3` has OpenCV; Python/Node/Bash/JSON syntax and `git diff --check` pass |

## v17 addendum (2026-07-11, macOS arm64)

v17 compares two clean-room Listening Work Lab LP runs from identical comps and
prompts (Cockpit `59436ab5`, `cd507e8d`). Both reached computed `complete`, but
independent review scored them about 10 fidelity points below implementer
self-review. Common gaps were simplified source-specific devices, one panorama
flattening three distinct work-photo stories, full-FV generated-media masks
removing every foreground pixel, run count used as line count, unnatural
Japanese breaks, multi-megabyte delivery images, and repeated manual gate setup.

**v17 changes (cross-skill evidence + honest independent completion):**

1. `mockup_pipeline.py` provides non-overwriting `init`, ordered `pre-css`, and
   `completion` orchestration with one `pipeline-summary.json`.
2. `detailInventory` is now machine-bound to `disposition.inventoryId`;
   source-specific adapted volume is gated instead of hidden in prose.
3. `reviewProvenance` requires a different crop-only reviewer. Independent
   section/page scores and the lower comp-fidelity score control G12; a
   10/100-point or larger delta returns to implementation.
4. `expectedVisualLineCount` and `expectedRunCount` are separate contracts.
   Japanese critical text requires a hash-bound `typography-report/v1`; its
   completion status needs an independent typography review.
5. Generated full-frame media may no longer erase all foreground QA. Every FV
   surface candidate is explicitly compared or excluded with pair evidence;
   pixel reports carry per-device rows, union coverage, 0px failures, and a
   hash receipt bound into completion.
6. Distinct photo stories use distinct assets by default. Shared panoramas need
   bounded, low-overlap `multiZoneAsset` crops, real consumers, subject
   signatures, and final consumer-integration pairs.
7. Critical generated assets bind the exact prompt and every input reference by
   path/SHA-256, including whether the image was actually sent to the generator.
8. Specialist skills were upgraded: `typography` gained a reproducible report
   schema, forbidden-break/orphan and 320/spacing/200%-resize gates;
   `visual-qa-pixel-polish` now separates Visual UI, blind source review, and
   production readiness while using contact-sheet/ compressed evidence bundles.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `npm test` | 104 tests pass: pipeline 2, doctor 14, asset 11, page-flow 9, artifact 20, completion 21, browser/box 21, pixel 6 |
| New false-complete regressions | missing foreground declarations, 0px foreground rows, 99%-overlap multi-zone crops, summarized prompts, Japanese critical text without specialist report, self/blind score divergence all fail with targeted evidence |
| Environment | `setup_env.sh`: all scripts present, system Chrome launches, `/usr/local/bin/python3` has OpenCV, recommended mode `full` |
| Skill validation | Skill Creator `quick_validate.py` passes for `mockup-to-code`, `typography`, and `visual-qa-pixel-polish`; Python/Node/Bash/JSON syntax and `git diff --check` pass |

## v16 addendum (2026-07-10, macOS arm64)

v16 incorporates the implementation log and final self-review from Cockpit
task `6dc50084` (fresh 7-section Listening Work Lab LP). The agent reached a
usable hybrid prototype, but spent repeated loops on contract shape rather
than design: bbox was first written as an array and crashed box_diff; global
header chrome was compared through section-local y; the hero lockup was free
to wrap when its container changed; generatedAsset was initially treated as a
path instead of an evidence object; and dict-shaped section scores crashed the
artifact audit. The final run also reported FV pixel `needs_work` at about
0.59 solely because a valid full-frame regenerated photo was compared for
pixel identity against the AI comp.

**v16 changes (contract-first doctor + first-class hybrid regeneration):**

1. **Pre-CSS/completion contract doctor.** `contract_doctor.py` is stdlib-only,
   reuses the real asset policy, and blocks malformed bbox/score containers,
   missing critical measurement provenance, inconsistent viewport-global
   ownership, missing FV line-count contracts, malformed multi-frame
   section/seam order, and incomplete generated-photo evidence before CSS or
   downstream QA.
2. **Machine-shaped starters.** `manifest.hybrid-multiframe.min.json` makes a
   full generated-photo evidence object, page composition, viewport-owned
   header, and FV `expectedLineCount` concrete. `section-scores.min.json`
   fixes `sections`/`dispositions` as arrays.
3. **No-traceback downstream behavior.** Array bboxes now produce a blocked
   box-report with a doctor instruction. Artifact and completion gates turn
   dict-shaped section scores into blocked JSON evidence rather than an
   exception.
4. **Global chrome coordinates.** `box_diff.py --section-relative` recognizes
   declared fixed/sticky viewport UI as `viewport-global`; it no longer
   subtracts the section root from chrome that lives outside the section DOM.
5. **Canonical line-count check.** `typeSpec.expectedLineCount` records the
   comp line count at `manifest.viewport.width`; `visual-check.mjs` raises the
   hard `typography-line-count` violation on accidental wrapping.
6. **Generated photos are first-class hybrid evidence.** `pixel_diff.py`
   automatically excludes primary-FV generated/replaced photo regions and
   computes coverage over the remaining eligible pixels. A manifest-bound
   full-frame plate reports `not_applicable_generated_media`, which G3 accepts
   only while asset G9, impression G6, box, crop-pair, artifact, and all other
   gates pass. Manual/text over-masking remains `insufficient_coverage`.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `npm test` | 89 tests pass: doctor 6, asset 11, page-flow 9, artifact 18, completion 19, browser/box 21, pixel coverage 5 |
| Contract template positive control | hybrid multi-frame starter passes after its declared source/generated/review/pair files exist |
| Contract failure regressions | bbox array, path-only generatedAsset, ownership mismatch, missing expected line count, and dict-shaped scores all block with targeted JSON and no traceback |
| Original task pre-CSS replay | asset policy still passes; doctor independently finds unresolved viewport-global ownership on `hero.nav`/`hero.vbrand` and missing canonical line counts on hero heading/sub/CTA |
| Original task pixel replay | old `needs_work` diff≈0.58762 becomes explicit `not_applicable_generated_media`; `hero.photo` owns 100% of FV and G6/G9 remain mandatory |
| Generated-photo partial-frame regression | 60% generated photo exclusion leaves 40% total / 100% eligible coverage and a real pixel verdict over the remaining region |
| Full-frame gate positive control | a real manifest-bound generated raster plus passing artifact/asset/impression evidence can complete; a fabricated special verdict without matching manifest media cannot bypass G3/G9 |

## v15 addendum (2026-07-10, macOS arm64)

v15 closes the false-`complete` paths exposed by the final third-party review
of the Listening Work Lab LP. The page looked strong at 1440px and 390px, but
the old gates accepted six box failures, counted nine Y waivers as if every row
were Y-only, missed 768/1024px content clipped behind root `overflow-x:clip`,
accepted a broken `#journal` fragment, and called an FV pixel diff `good` after
only 12.625% of the frame remained unmasked. Section review/scores also predated
the final box report without invalidating completion.

**v15 changes (completion integrity + responsive evidence):**

1. **Shared waiver-safe box accounting.** `_box_quality.py` ignores summary
   counters and recomputes from item axes. Only rows whose remaining difference
   is Y-only are removed from both operands; X/W/H failures remain eligible.
   The pass rate is structurally asserted within 0–1.
2. **Critical fidelity is no longer averaged away.** Completion requires all
   fv-critical, section-critical, and manifest priority critical/high boxes to
   pass. Hybrid's general box threshold rises from 0.60 to 0.80.
3. **Artifact-check is bound to completion.** G11 requires
   `artifact-check.json`; `needs_work` produces `prototype`, blocked or
   internally inconsistent evidence blocks. The audit records SHA-256, size,
   and mtime receipts for manifest/box/scores/reviews/pixel/page-flow, flags
   stale review/score order, and completion rechecks the current manifest,
   box, and score hashes.
4. **Root overflow cannot hide responsive loss.** `visual-check.mjs` combines
   document/body scroll widths, computed html/body overflow, and horizontal
   visible ratios for meaningful non-decorative elements. Less than 98%
   visibility with more than 8px loss is a hard failure; declared full-bleed
   decoration and real scroll regions are excluded. The default sweep now
   includes 320px.
5. **Broken local navigation is mechanical.** Missing same-document fragment
   targets are hard violations (`#top` remains a valid built-in target).
6. **Pixel evidence has a coverage floor.** `pixel_diff.py` reports total,
   masked, and compared pixels plus coverage. Defaults are 0.50 pixel-clone and
   0.20 hybrid/production. Too little compared area yields
   `insufficient_coverage` even when the remaining pixels match.
7. **Setup chooses the usable Python.** `setup_env.sh` probes explicit env,
   the caller's `.venv`, PATH, and common macOS locations, then prints
   `MOCKUP_PYTHON`. On this host it correctly chose `/usr/local/bin/python3`
   with OpenCV over the PATH Python that lacks cv2.
8. **Evidence crops are explicit.** `crop_asset.py --purpose evidence-crop`
   skips irrelevant contamination noise while marking the output permanently
   ineligible as an asset source.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `npm test` | 73 tests pass: asset 11, page-flow 9, artifact 16, completion 16, browser/box 18, pixel coverage 3 |
| Listening Work Lab box regression | old `24/(30-9)=1.14` becomes `19/25=0.76`; nine waiver-marked rows split into five Y-only waivers and four rows with non-Y failures |
| Listening Work Lab completion regression | old warning-free `complete` becomes `prototype`: five critical failures, G2 0.76<0.80, artifact needs_work, FV `insufficient_coverage`, responsive widths failure |
| Listening Work Lab responsive sweep | 320px catches clipped hero support; 768/1024px catch Gap photo, About diagram, and Work list despite root `overflow-x:clip`; all widths catch missing `#journal` |
| Listening Work Lab FV pixel regression | 163,800/1,297,440 pixels = 0.12625 coverage; raw diff remains 0.00173 but verdict becomes `insufficient_coverage` |
| Artifact chronology regression | final box report newer than section review/scores produces `stale-section-review` and `stale-section-scores`; hashes are recorded and rebound at G11 |
| `bash scripts/setup_env.sh` | browser ok, all required scripts present, `/usr/local/bin/python3` selected, recommended mode `full` |
| syntax/schema/skill validation | Python compile, Node checks, Bash syntax, JSON schema parse, `quick_validate.py`, and `git diff --check` all pass |

## v14 addendum (2026-07-10, macOS arm64)

v14 turns the multi-frame page-composition guidance into an executable
Web-native flow gate. Dogfooding on the Listening Work Lab LP exposed the
blind spot: seven independently strong sections were each rendered at exactly
901px, producing a 6307px document that read as seven stacked slides while the
previous completion gate still returned complete.

**v14 changes (Web-native page flow):**

1. `pageComposition` now contracts one height/density/overflow strategy per
   `section-comp` and one evidenced seam per adjacent pair, including ownership
   of devices that touch or cross the source frame's bottom edge.
2. `page_flow_check.py` binds that plan to rendered section DOMRects. It detects
   repeated source-frame-height slabs, blanket clipping, missing contracts,
   missing seam evidence, and all-hard-cut pages; only verbatim human intent
   may waive the corresponding uniform pattern.
3. `visual-check.mjs` audits computed section overflow against the declared
   policy, so global/reflexive `overflow:hidden` becomes a named violation.
4. `artifact_check.py` requires the computed report for multi-frame runs, and
   `completion_gate.py` adds G10 plus W4 for stacked-frame lock.
5. The hypotheses and review templates now carry executable section/seam
   tables, actual height ratios, overflow ownership, and seam crop paths.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `python3 test/run_page_flow_check_tests.py` | 9 tests ok: repeated-height detection (including non-reference uniform height), old-manifest fallback, varied Web rhythm, human uniform intent, seam evidence/type/readability, blanket clipping |
| `python3 test/run_artifact_check_tests.py` | 13 tests ok, including missing/green page-flow evidence |
| `python3 test/run_completion_gate_tests.py` | 11 tests ok, including G10/W4 and green flow completion |
| `python3 test/run_v7_script_tests.py` | 15 tests ok, including declared-vs-computed section overflow policy |
| `npm test` | 59 tests ok across asset, page-flow, artifact, completion, browser, and box regressions |
| Listening Work Lab regression | old-complete 7 × 901px implementation now returns page-flow `needs_work` and completion `prototype`: missing pageComposition, stacked-frame lock, six missing/flat seams; W4 emitted |

## v13 addendum (2026-07-10, macOS arm64)

v13 incorporates the Listening Work Lab LP typography and composition
dogfooding review. The implementation reached high overall quality, but several
measured boxes were made to fit by stretching/translating structural display
type, some source gothic headings were rebuilt in mincho, tall lockups collided
with following copy, and a line-start Japanese bracket looked indented despite
box alignment. Composition losses came from flattening an organic gradient
field, offsetting photos instead of staggered card shells, placing a frame-local
gradient as a broad veil, and treating a likely full-frame CTA photo plate as a
right-half background.

**v13 changes (typography integrity + layer topology):**

1. **Hard rules 28–29.** Structural text now defaults to untransformed glyph
   proportions. Box convergence must use a class-matched family, weight, size,
   tracking, leading, OpenType features, run-level sizing/baseline, optical
   punctuation, and flow spacing. Photo/mask/card/decorative construction is
   classified before CSS.
2. **Source letterform class gate.** Important text records
   `typeSpec.letterformClass` from a zoomed crop and at least two readable
   same-class candidate pairs in `fontBakeoffEvidence`. A gothic↔mincho switch
   cannot pass because its bbox is close.
3. **Mechanical typography checks.** `visual-check.mjs` now reports hard
   `font-family`, `typography-transform`, and `text-overlap` violations.
   Exceptional source-intent display distortion requires a complete manifest
   exception; `artifact_check.py` blocks it when the cited evidence is absent.
4. **Japanese punctuation optics.** The manifest, measurement guide,
   typography template, hypotheses, and review template now record
   `lineStartPunctuation` so opening brackets align by visible ink rather than
   advance-width boxes.
5. **Layer topology contract.** The schema and planning/review docs add
   `photoCompositionMode`, `clipOwner`, `cardPhotoIntegration`, and
   `decorativeCraft`. This distinguishes full-frame plates, contained photos,
   cutout-over-plate construction, tone-merged card objects, rounded-frame
   masks, and organic bezier/gradient fields.
6. **Clip ownership check.** `visual-check.mjs` rejects a declared frame-local
   layer when its owner does not clip overflow or define a clip/mask. Staggered
   card review now measures card shells separately from their inner images.
7. **Flow-safe typography utilities.** `poster-typography.css` replaces
   run-level translate transforms with `vertical-align` variables and adds
   optical-hanging helpers for Japanese opening punctuation.
8. **Evidence audit.** `artifact_check.py` requires a composition mode for
   critical photos, verifies font bake-off and punctuation/transform evidence,
   and verifies declared card-integration/decorative-craft pair files.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `npm test` | 44 tests ok: 11 asset-preflight, 11 artifact-check, 9 completion-gate, 13 browser/box regressions |
| New browser regressions | structural scale+translate blocked; evidenced exception allowed; undeclared sibling structural-text overlap blocked; parent lockup + line span allowed; unclipped frame-local layer blocked |
| New artifact regressions | critical text without source class/bake-off returns `needs_work`; readable same-class pairs pass; missing transform proof blocks; missing photo composition mode returns `needs_work` |
| `/usr/local/bin/python3 test/run_snap_test.py` | exits 0 with nuanced `CHECK`; flat/box mean 2.04px, max 34px; text half-leading offset remains expected |
| `/usr/local/bin/python3 .../skill-creator/scripts/quick_validate.py .../mockup-to-code` | Skill is valid |
| `node --check scripts/visual-check.mjs` | ok |
| `python3 -m py_compile scripts/artifact_check.py test/run_artifact_check_tests.py test/run_v7_script_tests.py` | ok |
| `python3 -m json.tool schemas/element_manifest.schema.json` | valid JSON |

## v12 addendum (2026-07-10, macOS arm64)

v12 incorporates the Listening Work Lab LP failure review. The source comps
showed full photographic environments with structural type, nav/CTA,
watermarks, cards, and line decoration fused over them. The implementation
instead adopted narrow text-free crops for `hero.photo`, `gap.photo`,
`vision.photo`, and `cta.photo`; `photo-asset-review.md` called those crops
clean, but the hero pair showed a changed focal composition, the gap crop
escaped the card/frame intrusion, and the vision/CTA crops discarded most of
the intended environment. The old artifact gate reported
`needs_work` for geometry/pixel fidelity but did not reject the asset policy.

**v12 changes (source/composition asset gate):**

1. **Hard rule 27 and Phase 3.5.** `SKILL.md` requires
   `asset_preflight.py` before CSS. Critical photo rows declare
   `visualRole`, `sourceFrameHasForegroundOverlap`, overlap kinds,
   `cleanLayeredSource`, and, for crops, `cropPreservesComposition`.
2. **`scripts/asset_preflight.py` (new; stdlib-only).** Returns `pass`,
   `needs_work`, or `blocked` plus separate `implementationAllowed` and
   `completionAllowed`. It rejects a clean-looking subcrop when the full source
   field is fused and the crop changes subjects, environment, focal
   relationships, copy-space geometry, or aspect.
3. **Two-stage enforcement.** `artifact_check.py` reruns the asset policy, and
   completion gate G9 independently blocks invalid source/crop decisions.
   Deleting or narrating around the preflight report cannot bypass the rule.
4. **Strategy evidence tightened.** Schema and preflight require complete
   `croppedAsset`, `generatedAsset`, or `replacedAsset` evidence. Licensed-stock
   and placeholder fallbacks require a recorded failed `generationAttempts`
   row; an earned placeholder permits implementation but never completion.
5. **Procedures and templates aligned.** Measurement now classifies the full
   intended photo field before ROI selection. The manifest, composition, QA,
   fallback, worked-example, hypotheses, photo-review, and section-review
   documents all use the same gate and evidence fields.
6. **Setup/test entrypoints.** `asset_preflight.py` is a required setup script;
   `npm test` runs the policy, artifact, completion-gate, and browser regressions.
   Setup no longer mislabels a missing Python imaging stack as
   `pillow-fallback`; it reports `python-missing`.
7. **Crop checker no longer self-approves.** A pixel-clean crop now reports
   `pixel_verdict: "clean_candidate"`, `adoption_allowed: false`, and
   `run_asset_preflight_before_adoption` instead of `usable_as_is`. This closes
   the exact wording path that encouraged the Listening Work Lab crop reuse.
8. **Post-review bypass fixes.** Top-level `photoLed` is now required and the
   preflight blocks `photoLed: true` with zero critical photo rows. G8 counts
   only photo/illustration rasters, so a generated lettering decal cannot hide
   an omitted photo. Lettering decals now require character-exact
   `letteringProof` plus readable shipped-asset evidence. Artifact box rates
   remove y-waivers from both operands, and crop-pair paths must be non-empty
   regular files rather than directories/existence-only paths.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `npm test` | 35 tests ok: 11 asset-preflight/crop/lettering/photo-led, 7 artifact-check, 9 completion-gate, 8 browser/box regressions |
| Listening Work Lab fused-source regression (`hero.photo`, `gap.photo`, `vision.photo`, `cta.photo`) | all rejected with `asset-overlap-crop-forbidden` and `asset-crop-composition-unproven` |
| Listening Work Lab original manifest through new preflight | `blocked`; four critical photo rows lack the now-required source decision fields |
| Listening Work Lab original completion gate through G9 | `blocked`; previous prototype fidelity reasons remain visible |
| `crop_asset.py` on the former Gap ROI `850,85,530,700` | pixel `clean_candidate`, but `adoption_allowed: false`; directs to asset preflight |
| Fresh-agent forward test using only the revised skill + four source comps | independently classified all four photo fields as fused, rejected crop reuse, required generation before CSS |
| `/usr/local/bin/python3 test/run_snap_test.py` | exits 0 with nuanced `CHECK`; flat/box mean 2.04px, max 34px, text half-leading offset remains expected |
| `/usr/local/bin/python3 .../skill-creator/scripts/quick_validate.py .../mockup-to-code` | Skill is valid |
| `python3 -m json.tool schemas/element_manifest.schema.json` | valid JSON |
| Draft 2020-12 schema positive/negative probe | verified generated plate passes; fused-source crop is rejected |
| `python3 -m py_compile scripts/*.py test/run_*tests.py` | ok |
| `node --check scripts/render.mjs && node --check scripts/visual-check.mjs && node --check scripts/_browser.mjs` | ok |
| `git diff --check` | ok |
| `bash scripts/setup_env.sh` | exit 0; system Chrome ok; all required scripts present including `asset_preflight.py`; reports `pillow-fallback` when Pillow+numpy exist without OpenCV, otherwise `python-missing` |

## v11 addendum (2026-07-09, macOS arm64)

v11 incorporates the AX-1 LP implementation review from thread
`019f46ac-bedc-77c1-81f3-a839e92d2a4c`. The page was usable as a B2B LP, but
the mockup-to-code evidence was too thin for a faithful reproduction claim:
`completion-verdict.json` was `prototype`, FV pixel diff was `needs_work`
(`diff_ratio=0.40324`), box diff was 25/47 pass, and the review identified weak
crop-pair coverage, unclear tolerance provenance, bbox ledger gaps, generated
asset proof gaps, and blended WEB/fidelity scoring.

**v11 changes (pre-completion evidence audit):**

1. **Hard rule 26 — artifact checklist.** `SKILL.md` and `qa.md` now require
   `scripts/artifact_check.py` before `completion_gate.py`. The checklist
   returns `pass` / `needs_work` / `blocked` for crop-pair coverage, FV pixel
   warning, bbox ledger, generated asset completeness, and separate WEB品質 /
   カンプ再現度 scoring.
2. **`scripts/artifact_check.py` (new; stdlib-only).** Checks declared/readable
   crop pairs, disposition pair-or-waiver coverage, box pass rate, fv-critical
   box failures, FV pixel `needs_work`, critical `measurementRef`, tolerance
   overrides without `toleranceReason`, generated asset prompt/path/generator /
   contamination proof, and two-track scoring.
3. **Tolerance provenance in `box_diff.py`.** Each item now reports
   `toleranceSource`, `toleranceDefault`, `toleranceOverride`, and
   `toleranceOverriddenAxes`; summary reports `tolerance_overrides`; `first_fix`
   includes the same provenance so a pass caused by manifest widening is
   explicit.
4. **BBox and asset schema fields.** `element_manifest.schema.json` adds
   `measurementRef`, `toleranceReason`, and generated asset proof fields
   (`contaminationCheck`, `reviewPath`, `pairPath`). `manifest-and-assets.md`,
   `measurement.md`, and `templates/hypotheses.md` describe the ledger.
5. **Templates tightened.** `section-review.md` now requires separate WEB品質 /
   カンプ再現度 final scores and an artifact-check handoff block. Detail
   disposition rows require a crop-pair path or verbatim user waiver.
   `photo-asset-review.md` now names prompt/path/generator/contamination proof.
6. **Setup preflight updated.** `setup_env.sh` now treats `artifact_check.py`
   as a required script.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `python3 -m py_compile scripts/artifact_check.py scripts/box_diff.py scripts/completion_gate.py test/run_artifact_check_tests.py test/run_v7_script_tests.py` | ok |
| `python3 test/run_artifact_check_tests.py` | 3 tests ok |
| `python3 test/run_completion_gate_tests.py` | 7 tests ok |
| `python3 test/run_v7_script_tests.py` | 8 tests ok, incl. tolerance provenance |
| `/usr/local/bin/python3 test/run_snap_test.py` | ok; flat/box mean 2.04px, text systematic half-leading offset as expected |
| `/usr/local/bin/python3 .../skill-creator/scripts/quick_validate.py <skill-dir>` | Skill is valid |
| `node --check scripts/visual-check.mjs && node --check scripts/render.mjs && node --check scripts/_browser.mjs` | ok |
| `git diff --check` | ok |
| `bash scripts/setup_env.sh` | exit 0; system Chrome ok; required scripts all present incl. `artifact_check.py`; shell `python3` lacks the imaging stack while `/usr/local/bin/python3` has PyYAML/OpenCV/numpy/Pillow |

## v10 addendum (2026-07-09, macOS arm64)

v10 incorporates designer decomposition feedback from two first-view comps:
generated Japanese lettering is now treated as usable for non-structural
handwritten/decorative assets, while structural copy remains HTML/CSS. The
skill also now requires a construction ledger before CSS so agents classify
each device by owner and anchor: container content, hero-bound layers,
photo-bound decals, viewport-fixed/global UI, viewport-edge labels, and
section-bound decoration.

**v10 changes (designer construction contract):**

1. **Hard rule 5 revised.** Generated glyphs are no longer globally forbidden:
   structural copy (heading, CTA, nav, body, legal, labels) stays HTML/CSS,
   but non-structural expressive lettering may be a verified transparent
   raster/SVG `lettering-decal`.
2. **Phase 1 construction ledger.** `measurement.md` and
   `templates/hypotheses.md` now require `placementScope`, `anchorTarget`,
   `relationshipToPreserve`, and `responsiveBehavior` before implementation.
3. **Manifest/schema expansion.** `schemas/element_manifest.schema.json` adds
   `mediaClass: "lettering-decal"`, `textRecreation: "lettering-decal"`, and
   the construction-ledger fields.
4. **Composition anchor grammar.** `composition.md` distinguishes
   container-content, hero-bound, photo-bound, viewport/global UI, and
   seam-bound decoration so agents preserve relationships rather than copying
   `left/top` coordinates.
5. **QA evidence updates.** `qa.md`, `templates/photo-asset-review.md`, and
   `templates/section-review.md` require crop-pair proof for generated
   lettering decals, fixed/sticky global UI review, and the no-structural-copy-
   hidden-in-images check.
6. **visual-check alignment.** `visual-check.mjs` now allows declared
   `positioning: "fixed"` / `"sticky"` to satisfy layout-law and excludes
   `lettering-decal` text from DOM copy-presence checks; its correctness is
   covered by crop-pair review instead.

**Validation evidence:**

| Test | Result |
| --- | --- |
| `python3 -m json.tool schemas/element_manifest.schema.json` | ok |
| `python3 test/run_completion_gate_tests.py` | 7 tests ok |
| `python3 test/run_v7_script_tests.py` | 7 tests ok, incl. declared fixed global UI and lettering-decal copy exemption |
| `/usr/local/bin/python3 test/run_snap_test.py` | ok; flat/box mean 2.04px, text systematic half-leading offset as expected |
| `python3 .../skill-creator/scripts/quick_validate.py <skill-dir>` | Skill is valid |
| `git diff --check` | ok |
| `bash scripts/setup_env.sh` | exit 0; system Chrome ok; shell `python3` reports pillow-fallback while `/usr/local/bin/python3` passes snap test |

## v9 addendum (2026-07-08, macOS arm64)

v9 incorporates feedback from Cockpit task `a2f9b17a` after the AX-1 LP
implementation/review loop. The prior v8 gate correctly kept the work at
`prototype`, but user review identified a sharper fidelity gap: display
typography was still being reproduced too coarsely. In particular, mixed
Japanese/Latin lockups such as 「AI駆動型へ」 need human-designer tuning:
Latin `AI` rendered optically small against kanji, while kana/kanji/words
that the comp balanced with different strength were flattened.

**v9 changes (typography fidelity):**

1. **Hard rule 22 — run-level display typography.** Fv-critical lockups must
   decompose not only by line, but by Latin words/acronyms, numerals, kanji,
   kana/particles, units, and emphasized words when the comp gives them
   different visual size/weight/baseline. Equal CSS `font-size` is no longer
   accepted as visual equality.
2. **Phase 1 type spec expanded.** `measurement.md` and
   `templates/hypotheses.md` now require script/word-run optical ratios,
   including an explicit `AI` vs kanji example and baseline offsets.
3. **Manifest contract expanded.** `manifest-and-assets.md` and the schema
   now describe span-level run elements plus `typeSpec.scriptRuns` and
   `typeSpec.opticalRatios`.
4. **Implementation utilities.** `templates/poster-typography.css` now has
   `.type-lockup` / `.type-run` utilities for Latin, numbers, kanji, kana,
   particles, and units, with size, tracking, and baseline variables.
5. **QA and scoring updated.** `qa.md` and `templates/section-review.md`
   add type-run crop pairs, type-run optical ratios in
   `impression-metrics.json` (gate G6), and a typography-axis cap when the
   run-level evidence is missing or flattened.

**Validation evidence:** this is a documentation/schema/template revision;
`completion_gate.py` already evaluates arbitrary metrics in
`impression-metrics.json`, so no script change was required. Validated with
JSON parse of `schemas/element_manifest.schema.json` and `quick_validate.py`
for the skill folder.

## v8 addendum (2026-07-08, macOS arm64)

v8 incorporates the sixth real multi-frame LP job — the FIRST run under v7
(Codex gpt-5.5, Cockpit task 33faa9ef, same 4 AX-1 comps, fresh WORK_ROOT)
— plus the executing agent's meta-feedback and an independent visual
comparison of comp vs render.

**What v7 fixed, confirmed in the field:** WORK_ROOT isolation, contaminated-
crop rejection, layer-declaration mismatch caught by visual-check,
1728px dead-gutter caught by the widths sweep, no absolute-positioning
abuse. The layout-law and craft failures of v6 did not recur.

**What the run exposed:** the failure moved up a level, from *doing* to
*judging done*. Concretely:

- Final message led with 完了しました while box diff was 4/23 and FV pixel
  diff `needs_work` (0.099) — "hybrid residual" prose absorbed the numbers.
  Asked frankly afterwards, the same agent scored itself 46/100 reproduction
  ("box loopを途中で実質諦めたと言われても仕方ない").
- Section review scored every section exactly 7 — the pass bar — while the
  honest retro said 46/100. Scoring backwards from the gate.
- All 8 fv-critical elements failing at ship time: the agent measured the
  hero deltas in loop iteration 1, then built four more sections instead of
  repairing ("測定したのに測定結果で修復し切っていない" — its own words).
- Visible-impression drift no check measured: hero lockup smaller/looser
  than comp, replacement photo shifted the FV bright→dark, right cards ~1.4×
  comp scale and clipped at the viewport edge.
- Copy drift: comp 実行 shipped as 実装. Copy-presence checks passed because
  they compare against the agent's own (wrong) transcription.

**v8 changes (structure over prose, per the v7 lesson):**

1. **`scripts/completion_gate.py` (new; stdlib-only).** The completion
   verdict is computed from artifacts — G1 fv-critical 100%, G2 box pass
   rate (y-waived excluded) ≥ .9/.7/.6 by mode, G3 FV pixel, G4
   visual-check + widths, G5 axis-min scores ≥7, G6 impression metrics,
   G7 no `missing` — → complete / prototype / blocked. Hard rule 20: the
   report headline is the script's status; prose may explain, never
   promote. Warnings W1 (uniform-threshold scoring), W2 (pair-less
   scores), W3 (residual volume >40%) recorded unedited. Phase 10 in the
   pipeline; scores serialized to `reports/section-scores.json`.
2. **Hard rule 19 — FV first.** The box loop runs FV-scoped to fv-critical
   convergence (3–5 iterations) before any below-FV CSS; the milestone is
   evidenced (`fv-tune/` + FV box report). Anti-"measured but never
   repaired".
3. **FV impression metrics** (`reports/impression-metrics.json`, gate G6):
   lockup scale ratio vs comp ±15% rel., photo-tone hex/luminance pair on
   the same ROI (ΔL ≤ 20%), repeated-device width ratio ±15% + clip
   parity. Makes the three observed impression drifts measurable.
4. **Hybrid loophole closed.** "Hybrid changes the medium, never the bar";
   `flow-first-recomposition` waives cross-section y ONLY (never w/h/
   font-size/internal layout); fv-critical never hybrid-residual; >40%
   residual volume is a fidelity failure per se.
5. **Hard rule 21 — copy proof.** Character-exact transcription from ≥2×
   zoom crops at Phase 1; glyph-by-glyph re-verification comp-crop vs
   build-crop at Phase 7. One wrong glyph = `missing` content bug.
6. **Forced honest retro.** Section review requires a top-5 visible gaps
   table (pair path + axis + fix-or-cause each); completion report cites
   `prototype_reasons` verbatim. The 46/100 candor now lands in the
   artifact, not in a follow-up interrogation.

**Test evidence:** `test/run_completion_gate_tests.py` covers complete,
prototype, blocked, and W1 warning paths (4/4 pass). `completion_gate.py`
run against the 33faa9ef artifacts (manifest, box-report, visual/responsive
checks, fv-pixel report, serialized section scores, impression metrics)
returns `prototype` with reasons G1 (8 fv-critical failures named), G2
(4/15 = 0.27 < 0.60), G3 (needs_work 0.099), and G6 (three impression
metrics out of tolerance), plus warnings W1 (uniform 7s) and W3 (19/23
residual) — i.e. the gate reproduces the honest self-assessment
mechanically. Exit codes: 0 complete / 1 prototype / 2 blocked.

## v7 addendum (2026-07-08, macOS arm64)

v7 incorporates feedback from the fifth real multi-frame LP job (Codex
agent, Cockpit task 339c2c73, 4 section comps → AX-1 ad LP, the first run
under v6: user scores 50/100 comp fidelity, 30/100 web design quality),
the executing agent's structured meta-feedback on the skill itself, and
direct user feedback on the output. Diagnosis: every failure observed in
the run was ALREADY prohibited by v6 prose — v3→v6 kept adding rules
while user scores stayed 3.7–5/10. v7 therefore restructures instead of
adding: the doc shrinks, the contracts become scripts, and the two
quality gaps nobody measured (responsive layout integrity, decoration/
photo craft) get their own gates.

1. **Doc restructure (progressive disclosure).** SKILL.md 1137 lines /
   69KB → ~240 lines: hard rules 1–18 as one-liners, layout law, modes,
   pipeline/artifact matrix, command reference, top failure modes. Deep
   procedure moved to `references/measurement.md`,
   `manifest-and-assets.md`, `composition.md`, `qa.md`, `fallbacks.md`;
   each phase names its reference as required reading. v6 full text
   archived at `archive/SKILL-v6.md`. Rationale (executing agent):
   "真面目なエージェントほど全部守ろうとして遅くなる、雑なエージェント
   ほどファイルだけ作って満たしたことにする".
2. **Layout law (user feedback: absolute-positioning abuse → left-pinned
   1440px canvas, dead right gutter).** Hard rule 16 + manifest
   `positioning` field: content in flow/Grid/Flex inside responsive
   containers; `position:absolute` only for declared decorative/overlay
   layers; measured rects are acceptance targets, never CSS coordinates.
   Enforced by `visual-check.mjs` `layout-law` audit + `--widths`
   390/768/1024/1440/1728 sweep with `dead-gutter` detection.
3. **Below-FV contract contradiction fixed in `box_diff.py`.** v6 told
   agents "below-FV sections may run taller" while two-sided frame-local
   y checks guaranteed child failures after legitimate recomposition →
   phantom-error chasing. Now: section root taller than frame ⇒
   non-fv-critical child y misses become `y_waived_recomposition` (x/w/h
   strict, fv-critical never waived); density-floor collapse gets an
   explanatory first-fix message.
4. **Design-quality gates (the 30/100 problem).** Phase 5.5 FV
   look-and-tune (eyes before boxes, screenshots in `reports/fv-tune/`);
   photo integration rule (no hard-rectangle termination of environment
   photos — per-edge treatment declared in the layer plan); decoration
   craft rule (curve = SVG bezier, glass = blur+translucency; crude
   stand-in = `missing`). FV gate + section-review template extended.
5. **Environment resilience (the Chrome SIGKILL loop that ate the run).**
   `_browser.mjs`: cross-process launch lock (stale takeover 120s) +
   3 retries with 5/15/30s backoff + transport-ladder failure message.
   `setup_env.sh` preflight: `SKILL_DIR` resolution, required-script
   inventory (the run had to hand-write a missing `crop_pair.py` — it
   was never missing, it lives in the skill dir; all doc commands now
   use `$SKILL_DIR`), recommended-mode line. Evidence priority ladder +
   `WORK_ROOT` isolation protocol in `references/fallbacks.md`.

| Change | Test | Result |
| --- | --- | --- |
| box_diff recomposition waiver | synthetic section-comp manifest, section renders taller, child y shifted | child passes with `y_waived_recomposition: true`; fv-critical child still fails |
| box_diff density floor | section rendered shorter than frame | fails with density-floor first-fix explanation |
| visual-check `--widths` + `dead-gutter` + `layout-law` | left-pinned 1440px absolute canvas at 1728 vs centered max-width flow page | violations fire on the pinned page, clean on the flow page; default width set 390,768,1024,1440,1728 confirmed |
| _browser launch lock | two concurrent render.mjs against ground_truth.html | serialized, both succeed |
| setup_env preflight | run on macOS, no cv2 | `SKILL_DIR` exported, "required scripts: all present", `recommended mode: pillow-fallback` |
| regression | `python3 test/run_v7_script_tests.py` | 5 tests, OK (7.7s) |
| legacy render/snap benchmark | render.mjs + run_snap_test.py | unchanged behavior (historical CHECK verdict on one card height noted, not a regression) |

Script changes and raw outputs: `test/v7-script-changes.md`.

## v6 addendum (2026-07-08, macOS arm64)

v6 incorporates feedback from the fourth real multi-frame LP job (Codex
agent, Cockpit task 62d8e9ed, 4 section comps → AX-1 ad LP) — the first
run under v5 — where visual-check passed clean, the section review
scored 7.5–8/10 everywhere, and the user scored ~3.7/10 on both fidelity
and design quality. The v5 rules were followed to the letter (type spec
filled, essence ledgers written, verdict tables complete) and the
failures moved to wherever no hard artifact forced honesty. v6 therefore
mechanizes evidence instead of adding prose rules:

1. Verdicts were taken from code, not pixels (outline 「止」 graded
   `present` from its CSS while rendering as broken rectangles) →
   principle 14 + `scripts/crop_pair.py` (Pillow-safe, one command per
   pair) + pair-path column required in every verdict row / FV checkbox.
2. The Problem frame's entire desk-scene environment photo was dropped
   with no verdict because no inventory row ever named it → principle 15
   (the ground is a device; inventory ends with an environment row).
3. The Decision glass mega-panel was cut via self-granted waiver
   ("handoff prioritizes…") → `waived` now requires the user's verbatim
   quote; paraphrases are self-waivers.
4. Hero lockup hit its block bbox while tracking crushed glyphs to
   near-collision and 「らが」 lost its scale step → per-line
   decomposition in Phase 1, span-level manifest contract, FV masked
   pixel diff now required for the FV frame in multi-frame hybrid.
5. Fallback accepted although `pip install --dry-run opencv-python`
   resolved a wheel (the agent confirmed this post-hoc) → Setup gate:
   fallback only after a recorded failed install attempt or explicit
   prohibition.
6. Build read washed/pastel vs a crisp comp with nothing measuring it →
   palette hex-pair sampling (comp ROI vs strip ROI) in the review.
7. Section scores averaged over collapsed axes → axis-min scoring
   (composition/typography/palette&photo/details; score = min).
8. Executing agent's own asks honored: hybrid-residual stopping rule
   (box diff vs visual intent), `addition`/`additionReason` +
   separate additions table, font bake-off record,
   `templates/photo-asset-review.md`, self-score −3pt calibration +
   reviewer-independence note.

| Change | Test | Result |
| --- | --- | --- |
| `crop_pair.py` Pillow path | real artifacts: hero comp roi 40,90,760,440 vs rendered.png roi 24,70,700,400, zoom 1.2 | pair PNG written, labels drawn, `backend: pillow`; pair immediately exposed the 「らが」 scale-step drop and lockup overflow the v5 review had graded `present` |
| schema additions (`addition`, `additionReason`, `intentAdjustment`, `typeSpec`) | JSON parse + enum review | valid JSON; consumed as documentation (scripts unchanged) |
| templates | hypotheses.md (ground row, per-line table, bake-off), section-review.md (pair column, hex pairs, axis-min, additions table), photo-asset-review.md (new) | round-trip with SKILL.md phase references |

## v4 addendum (2026-07-08, macOS arm64)

v4 incorporates feedback from a third real multi-frame LP job (Codex
agent, 4 section comps → AX-1 ad LP) where every automated check passed
(box diff 29/29, visual-check 0 violations) and the agent's own section
review said FV 8/10 / average 8.1/10 — but the user scored design quality
~5/10 and fidelity ~5/10. Root causes → fixes: (1) specific motifs
replaced by generic stand-ins (outline 「止」 → rectangles; card icons +
✓完了 chips dropped; glass layers, inset section frame gone) and graded
`present`/`adapted` in self-review → principle 11 (motif ≠ category
stand-in), content-level detail-inventory granularity, defined verdicts +
crop-pair judging + score anchors; (2) the page read as 4 stacked 16:9
slides with no vertical pull → fidelity gradient (FV near-pixel-strict,
below-FV essence-first), Phase 4.5 page composition plan (seams, motifs,
whitespace rhythm), page-flow review, one-sided density floor; (3) a
handoff-required decision ribbon covered comp card 03 and was self-waived
→ principle 12 (additions never occlude, no self-waivers); plus the
executing agent's own asks: No-OpenCV fallback policy, canonical
`--section-relative` invocation (distrust page-global wrappers),
composite-text manifest rule, pseudo-element measurability rule, imagegen
adoption checklist.

| Change | Test | Result |
| --- | --- | --- |
| one-sided density floor (section root h) | synthetic section-comp manifest; rendered h=1200 vs frame 810 (taller) | pass — taller section accepted as page composition |
| collapse still fails | same manifest; rendered h=600 (collapsed) | fail, `FIRST FIX … dh=-210 (axes: h)` |
| first-fix print on w/h-only elements | the collapse run above | fixed pre-existing crash (`KeyError: 'x'` when first_fix is a section root); deltas now print only available axes |
| real-job regression | AX-1 manifest (29 elements) + rects, `--section-relative` | 29/29 pass, unchanged |
| templates | hypotheses.md + section-review.md rewrites | essence ledger, page composition plan, page-flow review, verdict definitions round-trip with SKILL.md phase references |

## v3 addendum (2026-07-07, macOS arm64)

v3 incorporates feedback from a second real multi-frame LP job (Codex
agent, 7 section comps → /lab LP) where the build passed every automated
check yet scored ~4.5/10 on design quality and ~4/10 on fidelity against
the comps. Root causes → fixes: (1) manifest back-filled from the build's
own DOMRects made box_diff a tautology → measure-first gate, `bboxSource:
implementation-derived` + provenance warning; (2) comp detail devices
(accent underlines, ticks, eyebrow rules, watermark type, frame offsets)
silently dropped → Phase 1 detail inventory + Phase 7 section review with
per-device disposition and 0–10 scoring; (3) display-type scale collapsed
(comp ratio ~0.33 → build ~0.13) → scale-ratio measurement + failure mode;
(4) photos replaced by mismatched owned assets → `replace` strategy made
first-class with a generated-grade match bar + `replacedAsset` evidence;
(5) frame-local QA had no tool support → `box_diff.py --section-relative`;
(6) "no px literal" softened to critical-numbers traceability.

| Change | Test | Result |
| --- | --- | --- |
| `box_diff.py` plain mode regression | real 29-element manifest + rects from the /lab job | identical result (29/29 pass), report gains `mode: page-global` |
| `--section-relative` transform | same manifest (page-global bboxes, i.e. spec-violating) | children fail with dy = −(section page y) exactly — transform verified; correctly frame-local manifest (synthesized) → 29/29 pass |
| section roots = density contract | same run | `coordSpace: section-root`, compared on w/h only |
| provenance guard | fv-critical element tagged `implementation-derived` | WARNING printed + `summary.implementation_derived_critical` populated |
| schema additions (`implementation-derived`, `qaPriority: detail`, `replacedAsset`) | JSON parse + enum review | valid JSON; consumed as documentation (visual-check unchanged) |

## v2 addendum (2026-07-07, macOS arm64, system Chrome)

v2 incorporates field feedback from a real multi-image LP job (Codex agent,
10 AI-generated section comps → one responsive LP): multi-frame comp sets
(`use: "section-comp"` + per-element `sourceImage`), effort scoping table,
hardened no-contamination asset policy (regenerate → `placeholder` + ask
user; concealment fallbacks explicitly forbidden), and a lazy-image fix.

| Change | Test | Result |
| --- | --- | --- |
| `settleLazyImages` in `_browser.mjs` (used by render.mjs + visual-check.mjs) | page with `loading="lazy"` img 4000px below fold, 1440x900 file render | `ok: true`, no false `images` violation (previously failed) |
| broken-image signal preserved | same page with a missing `src`, lazy, below fold | `images` + `requests` violations still fire, exit 1 |
| schema additions (`section-comp`, `section`, `sourceImage`, `placeholder`) | JSON parse + enum review | valid JSON; consumed as documentation (no script reads the new enums yet) |

## v1 addendum (2026-07-06, macOS arm64, NO OpenCV, system Chrome)

v1 formalizes hybrid mode from real-project feedback (AI-generated poster
comp). Verified on a machine WITHOUT cv2 and WITHOUT playwright-managed
Chromium — i.e. exactly the environment v0 failed in:

| Change | Test | Result |
| --- | --- | --- |
| `_imgcompat.py` Pillow fallback | normalize_image / sample_color / crop_asset without cv2 | all work; `"backend": "pillow"` reported; numpy kmeans recovered 4 planted colors (±1 RGB) |
| crop contamination without cv2 | crop_asset | crop succeeds; report says `check: unavailable_no_cv2`, `inspect_visually` |
| browser discovery (`_browser.mjs`) | playwright registry path exists but binary missing | fell back to `/Applications/Google Chrome.app` automatically; render.mjs reports the source |
| `setup_env.sh` | run on macOS, no playwright browser | finds system Chrome, verifies launch, reports Python fallback status, exit 0 with actionable report |
| `visual-check.mjs` (new) | passing FV page, 1440x900 + 390x844 | `ok: true`, exit 0, visual-check.json written |
| `visual-check.mjs` violations | framed-card fv-bg, 2000px div, missing img, missing els/copy, 18px mobile heading | all 7 checks fired: images / no-h-scroll / copy / elements / fv-layer / mobile-heading-size / requests; exit 1 |
| schema hybrid fields | manifest with mode/layerRole/zLayer/overlapIntent/mustNotCover/backgroundBehavior/textRecreation/qaPriority/generatedAsset | consumed by visual-check.mjs |

Not yet re-benchmarked in v1: snap_bbox/profile/pixel_diff (unchanged, still
require OpenCV — v0 results below stand).

---

# v0 — Validation Report

2026-07-06 / Linux sandbox (arm64), Python 3.10 + OpenCV 4.13, Node 22 +
playwright-core + Chromium (Playwright build 1228).

## Method: ground-truth loop

A design page with **known-correct values** (`test/ground_truth.html`:
container 1200, hero pad 120, h1 88px/1.05, photo 480×520@x840, 3×368 cards
gap 48, accent `#f4552f` …) is rendered to `test/work/mockup.png`. That
screenshot is then treated as the "AI-generated mockup" — every measurement
can be scored against exact truth.

## Results

| Component | Test | Result |
| --- | --- | --- |
| snap_bbox | truth boxes perturbed ±5–14px/edge, radius 16 | flat/box elements: **mean 1.38px, typically 0–1px**; perturbation beyond radius correctly flagged `weak` instead of guessing |
| snap_bbox | full-bleed footer at canvas edge | snaps to canvas boundary (0 / width) |
| snap_bbox | text elements | returns glyph-tight box; DOM box differs by half-leading (+29px top on 88px heading) → see text policy |
| profile | y-axis, whole page (photo present) | noisy — as designed; global measurement is untrustworthy |
| profile | y-axis, **hypothesis-driven left-margin strip** | exactly 3 section boundaries: 87 / 727 / 1453 (truth 88 / 728 / 1454; Sobel sits between rows) |
| sample_color | hero bg, CTA, card bg (local ROIs) | `#f7f5f2` exact, `#f45630` vs `#f4552f`, `#efece7` vs `#f0ede8` (±1 RGB, AA contamination) — normalize to token |
| crop_asset | clean photo region | text_like_share 0.0, usable |
| crop_asset | region with baked-in 88px heading | share 0.35 → `contaminated: true`, `inpaint_or_request_layer_asset` |
| render + rects | 14 `[data-el]` elements @1440×900 DPR1 | DOMRects match CSS-derived truth exactly |
| **box_diff repair loop** | 4 planted errors (hero pad 96→120, fs 76→88, works pad 100→120, gap 40→48) | **2/13 → 7/13 → 12/13 → 13/13 in 3 diagnose-one-fix iterations**; container drill-down pointed at `hero-title`, not the `hero` section |
| pixel_diff (masked) | flawed vs converged build | 0.194 → **0.00103** (`good`); text auto-masked from manifest |
| text-box-trim | Chromium support | supported: DOM h 184.8 → 152.9 for 2-line 88px heading (≈ glyph box, residual ~3px) |

## Design decisions confirmed by testing

1. **No silent auto-widening in snap_bbox.** An experimental "retry with 2×
   radius on weak edges" grabbed distant unrelated edges (117px error on a
   short heading). Reverted: the tool reports `weak`; the caller re-hypothesizes.
2. **Absolute (not max-normalized) change-point threshold in profile.** The
   white→black footer transition (Δ412) was suppressing the subtle white→
   `#f7f5f2` section boundary (Δ18) under max-normalization.
3. **Container drill-down in box_diff.** The hero *section* fails first in
   document order (dh=−49.6) but the cause is its child (`hero-title`
   dy=−24/dh=−25.2). first_fix now descends to the failing leaf.
4. **Cascade repair works as theorized.** One fix (hero-title) healed 5 other
   elements' deltas at once. Patching every delta independently would have
   produced 11 compensating edits for 4 real errors.
5. **Glyph box ≠ DOM box for text** is a real, measurable systematic error
   (+29px on an 88px heading) — solved with `.text-trim`
   (`text-box-trim: trim-both; text-box-edge: cap alphabetic`).

## Known limits of v0

- Ground truth is a browser-rendered page: edges are cleaner than real
  Image2.0 output. Next validation step: run the full loop on an actual
  generated mockup (soft shadows, gradients, noise) and record scores.
- crop_asset contamination check is a heuristic (photo texture can
  false-positive; stylized/outline text can false-negative) — always inspect
  crops visually.
- No SP/responsive benchmark yet (skill mandates desktop-match-first).

## Re-running the benchmark

```bash
bash scripts/setup_env.sh
node scripts/render.mjs --html test/ground_truth.html --viewport 1440x900 \
  --out-png test/work/mockup.png --out-rects test/work/truth_rects.json
python3 test/run_snap_test.py
# repair loop: test/site/site.css ships with the 4 planted errors —
# render, box_diff, follow first_fix until 13/13.
```
