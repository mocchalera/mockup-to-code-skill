# Phase 1 hypotheses — <project>

<!--
Required in hybrid mode. Fill this BEFORE any implementation (Phase 5);
the Phase 7 section review (templates/section-review.md) checks the build
against this file. One block per section (per frame in a multi-frame set).

Detail-inventory hunting: zoom into each frame and sweep corners,
under-headings, card edges, photo edges. A device you never listed here
is a device you will silently drop.

Granularity rules (principle 11):
- Record the CONTENT, not the category: "outline kanji 「止」, ~560px,
  upper-left, cropped by frame edge" — not "oversized outline glyph".
  Write actual icon subjects, chip texts, numbers.
- Open up composite devices: a card/panel gets one row per internal part
  that carries design (icon, label, status chip, connector, rule). One
  row saying "workflow cards" hides three drops.
- Account for the ground (principle 15): the LAST row per frame is the
  section's environment itself (scene photo / glass panel / colored
  field / gradient), with its mediaClass. Sweep once more: "what carries
  the remaining frame area?" — unlisted ground is how a whole desk-scene
  photo disappears with no verdict.
-->

## Manifest-wide media declaration

- **photoLed**: true | false
- **Evidence**: <which authoritative frames contain photo/illustration, or why none do>
- **Required critical photo rows when true**: <element ids; never leave empty>

## <NN>. <section name>

- **Frame**: `work/references/<NN>-<name>.png` → `data-el: <section-el>` (frame H: <H>px)
- **Role**: hero / problem / value-path / about / examples / vision / cta / footer
- **Design core** (the one thing that must not be compromised):
- **Display-type scale**: tallest glyph block ≈ <h>px of <H>px frame → **ratio <0.NN>**
- **Layout hypothesis**: columns, photo placement & treatment (full-bleed /
  framed / offset), container, notable overlaps
- **Palette / mood of photos**: subject, warmth, lighting (the bar any
  `replace`/`generated` asset must meet)

### Construction ledger (ownership, anchors, responsive behavior)

<!-- Decide this BEFORE CSS. A bbox says where the device is at 1440; this
table says what it belongs to and which relationship must survive at every
width. Use placementScope values like container-content, hero-bound,
photo-bound, viewport-fixed, viewport-edge, section-bound-decoration. -->

| device | placementScope | render medium | layer owner | anchor target | relationship to preserve | responsive behavior | manifest fields |
| --- | --- | --- | --- | --- | --- | --- | --- |
| e.g. fixed nav | viewport-fixed | HTML nav | global header | viewport top/right | reads as site chrome, not hero content | stays fixed desktop; compact top bar on SP | `positioning: fixed`, `layerRole: header-nav` |
| e.g. vertical logo/title | viewport-edge | HTML vertical text/logo | global chrome | viewport left | remains a persistent identity mark | releases to horizontal mark on SP | `positioning: fixed`, `layerRole: vertical-label` |
| e.g. hero photo | hero-bound | generated clean photo plate | hero | hero section | left copy space empty; faces/key objects not covered | object-position shifts by breakpoint | `mediaClass: photo`, `backgroundBehavior: full-bleed` |
| e.g. handwritten bubble | photo-bound | generated transparent lettering decal | hero/photo | subject face/shoulder or copy-space edge | distance/tilt vs subject preserved; never covers face | shrink/re-anchor with photo crop | `mediaClass: lettering-decal`, `mustNotCover` |
| e.g. wave divider | section-bound-decoration | SVG path | seam | hero bottom / next section top | seam hand-off preserved | path scales horizontally | `mediaClass: decorative-geometry` |

### Layer topology ledger (photos, masks, cards, decorative fields)

<!-- Freeze how the visible result is assembled before writing CSS. A visual
on the right half of the comp may still be a full-frame plate hidden by a
left mask. A gradient inside a rounded frame belongs to that frame, not the
page. For staggered cards, record SHELL offsets separately from photo crops. -->

