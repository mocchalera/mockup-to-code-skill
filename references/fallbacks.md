# Environment setup, degraded modes, and the evidence ladder

Read this at setup, and again the moment any tool (OpenCV, browser, script)
fails. Degraded modes are legitimate; SILENT degradation is not.

## Setup (once per environment)

```bash
bash "$SKILL_DIR/scripts/setup_env.sh"
```

Reports three axes and a RECOMMENDED MODE line (full / pillow-fallback /
browser-degraded):

- **scripts** — verifies every required script exists in `$SKILL_DIR/scripts/`
  and prints `export SKILL_DIR=…`. All doc commands use `$SKILL_DIR` — the
  scripts live in the SKILL directory, NOT in your project workspace. If one
  is missing, the skill installation is broken: report it; do not rewrite the
  tool ad hoc unless the run cannot proceed otherwise (and say so).
- **browser** — discovery order: `CHROME_PATH` > playwright-managed Chromium >
  system Chrome/Chromium/Edge > playwright download.
- **python** — OpenCV+numpy = full. Pillow+numpy = fallback (normalize /
  sample_color / crop_asset / crop_pair work; snap_bbox, profile, pixel_diff
  and the contamination check need OpenCV). The setup probes, in order,
  `MOCKUP_PYTHON`, `PYTHON`, the caller project's `.venv`, PATH `python3`, and
  common macOS Python locations; it prints the first full-capability path as
  `export MOCKUP_PYTHON=...`. Use that interpreter for measurement commands
  instead of assuming PATH `python3` has cv2.

`contract_doctor.py` is stdlib-only and is never degraded by a missing browser,
OpenCV, or Pillow. Run it even when the rest of the evidence ladder is reduced;
an environment failure does not justify malformed manifest or score contracts.
`mockup_pipeline.py` is also stdlib-only: use `--phase init` once, then
`pre-css`/`completion` to assemble ordered gates and retain one
`pipeline-summary.json`. It never overwrites an existing run.

### Recommended Python environment

```bash
cd /path/to/project
python3 -m venv .venv && .venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install opencv-python numpy pillow
```

Use `.venv/bin/python` for measurement scripts; add `.venv/` to `.gitignore`.
After setup, either copy its printed export or invoke
`"${MOCKUP_PYTHON:-python3}" "$SKILL_DIR/scripts/<script>.py" ...`.

## WORK_ROOT — output isolation (dirty-repo protocol)

All commands are parameterized on `WORK_ROOT` (default `work/`). When the
user says "start fresh / don't touch existing artifacts", or `work/` holds
uncommitted output from another run:

```bash
export WORK_ROOT=work/<job-name>   # e.g. work/fresh-ax1-lp
mkdir -p "$WORK_ROOT"/{mockups,assets,site/css,reports/crops,reports/sections}
```

Never read or overwrite the previous run's tree. State the chosen WORK_ROOT
in your first progress message and in the completion report.

## No-OpenCV fallback — must be earned

`setup_env.sh` reporting "Pillow fallback" is a diagnosis, not permission.
ATTEMPT the venv install first (`pip install --dry-run opencv-python` costs
seconds). Fallback is legitimate only when (a) the attempt failed — paste the
command and error into the completion report — or (b) installs are explicitly
forbidden. Field data: a run accepted fallback where the dry-run resolved a
wheel; every downstream weakness traced back to that unforced choice.

In genuine fallback:

- **Measurement**: read FV + `section-critical` coordinates off the
  normalized frame yourself (zoom, count against the 1440px space), tag
  `bboxSource: normalized`; handoff/spec values are `bboxSource: user`.
  Never back-fill from your own DOMRects (hard rule 9).
- **Tolerances widen one step**: keep `priority`, set explicit `tolerance` —
  critical ±4 → ±8, high ±8 → ±16, normal ±16 → ±24.
- **Normalization/cropping**: `sips` (macOS) / ImageMagick; Playwright clip
  screenshots for section strips (clip is viewport-relative — scroll first).
- **Contamination check**: eyeball every shipped crop at ≥200% zoom, corners
  and edges included, and say so in the report.
- **Report it**: completion report states fallback mode, which elements are
  hand-measured, and that pixel-level claims are correspondingly weaker.

## Browser instability — discipline, then ladder

