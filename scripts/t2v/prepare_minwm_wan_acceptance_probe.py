#!/usr/bin/env python3
"""Prepare minWM Wan T2V acceptance probe inputs with unified prompts + yaw patch."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import wrbench
from wrbench.datasets import (
    NATURAL25_PROMPT_PROFILES,
    PROMPT_PROFILE_T2V_LAYOUT_ANCHOR,
    load_jsonl,
    load_natural25_t2v_layout_anchors,
    natural25_variants_path,
    resolve_variant_prompt,
    resolve_variant_prompt_profile,
)
from wrbench.presets import yaw_LR, yaw_RL


@dataclass(frozen=True)
class ProbeCase:
    variant_id: str
    camera_preset: str


def _parse_case(value: str) -> ProbeCase:
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("--case must be formatted as VARIANT_ID:CAMERA_PRESET")
    variant_id = parts[0].strip()
    camera_preset = parts[1].strip()
    if not variant_id:
        raise argparse.ArgumentTypeError("--case variant id must be non-empty")
    if camera_preset not in {"yaw_LR", "yaw_RL"}:
        raise argparse.ArgumentTypeError("--case camera preset must be yaw_LR or yaw_RL")
    return ProbeCase(variant_id=variant_id, camera_preset=camera_preset)


def _camera_for_preset(camera_preset: str, frames: int = 77):
    if camera_preset == "yaw_RL":
        return yaw_RL(frames=frames)
    if camera_preset == "yaw_LR":
        return yaw_LR(frames=frames)
    raise ValueError(f"unsupported probe camera preset {camera_preset!r}")


def build_probe(out_dir: Path, cases: tuple[ProbeCase, ...], *, prompt_profile: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt_profile_id = resolve_variant_prompt_profile(prompt_profile)
    layout_anchors = (
        load_natural25_t2v_layout_anchors()
        if prompt_profile_id == PROMPT_PROFILE_T2V_LAYOUT_ANCHOR
        else None
    )
    by_id = {row["variant_id"]: row for row in load_jsonl(natural25_variants_path())}
    manifest = []
    for case in cases:
        row = by_id[case.variant_id]
        prompt = resolve_variant_prompt(
            row,
            prompt_profile=prompt_profile_id,
            layout_anchors=layout_anchors,
        )
        variant_dir = out_dir / f"{case.variant_id}__{case.camera_preset}"
        variant_dir.mkdir(parents=True, exist_ok=True)
        out_video = variant_dir / "output.mp4"
        result = wrbench.compile_camera(
            model="minwm-wan-action2v",
            camera=_camera_for_preset(case.camera_preset),
            out=out_video,
            prompt=prompt,
            dry_run=True,
        )
        payload = result["payload"].payload
        patch = payload.get("rotation_step_patch") or {}
        prompt_path = variant_dir / "prompt.txt"
        traj_path = variant_dir / "trajectory.txt"
        shutil.copy2(payload["prompt_txt"], prompt_path)
        shutil.copy2(payload["trajectory_txt"], traj_path)
        launcher = None
        if patch:
            patch_root = Path(patch["patch_root"])
            if patch_root.parent != variant_dir:
                target_patch = variant_dir / "minwm_camera_patch"
                if target_patch.exists():
                    shutil.rmtree(target_patch)
                shutil.copytree(patch_root, target_patch)
                patch_root = target_patch
            launcher = variant_dir / "launch_with_rot_step.sh"
            launcher.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                'HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
                'PATCH_ROOT="${HERE}/minwm_camera_patch"\n'
                'PATCH_FILE="${PATCH_ROOT}/wan_utils/camera_trajectory.py"\n'
                'if [[ ! -f "${PATCH_FILE}" ]]; then\n'
                '  echo "FATAL: rotation-step patch module missing at ${PATCH_FILE}" >&2\n'
                "  exit 3\n"
                "fi\n"
                'if [[ ! -f "${PATCH_ROOT}/sitecustomize.py" ]]; then\n'
                '  echo "FATAL: sitecustomize meta_path override missing at ${PATCH_ROOT}/sitecustomize.py" >&2\n'
                "  exit 3\n"
                "fi\n"
                'if [[ -z "${PYTHONPATH+x}" ]]; then\n'
                '  echo "FATAL: PYTHONPATH must be set before applying the minWM patch" >&2\n'
                "  exit 3\n"
                "fi\n"
                'export PYTHONPATH="${PATCH_ROOT}:${PYTHONPATH}"\n'
                'exec "$@"\n',
                encoding="utf-8",
            )
            launcher.chmod(0o755)
        token_details = (
            result["payload"].metadata.get("model_payload_summary", {}).get("token_mapping_details")
            or result["payload"].metadata.get("model_control_extra", {}).get("token_mapping_details")
            or {}
        )
        entry = {
            "variant_id": case.variant_id,
            "camera_preset": case.camera_preset,
            "prompt_profile_id": prompt_profile_id,
            "ti2v_prompt": row["ti2v_prompt"],
            "generation_prompt": prompt,
            "prompt": prompt,
            "trajectory": payload["trajectory"],
            "token_mapping_details": token_details,
            "rotation_step_patch": patch or None,
            "work_dir": str(variant_dir),
        }
        manifest.append(entry)
        (variant_dir / "compile_manifest.json").write_text(
            json.dumps(entry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"out_dir": str(out_dir), "variants": manifest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prompt-profile", required=True, choices=NATURAL25_PROMPT_PROFILES)
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        required=True,
        type=_parse_case,
        help="Explicit probe case formatted as VARIANT_ID:CAMERA_PRESET.",
    )
    args = parser.parse_args()
    cases = tuple(args.cases)
    summary = build_probe(args.out_dir, cases, prompt_profile=args.prompt_profile)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
