# Raster and lettering asset review — <project>

<!--
One block per photo/illustration visual OR generated lettering decal that
needed an asset decision (generated / stock replace / layered source /
transparent lettering / placeholder). This is the Phase 3 adoption checklist
as a recorded table — the judgment trail that imagegen-prompt.md alone doesn't
hold. Every ADOPTED asset also gets a crop pair vs its comp region under
work/reports/crops/ and is re-judged in the Phase 7 section review (mood/grade
drift and lettering-glyph drift read at section scale).

Rules this file enforces (principles 6, 13):
- photo-class content is NEVER satisfied by SVG/CSS/flat-avatar or by
  rendering your own HTML to PNG.
- lettering decals are allowed only for non-structural expressive text; CTA,
  nav, headings, body, labels and legal copy are rebuilt as HTML/CSS text.
- a rejected candidate is recorded WITH its failing box — don't
  rationalize a near-miss into adoption; regenerate.
- contamination check runs on every candidate (crop_asset.py report, or
  a stated ≥200% visual sweep when cv2 is unavailable).
-->

## <visual id> — comp region: `<frame>` roi <x,y,w,h>

**Full intended photo field**: <bbox/description, before candidate crop>
**Visual role**: background-environment | contained-photo | object-detail | subject-cutout
**Source frame foreground overlap**: yes / no
**Overlap kinds**: <structural text, nav, CTA, watermark, UI, etc.; none if no>
**Separate clean layered source**: yes / no — <path when yes>
**Crop composition test**: preserves / fails — <subject count, environment,
focal relationships, copy-space geometry, aspect>

**Comp bar** (from hypotheses.md): subject / mood & lighting / color
grade / aspect & focal / empty zones the layer plan needs / in-photo
props that must become HTML overlays

**Strategy**: generated | crop-asset | replace(provided/owned/stock) | layered-source | placeholder
**Prompt / source**: <imagegen prompt ref or stock URL+license>
**Prompt integrity**: <exact prompt file + SHA-256; input references with role
and whether each was actually sent to the generator, not merely consulted>

Candidate effort is risk-based: generate at least two candidates for an FV
full-frame plate or a multi-device/CTA-critical asset. Start with one for a
low-risk contained photo, and generate another only when the scorecard has a
failing axis. Do not record an immediately adopted single candidate as a
bake-off.

### Generation attempts (required for fused/overlapped fields without a clean provided/layered source)

<!-- Record the actual tool call before any stock/placeholder fallback. A
clean subcrop is not a failed generation attempt and is not a fallback. -->

| attempt | generator | prompt path/full prompt | status | output path | exact error or rejection reason |
| --- | --- | --- | --- | --- | --- |
| 1 | imagegen | `work/reports/imagegen-prompt.md#<visual>` | succeeded / failed | `work/assets/<candidate>.png` / — | |

| candidate | zero text·logo·UI (≥200% sweep) | subject & identity | mood & lighting | color grade | aspect & focal | empty zones empty | props absent/planned | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| work/assets/<f1>.png | | | | | | | | adopt / reject: <why> |
| work/assets/<f2>.png | | | | | | | | |

**Adopted**: `work/assets/<file>.png` — pair vs comp:
`work/reports/crops/<NN>-<visual>-pair.png`
**Final crop-in-use pairs**: <desktop/mobile consumer pairs; for multi-zone
assets, one pair per `inventoryId`/consumer>
**Manifest evidence**: source overlap fields + `generatedAsset` /
`replacedAsset` / `croppedAsset` entry updated
(`prompt`, `workspacePath`, `generator`, `contaminationCheck`,
`reviewPath`, `pairPath`; `workspacePath` verified readable on disk)
**Residual** (known, accepted difference vs comp — e.g. "different
person, same age/wardrobe/mood"): <one line>

**Web delivery derivative**: <AVIF/WebP paths, intrinsic dimensions, bytes,
srcset/sizes/loading/fetchpriority policy. Keep the original as evidence; do
not ship the multi-megabyte evidence PNG by default.>

## <lettering id> — comp region: `<frame>` roi <x,y,w,h>

**Target text**: <exact phrase, punctuation, line breaks>
**Non-structural reason**: <why this is a decorative decal, not HTML copy>
**Anchor relationship**: <photo/face/copy-space/word it follows; mustNotCover>
**Strategy**: generated transparent PNG | crop-source | hand-traced SVG | replace
**Prompt / source**: <imagegen prompt ref or source path>

| candidate | exact text/glyphs at 200% | transparent/clean edge | hand/mood match | no extra marks | anchor fit | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| work/assets/<lettering-1>.png | | | | | | adopt / reject: <why> |
| work/assets/<lettering-2>.png | | | | | | |

**Adopted**: `work/assets/<file>.png` — pair vs comp:
`work/reports/crops/<NN>-<lettering>-pair.png`
**Manifest evidence**: `mediaClass: "lettering-decal"` +
`generatedAsset` / `replacedAsset` entry updated (`prompt`,
`workspacePath`, `generator`, `reviewPath`, `pairPath`) +
`letteringProof {exactText, method, pairPath}` with `exactText == text.content`
**Residual**: <one line, or "none">
