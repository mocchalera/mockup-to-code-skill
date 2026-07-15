#!/usr/bin/env bash
# setup_env.sh — environment bootstrap for the mockup-to-code skill.
#
# Philosophy: NEVER just fail — always end with a report of what works and
# what the alternative is. A missing playwright-managed Chromium is fine if a
# system Chrome exists; a missing OpenCV is fine for the basic
# normalize/sample/crop path (Pillow fallback); no browser at all still
# leaves MCP Playwright / the in-app browser as a verification route.
set -u
CALLER_CWD="$PWD"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SKILL_DIR"

echo "== mockup-to-code setup =="
echo "export SKILL_DIR=\"$SKILL_DIR\""
STATUS_BROWSER="missing"
STATUS_PY="missing"
STATUS_SCRIPTS="ok"

# --------------------------------------------------------------- preflight
REQUIRED_SCRIPTS=(
  normalize_image.py
  profile.py
  snap_bbox.py
  sample_color.py
  crop_asset.py
  crop_pair.py
  mockup_pipeline.py
  prompt_receipt.py
  split_sprite.py
  contract_doctor.py
  asset_preflight.py
  _box_quality.py
  box_diff.py
  artifact_check.py
  page_flow_check.py
  pixel_diff.py
  completion_gate.py
  render.mjs
  visual-check.mjs
  motion-check.mjs
  _browser.mjs
  _imgcompat.py
)
MISSING_SCRIPTS=()
for SCRIPT in "${REQUIRED_SCRIPTS[@]}"; do
  if [ ! -f "scripts/$SCRIPT" ]; then
    MISSING_SCRIPTS+=("$SCRIPT")
  fi
done
if [ "${#MISSING_SCRIPTS[@]}" -eq 0 ]; then
  echo "required scripts: all present"
else
  STATUS_SCRIPTS="missing"
  echo "missing required scripts:"
  for SCRIPT in "${MISSING_SCRIPTS[@]}"; do
    echo "  - scripts/$SCRIPT"
  done
fi

# ---------------------------------------------------------------- node deps
# playwright-core (the driver library) is required by render.mjs and
# visual-check.mjs regardless of WHICH chromium binary is used.
if [ ! -d node_modules/playwright-core ]; then
  npm init -y >/dev/null 2>&1 || true
  PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install playwright-core --no-fund --no-audit \
    || echo "WARN: npm install playwright-core failed — render.mjs will not run; use MCP Playwright / in-app browser"
fi

# ------------------------------------------------------------- find chromium
# Order: CHROME_PATH > existing playwright chromium > system browsers >
# playwright install (download) as last resort.
find_system_chrome() {
  for C in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium" \
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
    /usr/bin/google-chrome /usr/bin/google-chrome-stable \
    /usr/bin/chromium-browser /usr/bin/chromium; do
    if [ -x "$C" ]; then echo "$C"; return 0; fi
  done
  return 1
}

CHROME="${CHROME_PATH:-}"
if [ -n "$CHROME" ] && [ ! -x "$CHROME" ]; then
  echo "WARN: CHROME_PATH=$CHROME is not executable — ignoring"
  CHROME=""
fi
if [ -z "$CHROME" ]; then
  CHROME="$(node -e "console.log(require('playwright-core').chromium.executablePath())" 2>/dev/null || true)"
  [ -n "$CHROME" ] && [ ! -x "$CHROME" ] && CHROME=""
fi
if [ -z "$CHROME" ]; then
  CHROME="$(find_system_chrome || true)"
  [ -n "$CHROME" ] && echo "using system browser: $CHROME"
fi
if [ -z "$CHROME" ]; then
  echo "no system/playwright chromium — attempting playwright download..."
  export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1
  npx playwright install chromium --no-shell 2>&1 | tail -1 || true
  CHROME="$(node -e "console.log(require('playwright-core').chromium.executablePath())" 2>/dev/null || true)"
  [ -n "$CHROME" ] && [ ! -x "$CHROME" ] && CHROME=""
fi

# ------------------------------------------- stub missing X libs (linux only)
if [ -n "$CHROME" ] && command -v ldd >/dev/null 2>&1; then
  MISSING="$(ldd "$CHROME" 2>/dev/null | awk '/not found/{print $1}' | sort -u)"
  if [ -n "$MISSING" ]; then
    mkdir -p .libs
    for LIB in $MISSING; do
      case "$LIB" in
        libX*|libxcb*)
          echo "stubbing $LIB (X11 lib unused in headless)"
          cat > /tmp/stub_gen.c <<'EOF'
void XDamageQueryExtension(void){} void XDamageQueryVersion(void){}
void XDamageCreate(void){} void XDamageDestroy(void){}
void XDamageSubtract(void){} void XDamageAdd(void){}
EOF
          gcc -shared -fPIC -o ".libs/$LIB" /tmp/stub_gen.c || echo "WARN: gcc failed for $LIB"
          ;;
        *)
          echo "WARN: missing non-X library $LIB — stubbing is unsafe; install it properly"
          ;;
      esac
    done
  fi
fi

# --------------------------------------------------------------- verify launch
if [ -n "$CHROME" ]; then
  cat > /tmp/setup_verify.html <<'EOF'
