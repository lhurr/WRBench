"""Build Spatia inference.py subprocess commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from wrbench.runtime import ModelRuntime


def _write_intrinsics_file(out_path: Path, intrinsics: Any) -> Path:
    arr = np.asarray(intrinsics, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[None, ...]
    k = arr[0]
    intrinsics_path = out_path.with_suffix(out_path.suffix + ".payload.intrinsics.txt")
    intrinsics_path.write_text(
        f"{float(k[0, 0]):.8f} {float(k[1, 1]):.8f} {float(k[0, 2]):.8f} {float(k[1, 2]):.8f}\n",
        encoding="utf-8",
    )
    return intrinsics_path


def build_spatia_command(
    *,
    model: str,
    payload: dict[str, Any],
    runtime: ModelRuntime,
    source_video_path: Path,
    prompt: str,
    output_path: Path,
    width: int = 1248,
    height: int = 704,
    max_frames: int = 121,
) -> tuple[list[str], Path, dict[str, str], Path]:
    if not runtime.repo_root:
        raise ValueError(f"{model}: runtime.repo_root (spatia_dir) is required")
    if not runtime.python_bin:
        raise ValueError(f"{model}: runtime.python_bin is required")

    w2c_path = payload.get("w2c_trajectory_file")
    if not w2c_path:
        raise ValueError(f"{model}: payload missing w2c_trajectory_file")

    extra = runtime.extra_paths
    vace_path = extra.get("vace_path")
    lora_path = extra.get("lora_path")
    if not vace_path or not lora_path:
        raise ValueError(f"{model}: runtime.extra_paths must include vace_path and lora_path")

    spatia_dir = Path(runtime.repo_root)
    inference_py = spatia_dir / "inference.py"
    if not inference_py.is_file():
        raise FileNotFoundError(f"Spatia inference.py not found: {inference_py}")

    frame_path = output_path.with_suffix(output_path.suffix + ".first_frame.png")
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    _extract_first_frame(source_video_path, frame_path)

    intrinsics_path = _write_intrinsics_file(output_path, payload.get("intrinsics"))
    work_dir = Path(str(output_path.with_suffix("")) + "_assets")
    work_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(runtime.python_bin),
        str(inference_py),
        "--img_path",
        str(frame_path),
        "--camera_w2c_path",
        str(w2c_path),
        "--camera_intrinsics_path",
        str(intrinsics_path),
        "--vace_path",
        str(vace_path),
        "--lora_path",
        str(lora_path),
        "--save_path",
        str(output_path),
        "--work_dir",
        str(work_dir),
        "--prompt",
        prompt,
        "--prompt_path",
        "",
        "--width",
        str(width),
        "--height",
        str(height),
        "--max_frames",
        str(max_frames),
        "--first_round_frames",
        str(max_frames),
        "--fps",
        "24",
        "--num_inference_steps",
        str(extra.get("num_inference_steps", "40")),
        "--cfg_scale",
        str(extra.get("cfg_scale", "3.5")),
        "--sigma_shift",
        str(extra.get("sigma_shift", "5.0")),
        "--seed",
        str(extra.get("seed", "20917")),
    ]

    env = dict(runtime.env)
    env.setdefault("CUDA_VISIBLE_DEVICES", str(runtime.gpu_id))
    env.setdefault("PYTHONUNBUFFERED", "1")
    return cmd, spatia_dir, env, frame_path


def _extract_first_frame(source_video: Path, out_png: Path) -> None:
    import shutil
    import subprocess

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(source_video),
                "-frames:v",
                "1",
                str(out_png),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and out_png.is_file():
            return
    try:
        import cv2  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Spatia backend needs ffmpeg on PATH or opencv-python-headless for first-frame extraction"
        ) from exc
    cap = cv2.VideoCapture(str(source_video))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open source video: {source_video}")
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError(f"Failed to read first frame from {source_video}")
    if not cv2.imwrite(str(out_png), frame):
        raise RuntimeError(f"Failed to write first frame to {out_png}")
