#!/usr/bin/env bash
# Open-source verification gate for WRCam.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== leak scan =="
PATTERN='/media/datasets|10\.40\.|OminiEWM|/tmp/ljp|root@10\.|ssh -'
if rg -n "$PATTERN" src docs examples wrcam.runtime.example.json README.md CONTRIBUTING.md CHANGELOG.md 2>/dev/null; then
  echo "FAIL: private path or ssh reference found in publish tree"
  exit 1
fi
echo "OK: no private-path matches"

echo "== install + pytest =="
TMP="$(mktemp -d)"
python3 -m venv "$TMP/venv"
# shellcheck disable=SC1091
source "$TMP/venv/bin/activate"
pip install -q -U pip setuptools wheel
pip install -q -e ".[dev]" || {
  echo "editable install failed; falling back to PYTHONPATH=src"
  pip install -q pytest numpy
  export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
}
python -m pytest -q
python -c "import wrcam; print('models', len(wrcam.list_models()))"
deactivate
rm -rf "$TMP"
echo "OK: clean venv install + tests"

echo "All OSS checks passed."
