#!/usr/bin/env bash
# Run fairness + capability verification (VGGT-Omega direction + frame QC).
# Requires WRBenchLib calibration harness on the GPU host.
set -euo pipefail

CONFIG="${WRCAM_FAIRNESS_CONFIG:-}"
WRBENCHLIB="${WRBENCHLIB_ROOT:-}"
HOST="${WRCAM_SSH_HOST:-}"
PORT="${WRCAM_SSH_PORT:-22}"
REMOTE_REPO="${WRBENCHLIB_REMOTE_REPO:-}"
REMOTE_OUT="${WRCAM_FAIRNESS_REMOTE_OUT:-}"
OUT="${WRCAM_FAIRNESS_OUT:-.artifacts/fairness_verification}"

if [[ -z "$CONFIG" ]]; then
  if [[ -n "$WRBENCHLIB" && -f "$WRBENCHLIB/config/camera_calibration_acceptance.json" ]]; then
    CONFIG="$WRBENCHLIB/config/camera_calibration_acceptance.json"
  elif [[ -f "config/camera_calibration_acceptance.json" ]]; then
    CONFIG="config/camera_calibration_acceptance.json"
  else
    echo "Set WRCAM_FAIRNESS_CONFIG to camera_calibration_acceptance.json"
    exit 1
  fi
fi

mkdir -p "$OUT"

echo "Running baseline acceptance (skip D2 triage; VGGT direction gate)..."
if [[ -n "$WRBENCHLIB" && -d "$WRBENCHLIB" ]]; then
  cd "$WRBENCHLIB"
  python3 scripts/calibration/run_calibration_batch.py \
    --config "$CONFIG" \
    --phase baseline \
    --skip-d2 \
    --out-dir "$(cd - >/dev/null && pwd)/$OUT" \
    --local-only
  python3 scripts/calibration/run_calibration_batch.py \
    --config "$CONFIG" \
    --phase report \
    --out-dir "$(pwd)/$OUT"
else
  if [[ -z "$HOST" || -z "$REMOTE_REPO" || -z "$REMOTE_OUT" ]]; then
    echo "Remote mode requires WRCAM_SSH_HOST, WRBENCHLIB_REMOTE_REPO, and WRCAM_FAIRNESS_REMOTE_OUT"
    echo "Or set WRBENCHLIB_ROOT to a local WRBenchLib checkout."
    exit 1
  fi
  ssh -o BatchMode=yes -p "$PORT" "root@${HOST}" \
    "cd ${REMOTE_REPO} && \
     python3 scripts/calibration/run_calibration_batch.py \
       --config config/camera_calibration_acceptance.json \
       --phase baseline --skip-d2 --skip-vggt \
       --remote-out ${REMOTE_OUT}/baseline && \
     python3 scripts/calibration/run_calibration_batch.py \
       --config config/camera_calibration_acceptance.json \
       --phase report --remote-out ${REMOTE_OUT}"
  scp -P "$PORT" -r "root@${HOST}:${REMOTE_OUT}/" "$OUT/remote/"
fi

echo "Report: $OUT/ACCEPTANCE_SUMMARY.md (or remote copy under $OUT/remote/)"
echo "Policy: direction-correct (VGGT-Omega/D1) + frame-clean = fairness gate;"
echo "        amplitude/D1 accuracy is advisory (model_limitation), not perfection."
