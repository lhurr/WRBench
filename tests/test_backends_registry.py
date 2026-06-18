"""Extended backend and runtime tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wrbench.backends.launchers.easyanimate import build_easyanimate_command
from wrbench.backends.registry import list_backends, resolve_backend
from wrbench.runtime import RuntimeConfig, ModelRuntime, load_runtime_config


def test_resolve_backend_defaults_to_dry_run_without_runtime():
    backend = resolve_backend("wan22-fun-5b-cam")
    assert backend.name == "dry_run"


def test_resolve_backend_local_when_runtime_configured(tmp_path: Path):
    runtime_path = tmp_path / "wrbench.runtime.json"
    repo = tmp_path / "EasyAnimate"
    repo.mkdir()
    (repo / "predict_v2v_control.py").write_text("# stub\n", encoding="utf-8")
    py = tmp_path / "python"
    py.write_text("#!/bin/sh\n", encoding="utf-8")
    py.chmod(0o755)
    weights = tmp_path / "weights"
    weights.mkdir()
    runtime_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "models": {
                    "easyanimate-v51-camera": {
                        "python_bin": str(py),
                        "repo_root": str(repo),
                        "model_path": str(weights),
                        "gpu_id": 0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    runtime = load_runtime_config(runtime_path)
    assert runtime is not None
    backend = resolve_backend("easyanimate-v51-camera", runtime=runtime)
    assert backend.name == "local_subprocess"
    ok, _ = backend.available_for("easyanimate-v51-camera")
    assert ok


def test_build_easyanimate_command(tmp_path: Path):
    repo = tmp_path / "EasyAnimate"
    repo.mkdir()
    (repo / "predict_v2v_control.py").write_text(
        "\n".join(
            [
                "GPU_memory_mode         = \"model_cpu_offload\"",
                "enable_teacache         = True",
                "teacache_threshold      = 0.08",
                "config_path             = \"config/easyanimate.yaml\"",
                "model_name              = \"models/default\"",
                "sampler_name            = \"Flow\"",
                "sample_size             = [384, 672]",
                "video_length            = 49",
                "fps                     = 8",
                "weight_dtype            = \"torch.float16\"",
                "control_video           = None",
                "control_camera_txt      = \"control.txt\"",
                "ref_image               = \"ref.png\"",
                "prompt                  = \"prompt\"",
                "guidance_scale          = 6.0",
                "seed                    = 43",
                "num_inference_steps     = 50",
                "save_path               = \"samples/out\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    py = tmp_path / "python"
    py.write_text("#!/bin/sh\n", encoding="utf-8")
    py.chmod(0o755)
    weights = tmp_path / "weights"
    weights.mkdir()
    cam_txt = tmp_path / "control.txt"
    cam_txt.write_text("0\n", encoding="utf-8")
    image = tmp_path / "first.png"
    image.write_bytes(b"png")
    out = tmp_path / "out.mp4"

    runtime = ModelRuntime(
        key="easyanimate-v51-camera",
        python_bin=str(py),
        repo_root=str(repo),
        model_path=str(weights),
        gpu_id=0,
    )
    cmd, cwd, env = build_easyanimate_command(
        model="easyanimate-v51-camera",
        payload={
            "control_camera_txt": str(cam_txt),
            "sample_size": [384, 672],
            "video_length": 49,
            "fps": 8,
        },
        runtime=runtime,
        image_path=image,
        prompt="A scene.",
        output_path=out,
    )[:3]
    assert cmd[0] == str(py)
    assert cmd[1].endswith("_easyanimate_run.py")
    assert cwd == repo
    assert env["CUDA_VISIBLE_DEVICES"] == "0"
    materialized = Path(cmd[1])
    assert materialized.is_file()
    assert str(weights) in materialized.read_text(encoding="utf-8")


def test_list_backends_without_runtime():
    rows = list_backends("wan22-fun-5b-cam", runtime=None)
    names = [name for name, _, _ in rows]
    assert "dry_run" in names
