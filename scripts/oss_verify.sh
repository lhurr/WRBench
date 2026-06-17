#!/usr/bin/env bash
# Open-source verification gate for WRCam.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== leak scan =="
PATTERN='(/media/datasets|10\.40\.[0-9]+|OminiEWM_Data|/tmp/ljp/)'
SCAN_PATHS=(src docs examples scripts wrcam.runtime.example.json README.md CONTRIBUTING.md CHANGELOG.md)
if rg -n "$PATTERN" "${SCAN_PATHS[@]}" --glob '!scripts/oss_verify.sh' 2>/dev/null; then
  echo "FAIL: private path or ssh reference found in publish tree"
  exit 1
fi
echo "OK: no private-path matches"

echo "== install + pytest =="
TMP="$(mktemp -d)"
PY=""
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    major="${ver%%.*}"
    minor="${ver#*.}"
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; }; then
      PY="$candidate"
      break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "FAIL: need Python >=3.10 (python3.12/python3.11/python3.10 not found)"
  exit 1
fi
echo "Using $PY ($("$PY" --version))"
"$PY" -m venv "$TMP/venv"
# shellcheck disable=SC1091
source "$TMP/venv/bin/activate"
pip install -q -U pip setuptools wheel
if ! pip install -q -e ".[dev]"; then
  echo "FAIL: editable install -e \".[dev]\" failed"
  exit 1
fi
python -m pytest -q
python -c "import wrcam; print('models', len(wrcam.list_models()))"
deactivate
rm -rf "$TMP"
echo "OK: clean venv install + tests"

echo "All OSS checks passed."
