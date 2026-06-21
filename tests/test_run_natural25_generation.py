from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_run_natural25_generation_manifest_is_eval_ready(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_natural25_generation.py"
    scope = root / "src" / "wrbench" / "data" / "natural25" / "camera_scopes" / "t2v_rotation_stress_30_60.json"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--model",
            "minwm-wan-action2v",
            "--out-dir",
            str(tmp_path),
            "--camera-scope",
            str(scope),
            "--prompt-profile",
            "t2v_layout_anchor",
            "--dry-run",
            "--overwrite-existing",
            "--fail-fast",
            "--limit",
            "1",
            "--shard-index",
            "0",
            "--num-shards",
            "1",
        ],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    manifest = tmp_path / "minwm-wan-action2v" / "manifest.shard00.jsonl"
    row = json.loads(manifest.read_text(encoding="utf-8").splitlines()[0])
    assert set(row) >= {
        "schema_version",
        "model",
        "display_name",
        "video_id",
        "variant_id",
        "family_id",
        "reasoning_tier",
        "event_delta",
        "camera",
        "camera_type",
        "camera_preset",
        "camera_scope_id",
        "path",
        "world_state_prompt",
        "expected_state",
        "prompt_profile_id",
        "ti2v_prompt",
        "prompt",
        "model_input",
        "status",
    }
    assert "output_id" not in row
    assert "event_tier" not in row
    assert "output_path" not in row
    assert "video_path" not in row
    assert "prompt_text" not in row
    assert "generation_prompt" not in row
    assert "generation_manifest_status" not in row
    assert row["world_state_prompt"]
    assert row["expected_state"]
    assert row["ti2v_prompt"]
    assert row["prompt_profile_id"] == "t2v_layout_anchor"
    assert row["prompt"]
    assert row["prompt"] != row["ti2v_prompt"]
    assert "Realistic photography" not in row["prompt"]
    assert "left third of the frame" in row["prompt"]
    assert row["model_input"] == "T2V"
    assert row["status"] == "ok"
    assert row["control_family"] == "static"
    assert row["control_direction"] == "static"
    assert row["control_profile"] == "canonical_static"
    assert row["target_coordinate_convention"] == "opencv_c2w"
    assert Path(row["target_pose_path"]).is_file()
