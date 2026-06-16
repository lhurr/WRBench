"""Build EasyAnimate V5.1 control-camera subprocess commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wrcam.contracts import require_execution_contract, require_mapping, require_int
from wrcam.runtime import ModelRuntime


def build_easyanimate_command(
    *,
    model: str,
    payload: dict[str, Any],
    runtime: ModelRuntime,
    image_path: Path,
    prompt: str,
    output_path: Path,
) -> tuple[list[str], Path, dict[str, str]]:
    execution = require_execution_contract(model)
    runtime_parameters = dict(require_mapping(execution, "runtime_parameters"))
    official_defaults = dict(require_mapping(execution, "official_script_defaults"))
    benchmark_profile = dict(require_mapping(execution, "wrbench_benchmark_profile"))
    official_profile = dict(require_mapping(execution, "official_inference_profile"))

    if not runtime.repo_root:
        raise ValueError(f"{model}: runtime.repo_root is required")
    if not runtime.python_bin:
        raise ValueError(f"{model}: runtime.python_bin is required")
    if not runtime.model_path:
        raise ValueError(f"{model}: runtime.model_path is required")

    control_camera_txt = payload.get("control_camera_txt")
    if not control_camera_txt:
        raise ValueError(f"{model}: payload missing control_camera_txt")

    sample_size = payload.get("sample_size") or benchmark_profile.get("sample_size") or [384, 672]
    height, width = int(sample_size[0]), int(sample_size[1])
    video_length = int(payload.get("video_length") or benchmark_profile.get("video_length") or 49)
    fps = int(payload.get("fps") or benchmark_profile.get("fps") or 8)

    repo = Path(runtime.repo_root)
    entrypoint = str(execution.get("entrypoint") or "predict_v2v_control.py")
    script = repo / entrypoint
    if not script.is_file():
        raise FileNotFoundError(f"EasyAnimate entrypoint not found: {script}")

    cmd = [
        str(runtime.python_bin),
        str(script),
        "--prompt",
        prompt,
        "--video_length",
        str(video_length),
        "--fps",
        str(fps),
        "--sample_size",
        str(height),
        str(width),
        "--config_path",
        str(official_defaults.get("config_path", runtime_parameters.get("config_path", ""))),
        "--model_path",
        str(runtime.model_path),
        "--weight_dtype",
        str(official_defaults.get("weight_dtype", runtime_parameters.get("weight_dtype", "torch.bfloat16"))),
        "--gpu_memory_mode",
        str(official_defaults.get("gpu_memory_mode", runtime_parameters.get("gpu_memory_mode", "model_cpu_offload"))),
        "--guidance_scale",
        str(official_profile.get("guidance_scale", official_defaults.get("guidance_scale", 6.0))),
        "--num_inference_steps",
        str(official_profile.get("num_inference_steps", official_defaults.get("num_inference_steps", 50))),
        "--sampler_name",
        str(official_profile.get("sampler_name", official_defaults.get("sampler_name", "Flow"))),
        "--seed",
        str(official_profile.get("seed", official_defaults.get("seed", 43))),
        "--validation_image_start",
        str(image_path),
        "--control_camera_txt",
        str(control_camera_txt),
        "--save_path",
        str(output_path),
    ]
    if official_defaults.get("enable_teacache") or official_profile.get("enable_teacache"):
        cmd.extend(
            [
                "--enable_teacache",
                "--teacache_threshold",
                str(official_profile.get("teacache_threshold", official_defaults.get("teacache_threshold", 0.08))),
            ]
        )

    env = dict(runtime.env)
    env.setdefault("CUDA_VISIBLE_DEVICES", str(runtime.gpu_id))
    env.setdefault("PYTHONUNBUFFERED", "1")
    return cmd, repo, env