| visual/device | photoCompositionMode / field type | clipOwner | shell geometry / stagger | card-photo integration / edge treatment | medium | source evidence pair |
| --- | --- | --- | --- | --- | --- | --- |
| e.g. final CTA portrait | full-frame-plate | cta frame | — | left copy mask over full plate | generated raster + CSS mask | crops/cta-topology-pair.png |
| e.g. work examples | object-detail-tone-merged | each card shell | card 2 +36px y; card 3 +72px y | sampled card/photo background + soft masked edge | transparent/clean raster + HTML card | crops/work-card-stack-pair.png |
| e.g. blue/green sweep | bezier-gradient-field | value section | — | — | SVG/CSS gradient or generated clean raster | crops/value-field-pair.png |

### Type spec (per display-text block — decompose BEFORE choosing fonts)

<!-- The comp's typography is designed; a flat single-size/one-family
rebuild is a drop. In-line scale steps: kana/particles smaller than
kanji (「らが」≈0.6×), unit suffixes smaller than numbers (55,000円),
Latin acronyms/numerals optically corrected against kanji (AI may need
1.08–1.18× to LOOK the same height).
Freeze the source's letterform class (gothic/mincho/rounded/display/etc.)
from a zoomed crop BEFORE candidate selection. Font candidates stay inside
that class and are judged against the crop with a one-line rationale;
structural display type never ships on a system-ui fallback.
Structural text defaults to `transform:none`: do not use scaleX/scaleY/skew/
rotate/translate to buy a bbox pass. Repair with family, weight, size,
tracking, leading, features, per-run size/vertical-align, and flow spacing.
An exception requires visible source intent plus manifest evidence. Record
line-start opening punctuation optical hanging when its ink edge would look
indented despite a matching DOM x-position.
Non-structural handwritten/speech-bubble lettering belongs in the asset plan
as `mediaClass: lettering-decal`, not in this table unless you rebuild it as
DOM text. -->

| block | source letterform class · observed traits · weight | in-line scale steps | per-word accents (color/marker/underline → which words) | numerals/dates | tracking/leading | transform policy | line-start punctuation | font pick + rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| e.g. hero heading | gothic · low contrast, square counters, flat terminals · 900 | 「らが」≈0.6× of kanji | lime underline → 「1DAY」 | — | -0.02em / 1.05 | none | `「`: hanging-punctuation + measured fallback | Noto Sans JP 900 — same-class counters/terminals match |
| e.g. decision dates | mincho · high contrast, triangular uroko · 600 | Thu ≈0.45× of date | — | serif lining figures | 0 / 1.1 | none | none-needed | Shippori Mincho B1 — high-contrast strokes match |

**Per-line decomposition (fv-critical lockups)** — each rendered line
becomes a span-level manifest element with a comp-measured bbox; this is
what lets box diff see crushed tracking / flattened scale steps:

| line | data-el | comp bbox (frame-local) | notes (scale step / accent inside the line) |
| --- | --- | --- | --- |
| e.g. 「社長自らが」 | hero-title-line1 | 64,176,690,150 | 「らが」 span ≈0.6× |

**Script/word-run decomposition (fv-critical lockups)** — every run with its
own optical size, baseline, family, weight, or accent becomes a span-level
manifest element. Measure visible glyph boxes, not nominal font-size:

| run | data-el | class (latin/number/kanji/kana/particle/unit/accent) | comp bbox | optical ratio vs anchor | baseline offset | implementation note |
| --- | --- | --- | --- | --- | --- | --- |
| e.g. `AI` in 「AI駆動型へ」 | hero-title-ai | latin acronym | 66,310,150,94 | 1.10× vs `hero-title-kanji` | -0.02em | use `.type-run.type-latin` with `--run-size: 1.12`; verify crop |
| e.g. 「駆動型」 | hero-title-kanji | kanji anchor | 220,306,340,96 | 1.00 anchor | 0 | anchor run |
| e.g. 「へ」 | hero-title-particle | particle/kana | 570,330,54,62 | 0.65× vs anchor | 0.05em | smaller particle, not same-size |

**Font bake-off (JP display roles — required in hybrid):** render the
real copy in 2–3 candidates, crop-pair each vs the comp glyphs, record:

| candidate | pair (`work/reports/crops/…`) | verdict / known residual |
| --- | --- | --- |
| e.g. Noto Sans JP 900 | crops/font-noto-pair.png | pick — counters match; 型 slightly narrower than comp |
| e.g. M PLUS 2 800 | crops/font-mplus-pair.png | reject — terminals too round |

### Bbox measurement ledger (FV + section-critical)

