# v7 Script Changes

## Changed files

- `scripts/box_diff.py`
  - Added section-relative recomposition waivers: when a section root renders taller than its comp frame beyond tolerance, non-`fv-critical` child `y` failures are waived as `y_waived_recomposition: true`.
  - Added `summary.y_waived_recomposition`.
  - Kept `x`, `w`, and `h` checks strict, and kept `fv-critical` child `y` checks strict.
  - Added density-floor first-fix guidance when a section root collapses below its comp frame height.

- `scripts/visual-check.mjs`
  - Added `--widths`; with no value it expands to `390,768,1024,1440,1728`.
  - Width mode uses height `844` for widths `<=430`, otherwise `900`.
  - Added `dead-gutter` violations for left-pinned section content that leaves a large right gutter on desktop widths.
  - Added `layout-law` violations for undeclared `position:absolute` / `position:fixed` on `[data-el]` nodes unless the manifest declares `positioning:"absolute"` or an allowed decorative/layer role.

- `scripts/_browser.mjs`
  - Added cross-process Chromium launch lock at `os.tmpdir()/mockup-to-code-browser.lock`.
  - Stale launch locks are taken over after 120 seconds.
  - Browser launch now retries after 5s, 15s, and 30s before failing with a transport-ladder fallback message.

- `scripts/setup_env.sh`
  - Prints `export SKILL_DIR=...` from the script's own location.
  - Verifies required scripts are present and reports missing entries.
  - Prints `recommended mode: full`, `pillow-fallback`, or `browser-degraded`.

- `test/run_v7_script_tests.py`
  - Added regression tests for recomposition y-waiver behavior, density-floor first-fix text, `dead-gutter`, `layout-law`, and concurrent render launch serialization.

## Test commands and observed output

```bash
python3 test/run_v7_script_tests.py
```

Observed:

```text
Ran 5 tests in 7.738s

OK
```

```bash
bash scripts/setup_env.sh
```

Observed:

```text
export SKILL_DIR="$(pwd)"
required scripts: all present
browser : ok (/Applications/Google Chrome.app/Contents/MacOS/Google Chrome)
python  : missing (pip install opencv-python numpy ... or minimally: pip install Pillow numpy)
scripts : ok
recommended mode: pillow-fallback
== setup complete ==
```

```bash
mkdir -p test/work && node scripts/render.mjs --html test/ground_truth.html --viewport 1440x900 --out-png test/work/mockup.png --out-rects test/work/truth_rects.json && python3.13 test/run_snap_test.py
```

Observed:

```text
render.mjs: ok true, viewport 1440x900@1, docHeight 1614, elements 14
box elements:  mean 2.04px / max 34px  (CHECK)
text elements: mean 12.88px / max 29px  (systematic half-leading offset)
```

```bash
python3 -m py_compile scripts/box_diff.py test/run_v7_script_tests.py && node --check scripts/visual-check.mjs && node --check scripts/_browser.mjs
```

Observed: command exited 0 with no output.

```bash
node scripts/visual-check.mjs --html test/ground_truth.html --widths --out test/work/v7-widths-ground-truth.json
```

Observed: command exited 1 as expected for this no-manifest fixture. The output used the default width set `390,768,1024,1440,1728` and reported existing fixture violations including `no-h-scroll` at small widths and `layout-law` for undeclared absolute-position hero elements.