`render.mjs`/`visual-check.mjs` (v7) hold a cross-process launch lock and
retry with backoff internally. Your side of the discipline:

- **ONE browser at a time.** Never run two renders/checks in parallel —
  parallel launches were the original crash trigger (SIGKILL under memory
  pressure).
- Sequential loop: render → diff → fix → render.
- If a launch still fails after the script's own 3 retries, do NOT keep
  re-running it in a loop. Move DOWN the transport ladder:

1. **File-based scripts** (render.mjs / visual-check.mjs) — default; full
   evidence.
2. **MCP Playwright / in-app browser / Chrome extension** — same checks,
   different transport: navigate to the file, resize per viewport, evaluate
   the same DOMRect/overlap probes, screenshot. Artifacts stay the same
   (rects → box-report, screenshots into `reports/`).
3. **Chrome CLI one-shots** (`--headless --screenshot=… --window-size=…`) —
   screenshots only; no rects. Box diff and computed height rhythm pause;
   visual judgment (crop pairs, section review) continues — crop_pair.py needs
   only the PNG. Capture a crop spanning every adjacent seam.
4. **Static checks + blocked note** — manifest `data-el` presence, copy
   strings, event wiring greppable in the HTML/JS. Write
   `reports/verification-blocked.md`: what was attempted (commands + errors),
   what evidence exists, what remains unverified.

## Evidence priority ladder (when the environment caps you)

Spend whatever verification capacity exists in THIS order — the FV carries
the user's judgment of the whole build:

1. FV crop pairs (lockup, photo, CTA) — Pillow-only, almost never blocked
2. FV box diff (desktop) + FV masked pixel diff
3. Mobile FV screenshot + heading/CTA checks
4. One screenshot per below-FV section + their `section-critical` crop pairs
5. Full box loop across all sections
6. `--widths` responsive sweep

## Image generation output persistence

When a generated background is required, treat the generator as incomplete
until a readable image file is verified on disk. If the environment reports a
save directory for generated images, list it and copy the chosen generated
file into `"$WORK_ROOT"/assets/`; leave the original in place. If no file can
be found, record the failed lookup in `reports/photo-asset-review.md` and use
`assetStrategy: "placeholder"` rather than drawing a synthetic substitute.
Never upgrade a placeholder to `generated` based only on an in-chat preview.
Do not downgrade from generation to a narrower crop of the fused comp. A
text-free crop is not a fallback when it changes the specified environment;
`asset_preflight.py` blocks it. For stock or placeholder fallback, keep the
failed `generationAttempts` entry with generator, full prompt, and exact error.

An honest run that delivers 1–4 with a blocked note beats a run that burned
its budget retrying Chrome for item 5. Degradations are stated in the
completion report — pass/limitation split, never buried.

## Completion report (all modes)

**The headline is `completion-verdict.json`'s status** (Phase 10, hard rule
20): `complete`, `prototype`, or `blocked` — 完了/complete wording only for
`complete`. Immediately after the headline, state `asset-preflight.json` and
`artifact-check.json` status
(`pass` / `needs_work` / `blocked`) and any needs_work/blocked items. Then state:
mode (+ degraded axes), WORK_ROOT, artifact checklist with paths, box-diff pass
rate (and what it covers), section + page scores (axis-min), impression metrics,
the top-5 visible gaps table, pixel comparison coverage, artifact input SHA
receipts/freshness, every placeholder, every hybrid-residual with
cause, every blocked verification with its attempt evidence, and the gate's
`prototype_reasons`/`warnings` verbatim. Multi-frame reports also state
`page-flow.json` status, actual section-height ratios, each section's overflow
policy, and the seam-evidence paths. If the browser ladder could not produce
rects, report page-flow as blocked rather than inferring a pass from the source
frame dimensions.

Report two self-scores separately, never as one blended number:

- **WEB品質 / Web quality** — usability, responsive behavior, accessibility,
  information architecture, production readiness.
- **カンプ再現度 / Comp fidelity** — box/pixel fidelity, crop-pair evidence,
  photo/asset match, detail-device survival, section/page scores.

The self-score calibration note (−3pt) applies: report scores you can back with
crop-pair paths. In degraded modes the gate still runs — pass
`--no-pixel-evidence`/`--no-impression-evidence` with the recorded failure,
never skip it.