<!doctype html><body><h1 data-el="probe" style="font-size:40px">setup ok</h1></body>
EOF
  if CHROME_PATH="$CHROME" node scripts/render.mjs --html /tmp/setup_verify.html \
       --out-rects /tmp/setup_rects.json >/dev/null 2>&1 \
     && grep -q '"el": "probe"' /tmp/setup_rects.json; then
    STATUS_BROWSER="ok ($CHROME)"
    case "$CHROME" in
      "$SKILL_DIR"*|*ms-playwright*) : ;;  # playwright-managed: auto-discovered
      *) echo "NOTE: export CHROME_PATH=\"$CHROME\" (render.mjs also auto-discovers this path)";;
    esac
  else
    STATUS_BROWSER="found but launch failed ($CHROME)"
  fi
fi

# --------------------------------------------------------------- python deps
# Do not assume the first `python3` on PATH is the useful one. On macOS it is
# common for Homebrew Python to lack cv2 while /usr/local/bin/python3 or the
# project's venv has the full measurement stack.
probe_python() {
  "$1" - <<'EOF' 2>/dev/null
mods = {}
for m in ("cv2", "numpy", "PIL"):
    try:
        __import__(m)
        mods[m] = True
    except ImportError:
        mods[m] = False
if mods["cv2"] and mods["numpy"]:
    print("full")
elif mods["PIL"] and mods["numpy"]:
    print("fallback")
else:
    print("none")
EOF
}

PYTHON_CANDIDATES=()
[ -n "${MOCKUP_PYTHON:-}" ] && PYTHON_CANDIDATES+=("$MOCKUP_PYTHON")
[ -n "${PYTHON:-}" ] && PYTHON_CANDIDATES+=("$PYTHON")
[ -x "$CALLER_CWD/.venv/bin/python" ] && PYTHON_CANDIDATES+=("$CALLER_CWD/.venv/bin/python")
PATH_PYTHON="$(command -v python3 2>/dev/null || true)"
[ -n "$PATH_PYTHON" ] && PYTHON_CANDIDATES+=("$PATH_PYTHON")
for CANDIDATE in /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
  [ -x "$CANDIDATE" ] && PYTHON_CANDIDATES+=("$CANDIDATE")
done

PYTHON_BIN=""
PY_REPORT="none"
FALLBACK_PYTHON=""
SEEN_PYTHONS="|"
for CANDIDATE in "${PYTHON_CANDIDATES[@]}"; do
  [ -x "$CANDIDATE" ] || continue
  case "$SEEN_PYTHONS" in
    *"|$CANDIDATE|"*) continue ;;
  esac
  SEEN_PYTHONS="$SEEN_PYTHONS$CANDIDATE|"
  CANDIDATE_REPORT="$(probe_python "$CANDIDATE" || true)"
  case "$CANDIDATE_REPORT" in
    full)
      PYTHON_BIN="$CANDIDATE"
      PY_REPORT="full"
      break
      ;;
    fallback)
      if [ -z "$FALLBACK_PYTHON" ]; then
        FALLBACK_PYTHON="$CANDIDATE"
      fi
      ;;
  esac
done

if [ -z "$PYTHON_BIN" ] && [ -n "$FALLBACK_PYTHON" ]; then
  PYTHON_BIN="$FALLBACK_PYTHON"
  PY_REPORT="fallback"
fi

case "${PY_REPORT:-none}" in
  full)     STATUS_PY="ok ($PYTHON_BIN; OpenCV — all scripts)" ;;
  fallback) STATUS_PY="fallback ($PYTHON_BIN; Pillow — normalize/sample/crop work; snap_bbox, profile, pixel_diff and the crop contamination check need OpenCV: pip install opencv-python)" ;;
  *)        STATUS_PY="missing (pip install opencv-python numpy — or minimally: pip install Pillow numpy)" ;;
esac

# -------------------------------------------------------------------- report
echo ""
echo "== setup report =="
echo "browser : $STATUS_BROWSER"
echo "python  : $STATUS_PY"
[ -n "$PYTHON_BIN" ] && echo "export MOCKUP_PYTHON=\"$PYTHON_BIN\""
echo "scripts : $STATUS_SCRIPTS"
if [ "$STATUS_SCRIPTS" != "ok" ] || [[ "$STATUS_BROWSER" != ok* ]]; then
  RECOMMENDED_MODE="browser-degraded"
elif [ "${PY_REPORT:-none}" = "full" ]; then
  RECOMMENDED_MODE="full"
elif [ "${PY_REPORT:-none}" = "fallback" ]; then
  RECOMMENDED_MODE="pillow-fallback"
else
  RECOMMENDED_MODE="python-missing"
fi
echo "recommended mode: $RECOMMENDED_MODE"
if [ "$STATUS_BROWSER" = "missing" ]; then
  echo ""
  echo "No local Chromium available. render.mjs / visual-check.mjs will not run."
  echo "Alternatives (SKILL.md 'Rendering environments'):"
  echo "  - install Google Chrome and re-run, or set CHROME_PATH"
  echo "  - use MCP Playwright (mcp__playwright_*) or the in-app browser for"
  echo "    rendering/screenshots; keep the manifest+box-diff loop for geometry"
  exit 1
fi
echo "== setup complete =="
