#!/usr/bin/env bash
# Open-source verification gate for WRBench.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== leak scan =="
SCAN_PATHS=(src docs examples scripts wrbench.runtime.example.json README.md CONTRIBUTING.md CHANGELOG.md CODE_OF_CONDUCT.md SECURITY.md)

PRIVATE_PATTERN='(/media/datasets|10\.40\.[0-9]+|OminiEWM_Data|/tmp/ljp/|OoVMetric|4DWorldEvolution|workplace/|gpu_proof|qwen35_vlm|P25D3D4|docs/teamwork/)'
if rg -n "$PRIVATE_PATTERN" "${SCAN_PATHS[@]}" \
  --glob '!scripts/oss_verify.sh' \
  --glob '!docs/teamwork/**' 2>/dev/null; then
  echo "FAIL: internal path or legacy reference found in publish tree"
  exit 1
fi
echo "OK: no private-path matches"

WRBENCHLIB_FORM_PATTERN='WRBenchLib/|WRBenchLib\.git|github\.com/[^[:space:]]*WRBenchLib|git@[^[:space:]]*WRBenchLib|(^|[^[:alnum:]_])wrbenchlib([^[:alnum:]_]|$)|pip[[:space:]]+install[^[:cntrl:]]*WRBenchLib|from[[:space:]]+WRBenchLib|import[[:space:]]+WRBenchLib'
if rg -n "$WRBENCHLIB_FORM_PATTERN" "${SCAN_PATHS[@]}" \
  --glob '!scripts/oss_verify.sh' \
  --glob '!docs/teamwork/**' 2>/dev/null; then
  echo "FAIL: internal WRBenchLib path, package, import, or repo reference found"
  exit 1
fi

WRBENCHLIB_BAD=0
while IFS= read -r hit; do
  case "$hit" in
    docs/index.html:*"WRBenchLib, the generation-provenance layer in WRBench"*) ;;
    docs/index.html:*"The WRBenchLib layer maps each test record"*) ;;
    *)
      echo "$hit"
      WRBENCHLIB_BAD=1
      ;;
  esac
done < <(rg -n "WRBenchLib" "${SCAN_PATHS[@]}" \
  --glob '!scripts/oss_verify.sh' \
  --glob '!docs/teamwork/**' 2>/dev/null || true)
if [ "$WRBENCHLIB_BAD" -ne 0 ]; then
  echo "FAIL: WRBenchLib is allowed only as bounded project-page provenance prose"
  exit 1
fi
echo "OK: WRBenchLib references are allowlisted"

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
python - <<'PY'
import json

import wrbench
from wrbench.datasets import (
    load_jsonl,
    load_natural25_families,
    natural25_families_path,
    natural25_first_frame_path,
    natural25_first_frames_dir,
    natural25_first_frames_manifest_path,
    natural25_variants_path,
)
from wrbench.eval.runtime import contract_path

families = load_natural25_families()
variants = list(load_jsonl(natural25_variants_path()))
manifest = json.loads(natural25_first_frames_manifest_path().read_text(encoding="utf-8"))
frames = sorted(natural25_first_frames_dir().glob("*.png"))
missing = [family_id for family_id in families if not natural25_first_frame_path(family_id).is_file()]
manifest_ids = {row["family_id"] for row in manifest}

assert len(families) == 25, len(families)
assert len(variants) == 400, len(variants)
assert len(manifest) == 25, len(manifest)
assert len(frames) == 25, len(frames)
assert not missing, missing
assert manifest_ids == set(families), sorted(set(families) ^ manifest_ids)

print(
    "models", len(wrbench.list_models()),
    "contract", contract_path(),
    "natural25", natural25_families_path(),
    "first_frames", len(frames),
    "variants", len(variants),
)
PY
deactivate
rm -rf "$TMP"
echo "OK: clean venv install + tests"

echo "All OSS checks passed."
