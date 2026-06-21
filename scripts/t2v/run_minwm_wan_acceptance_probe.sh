#!/usr/bin/env bash
# Run minWM Wan T2V acceptance probe on a GPU server (official T2V path, yaw patch enabled).
# Required env: MINWM_ROOT, TORCHRUN_BIN, CKPT, CONFIG, NUM_OUTPUT_FRAMES,
# SP_SIZE, NPROC_PER_NODE, MASTER_PORT, PROBE_ROOT
set -euo pipefail

PROBE_ROOT="${1:?probe root on server}"
MINWM_ROOT="${MINWM_ROOT:?set MINWM_ROOT to minWM checkout}"
TORCHRUN_BIN="${TORCHRUN_BIN:?set TORCHRUN_BIN explicitly}"
CKPT="${CKPT:?set CKPT to Wan21/Action2V/dmd/model.pt}"
CONFIG="${CONFIG:?set CONFIG to the minWM Wan config path}"
NUM_OUTPUT_FRAMES="${NUM_OUTPUT_FRAMES:?set NUM_OUTPUT_FRAMES explicitly}"
SP_SIZE="${SP_SIZE:?set SP_SIZE explicitly}"
NPROC_PER_NODE="${NPROC_PER_NODE:?set NPROC_PER_NODE explicitly}"
MASTER_PORT="${MASTER_PORT:?set MASTER_PORT explicitly}"
if ! [[ "$NUM_OUTPUT_FRAMES" =~ ^[0-9]+$ ]]; then
  echo "NUM_OUTPUT_FRAMES must be an integer, got: $NUM_OUTPUT_FRAMES" >&2
  exit 2
fi
if ! [[ "$SP_SIZE" =~ ^[0-9]+$ ]]; then
  echo "SP_SIZE must be an integer, got: $SP_SIZE" >&2
  exit 2
fi
if ! [[ "$NPROC_PER_NODE" =~ ^[0-9]+$ ]]; then
  echo "NPROC_PER_NODE must be an integer, got: $NPROC_PER_NODE" >&2
  exit 2
fi
if ! [[ "$MASTER_PORT" =~ ^[0-9]+$ ]]; then
  echo "MASTER_PORT must be an integer, got: $MASTER_PORT" >&2
  exit 2
fi

cd "$MINWM_ROOT"
export PYTHONPATH="${MINWM_ROOT}:${PYTHONPATH:-}"

find "$PROBE_ROOT" -mindepth 1 -maxdepth 1 -type d | sort | while read -r variant_dir; do
  variant_id="$(basename "$variant_dir")"
  prompt_path="$variant_dir/prompt.txt"
  traj_path="$variant_dir/trajectory.txt"
  out_dir="$variant_dir/videos"
  mkdir -p "$out_dir"
  launcher="$variant_dir/launch_with_rot_step.sh"
  cmd=(
    "$TORCHRUN_BIN" --standalone --nproc_per_node="$NPROC_PER_NODE" --master_port="$MASTER_PORT"
    Wan21/wan_inference.py
    --config_path "$CONFIG"
    --checkpoint_path "$CKPT"
    --data_path "$prompt_path"
    --output_folder "$out_dir"
    --sp_size "$SP_SIZE"
    --trajectory_path "$traj_path"
    --num_output_frames "$NUM_OUTPUT_FRAMES"
  )
  echo "==> $variant_id"
  if [[ -x "$launcher" ]]; then
    "$launcher" "${cmd[@]}"
  else
    "${cmd[@]}"
  fi
  latest="$(find "$out_dir" -name '*.mp4' -type f | sort | tail -n 1)"
  cp "$latest" "$variant_dir/output.mp4"
  echo "    wrote $variant_dir/output.mp4"
done

echo "Probe complete under $PROBE_ROOT"