<!-- Every manifest bbox for qaPriority=fv-critical or section-critical must
have a matching `measurementRef`. This table is the human-readable ledger.
If a bbox changes later, add a new row with the comp-side measurement that
justifies the change. "Matched DOMRect" is not a measurement source. -->

| element id | data-el | source frame/artifact | ROI / command | accepted bbox | confidence | revision reason / manifest `measurementRef` |
| --- | --- | --- | --- | --- | --- | --- |
| e.g. hero.title.line1 | hero-title-line1 | work/mockups/01-hero.png | `snap_bbox.py --bbox 64,176,690,150 --radius 24` | 66,178,684,146 | strong | `measurementRef.sourceArtifact=reports/measurements/hero-title-line1.json` |
| e.g. hero.photo | hero-photo | work/mockups/01-hero.png | full-frame visual/photo ROI | 0,0,1440,810 | normalized | background plate region, not DOM-derived |

### Essence ledger (multi-frame only)

<!-- 3–5 bullets: what MUST survive translation to the scrolling page —
the frame's core statement, its 1–2 signature devices, its palette/mood.
Then name the frame artifacts to TRANSLATE, not copy. -->

- Must survive: …
- Must survive: …
- Must survive: …
- Frame artifacts to translate (not copy): 16:9 letterbox height? slide
  full-bleed edges? per-frame background reset? → …

### Detail inventory

<!-- For repeated/staggered cards, inventory each card SHELL's x/y offset,
not only its inner image crop. For masks/gradients, name the rounded clip
owner. For organic fields and conceptual diagrams, inventory path/node/
gradient complexity so a flat band or sparse icon cannot pass as present. -->

| # | device (specific content) | where | placementScope / anchor | plan (css/svg/html/generated asset) | qaPriority |
| --- | --- | --- | --- | --- | --- |
| 1 | e.g. coral hand-drawn underline under 「体験」 | heading | container-content / target word | inline SVG stroke | detail |
| 2 | e.g. eyebrow label "VOICE / ENTRY" + cyan rule, letterspaced | above heading | container-content / heading block | flex + borders | detail |
| 3 | e.g. workflow card 1: document icon + 「資料要約」 + AI chip + ✓完了 status | upper right | container-content / card grid | HTML card (icon svg, chip, status row) | detail |
| 4 | e.g. handwritten bubble 「聴くから、つながる。」 | lower photo edge | photo-bound / subject shoulder | generated transparent lettering decal | detail |
| 5 | e.g. oversized outline kanji 「止」 cropped by frame top | background upper-left | hero-bound / section edge | poster-typography outline text | detail |
| … | (last row, always) e.g. environment: top-down white desk scene photo — tablet, hand, coffee, notebook — content sits IN it (mediaClass: photo) | whole frame ground | hero-bound / section | generated raster background layer | section-critical |

### Full-field photo source gate (before asset plan or cropping)

<!-- Judge the whole photographic field the comp intends, not only a clean
candidate ROI. A crop that removes fused text/UI by deleting most of the room,
people, or focal relationships is NOT a clean plate. The manifest copies these
fields and asset_preflight.py runs before CSS. -->

| visual | visualRole | full intended photo field / bbox | foreground overlap? | overlap kinds | separate clean layered source? | would crop preserve subjects·environment·focal·copy-space·aspect? | required strategy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| e.g. hero room | background-environment | whole hero room, 0,0,1440,810 | yes | heading, nav, CTA, watermark | no | no — clean right crop loses half room and copy-space geometry | generated clean full plate |
| e.g. contained interview photo | contained-photo | framed photo ROI, 850,85,530,700 | no | — | no | yes | crop-asset + croppedAsset proof |

### Asset plan

<!-- mediaClass drives the strategy (principle 13): photo/illustration →
layered / replace(stock) / crop / generated / placeholder — NEVER
svg/css; lettering-decal → generated/crop/replace transparent asset or
hand-traced SVG, only for non-structural expressive text; icon → icon set
(record set:name); ui-mock → HTML/CSS rebuild; decorative-geometry → css/svg. -->

