#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CANDIDATES=()
[ -n "${MOCKUP_PYTHON:-}" ] && CANDIDATES+=("$MOCKUP_PYTHON")
CANDIDATES+=(python3 /usr/local/bin/python3 /opt/homebrew/bin/python3)

for PYTHON_BIN in "${CANDIDATES[@]}"; do
  if command -v "$PYTHON_BIN" >/dev/null 2>&1 \
    && "$PYTHON_BIN" -c 'import PIL, numpy' >/dev/null 2>&1; then
    exec "$PYTHON_BIN" "$ROOT/test/run_sprite_split_tests.py"
  fi
done

echo "sprite split tests require one Python with Pillow and numpy" >&2
echo "run scripts/setup_env.sh and export its MOCKUP_PYTHON value" >&2
exit 1
