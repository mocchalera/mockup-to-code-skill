# Worked example — reconstructing an AI-generated poster FV (hybrid mode)

The canonical hybrid case: an AI-generated comp where the first view is a
poster — a full-bleed photo with a giant Japanese heading, an outline-type
year, a yellow highlight band, a vertical label, and a CTA, all **baked into
one image**. This walks the decomposition end to end. Follow the same shape
for your own comp; every artifact listed at the end is completion evidence.

## Before: what the comp gives you

One PNG (`raw.png`, 1536px wide), FV region roughly `0,0,1536,1000`:

- photo of a person at a desk, text printed across it
- 96px-equivalent heading 「想いを、かたちに。」 overlapping the photo
- outline-only "2026" behind the heading
- yellow band under one phrase, vertical label 「相続と遺言」 on the right edge
- dark bottom band with CTA 「無料相談を予約する」

Naive approaches that fail here:

- **crop the whole FV as an image** → copy is frozen, not responsive, not accessible
- **crop the photo region as-is** → `crop_asset.py` flags contamination (text
  baked into the photo); shipping it doubles the text under HTML type
- **HTML type with default letter-spacing/line-height** → "cheap" — the comp's
  quality lives in the tight typography

## Step 1 — layer plan (before any CSS)

| id | layerRole | zLayer | positioning | assetStrategy | notes |
| --- | --- | --- | --- | --- | --- |
| fv.bg | background-photo | -2 | absolute | **generated** | full-bleed, NOT a card |
| fv.overlay | photo-overlay-gradient | -1 | absolute | css | bottom-up dark gradient |
| fv.year | decorative-outline-type | 0 | absolute | html-text | aria-hidden |
| fv.title | primary-html-type | 1 | flow | html-text | mustNotCover: [fv.bg face area] |
| fv.band | accent-band | 1 | flow | html-text | highlight-band pattern |
| fv.label | vertical-label | 1 | absolute | html-text | writing-mode vertical-rl |
| fv.panel | dark-bottom-panel | 2 | flow | css | holds CTA |
| fv.cta | cta | 3 | flow | html-text | qaPriority: fv-critical |

The single highest-leverage decision: **fv.bg is a background layer, not an
image card.** Record it as `backgroundBehavior: "full-bleed"` so
visual-check.mjs can enforce it.

## Step 2 — regenerate the photo text-free (imagegen)

The crop is contaminated, no layered source exists → regenerate:

```
prompt: "Photo of a Japanese man in his 60s writing at a wooden desk by a
window, soft natural morning light, shallow depth of field, warm muted
tones, calm and dignified mood, no text, no letters, no typography,
clean background, photographic, 3:2"
```

Save to `work/assets/fv-bg.png` and record in the manifest:

```json
{
  "id": "fv.bg", "el": "fv-bg", "role": "image",
  "priority": "critical", "qaPriority": "fv-critical",
  "layerRole": "background-photo", "zLayer": -2, "positioning": "absolute",
  "assetStrategy": "generated", "backgroundBehavior": "full-bleed",
  "visualRole": "background-environment",
  "photoCompositionMode": "full-frame-plate",
  "sourceFrameHasForegroundOverlap": true,
  "sourceFrameOverlapKinds": ["structural-text", "cta", "watermark"],
  "cleanLayeredSource": false,
  "generatedAsset": {
    "prompt": "Photo of a Japanese man in his 60s writing at a wooden desk…",
    "sourceImage": "raw.png",
    "workspacePath": "work/assets/fv-bg.png",
    "generator": "imagegen",
    "usedBy": ["fv.bg"],
    "contaminationCheck": {"method": "200% visual sweep", "verdict": "clean"},
    "reviewPath": "work/reports/photo-asset-review.md",
    "pairPath": "work/reports/crops/fv-photo-pair.png"
  },
  "bbox": {"x": 0, "y": 0, "w": 1440, "h": 940}, "bboxSource": "normalized"
}
```

Before writing FV CSS, run the source/composition gate:

```bash
python3 "$SKILL_DIR/scripts/asset_preflight.py" work/manifest.json --work-root work \
  --out work/reports/asset-preflight.json
```

Continue only when `implementationAllowed` is true. Cropping a clean corner of
`raw.png` would remain blocked because the intended full-field photo is fused
with foreground design and the crop would change the poster composition.

Also write `work/reports/imagegen-prompt.md` (prompt + source + destination +
where used) — that file is evidence.

## Step 3 — rebuild every piece of type in HTML

All copy — heading, year, band phrase, vertical label, CTA — is HTML text.
Match the comp's typographic treatment with `templates/poster-typography.css`:

```html
<section class="fv" data-el="fv">
  <div class="fv-bg" data-el="fv-bg"><img src="../assets/fv-bg.png" alt=""></div>
  <div class="fv-overlay" data-el="fv-overlay"></div>
  <span class="outline-type" data-el="fv-year" aria-hidden="true">2026</span>
  <div class="fv-content container">
    <p class="caption-en" data-el="fv-eyebrow">WILL &amp; INHERITANCE</p>
    <h1 class="poster-heading" data-el="fv-title">想いを、<br>かたちに。</h1>
    <p data-el="fv-band"><span class="highlight-band">遺言書は、家族への最後の手紙です</span></p>
  </div>
  <p class="vertical-label" data-el="fv-label">相続と遺言</p>
  <div class="dark-panel" data-el="fv-panel">
    <a class="cta" data-el="fv-cta" href="#contact">無料相談を予約する</a>
  </div>
</section>
```

Size/tracking/leading come from the comp via the render loop (bbox compare),
not by eyeballing — but chase the *treatment*: if the comp's heading is
tight (line-height ≈ 1.05, negative tracking, palt), yours must be too.
First freeze its source `letterformClass`, then save crop pairs for 2–3
same-class font candidates in `typeSpec.fontBakeoffEvidence`. Keep structural
glyphs untransformed; adjust family, weight, size, tracking, leading, run-level
size/vertical-align, and flow spacing. A transform needs a visibly distorted
source device plus `typeSpec.transformException` and a readable proof crop.

## Step 4 — verify intent, both viewports, from the start

```bash
node scripts/render.mjs --html work/site/index.html --viewport 1440x900 \
  --out-png work/reports/rendered.png --out-rects work/reports/rects.json
python3 scripts/box_diff.py work/manifest.json work/reports/rects.json \
  --out work/reports/box-report.json
node scripts/visual-check.mjs --html work/site/index.html \
  --manifest work/manifest.json --viewports 1440x900,390x844 \
  --out work/reports/visual-check.json
```

Then the FV QA gate (SKILL.md) — the questions visual-check cannot answer
(does the photo read as a seamless background? does type interfere with the
face?) you answer by looking at the screenshots at both widths.

## Evidence checklist (done = all of these exist)

- `work/manifest.json` — layer plan fields populated for every FV element
- `work/reports/asset-preflight.json` — `pass`, implementation allowed
- `work/assets/fv-bg.png` — regenerated text-free photo
- `work/reports/imagegen-prompt.md` — prompt / source / path / usedBy
- `work/reports/box-report.json` — geometry loop result
- `work/reports/visual-check.json` — `"ok": true` at desktop AND mobile
- `work/reports/rendered.png` (+ a mobile screenshot) — for the human eye