| visual | mediaClass | structural copy? | strategy | source/prompt/icon set | anchor target | relationship to preserve | responsive behavior | manifest evidence / proof needed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| e.g. hero room photo | photo | no | generated | prompt: bright listening lab, left copy space, green cardigan… | hero section | faces clear, left copy space empty | object-position adjusts | `sourceFrameHasForegroundOverlap: true`; generatedAsset path + clean check + review/pair |
| e.g. handwritten bubble | lettering-decal | no | generated | prompt exact text, teal hand lettering, transparent bg | hero photo / subject | tilt and distance from face/shoulder | scale/re-anchor on SP | `letteringProof {exactText, method, pairPath}` + shipped asset; transparent edges, no extra marks |
| e.g. CTA label | — | yes | html-text | HTML/CSS | CTA button | text centered in button | line-break/fit on SP | copy proof + font proof |

### Raster / consumer surface ownership

<!-- Required for contained and object-detail photos before generation. If CSS
owns the card, the bitmap contains no panel shell, internal padding, radius,
shadow, or colored card field. Separate semantic stories default to separate
assets. -->

| raster | consumer id(s) | frame owner | background owner | bleed edges | bitmap must exclude | isolated + crop-in-use review |
| --- | --- | --- | --- | --- | --- | --- |
| e.g. phone object photo | work.card-01 | CSS consumer | CSS consumer | right/top/bottom | panel, radius, shadow, blue padding | `reports/crops/work-phone-surface-pair.png` |

### Large curve geometry

| element | primitive | measured geometry | source evidence / exception | elements it must stay behind |
| --- | --- | --- | --- | --- |
| e.g. CTA/footer arc | circle-arc | diameter 2200px; center 42% / 1180px; upper outer arc visible | `reports/crops/cta-seam-comp.png` | cta.copy, cta.photo |

<!-- ============================================================ -->

## Page composition plan (Phase 4.5 — multi-frame: REQUIRED)

<!-- The frames say what each section says; THIS designs the page.
Copy these rows into manifest.pageComposition. Phase 7 binds them to rendered
section rects with page_flow_check.py. -->

**Reference frame height**: <px>

### Section strategy and bottom-edge ownership

<!-- One row per section-comp. For every source device touching/extending past
the lower frame edge, decide clip / bleed-to-next / next-section-owned /
cross-section-bridge. Do not default every section to overflow:hidden. -->

| section | heightStrategy | density | minHeightRatio / target range | overflowPolicy | bottom-edge device disposition / clipReason |
| --- | --- | --- | --- | --- | --- |
| 01 | content-led | balanced | 1.0 / 900–1180px | visible | e.g. line continues into 02 as bridge |
| 02 | breathing | airy | 1.15 / 1040–1320px | bleed-to-next | |

### Seam contract (one line per adjacent pair)

| from→to | type | eye hand-off / narrative | transitionSpacePx | bridgeElements (manifest id/el) | evidencePath |
| --- | --- | --- | ---: | --- | --- |
| 01→02 | motif-bridge | shared white ground; photo edge fades out | 120 | motif.line | reports/crops/seam-01-02.png |
| 02→03 | | | | | |

### Art-directed continuity (only from a verbatim seamless/scroll request)

<!-- Invoke seamless-section-waves. target-surface + incoming-preview are
mandatory; add outgoing-environment or connective-motif so at least three
layers participate. Bind the resulting seam-continuity/v1 receipt in
specialistReports.seamContinuity. -->

| from→to | source quote/path | surface owner + destination token | primitive | layers | previewTargets / cueTarget | desktop + mobile crops | color sample report |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01→02 | — | to-section / — | bezier | outgoing-environment, target-surface, connective-motif, incoming-preview | next.title / hero.scrollCue | reports/seams/01-02.png + reports/seams/01-02-mobile.png | reports/seams/01-02-color.json |

### Connective motifs

<!-- Recurring devices from the essence ledgers (accent lines, label
style, numbering, palette accents) and where each recurs — one hand, one
system, not one appearance per frame. -->

- Motif: … → recurs at: …

### Whitespace & density rhythm

<!-- Which sections are dense, which are air; where the reader pauses
before the next push (esp. around CTA sections). Section heights follow
content + rhythm; frame height is the density FLOOR — below-FV sections
may run taller than their 16:9 frames. -->

### Scroll narrative

<!-- One sentence per boundary: what should the reader feel/expect next? -->

- After 01: …
- After 02: …
