"""Config-driven local subprocess generation backend."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from wrbench.backends.base import GenerationBackend, GenerationRequest, GenerationResult
from wrbench.backends.launchers.easyanimate import build_easyanimate_command, easyanimate_expected_output
from wrbench.backends.launchers.minwm_hy import (
    build_minwm_hy_command,
    minwm_hy_expected_output,
    validate_minwm_hy_runtime,
)
from wrbench.backends.launchers.minwm_wan import (
    build_minwm_wan_command,
    minwm_wan_expected_output,
    validate_minwm_wan_runtime,
)
from wrbench.backends.launchers.spatia import build_spatia_command
from wrbench.registry import canonical_model_key, input_kind, model_record
from wrbench.runtime import ModelRuntime, RuntimeConfig


_SUPPORTED_MODELS = frozenset({"easyanimate-v51-camera", "minwm-hy-action2v", "minwm-wan-action2v", "spatia"})


class LocalSubprocessBackend:
    """Launch model-native inference via subprocess using ``wrbench.runtime.json``."""

    name = "local_subprocess"

    def __init__(self, runtime: RuntimeConfig) -> None:
        self._runtime = runtime

    def available(self) -> tuple[bool, str]:
        if not self._runtime.models:
            return False, "runtime config has no model entries"
        supported = sorted(k for k in self._runtime.models if k in _SUPPORTED_MODELS)
        if not supported:
            return False, f"no supported model runtime entries (supported: {sorted(_SUPPORTED_MODELS)})"
        return True, f"configured for {', '.join(supported)}"

    def available_for(self, model: str) -> tuple[bool, str]:
        key = canonical_model_key(model)
        if key not in _SUPPORTED_MODELS:
            return False, f"local_subprocess backend does not support {key!r} yet"
        node = self._runtime.model(key)
        if node is None:
            return False, f"no runtime entry for {key!r} in wrbench.runtime.json"
        missing = []
        if not node.python_bin or not Path(str(node.python_bin)).exists():
            missing.append("python_bin")
        if not node.repo_root or not Path(str(node.repo_root)).is_dir():
            missing.append("repo_root")
        if key == "easyanimate-v51-camera" and (not node.model_path or not Path(str(node.model_path)).exists()):
            missing.append("model_path")
        if key == "minwm-hy-action2v":
            missing.extend(validate_minwm_hy_runtime(node))
        if key == "minwm-wan-action2v":
            missing.extend(validate_minwm_wan_runtime(node))
        if key == "spatia":
            for field in ("vace_path", "lora_path", "ffmpeg_bin"):
                if field not in node.extra_paths or not Path(str(node.extra_paths[field])).is_file():
                    missing.append(f"extra_paths.{field}")
            for field in ("num_inference_steps", "cfg_scale", "sigma_shift", "seed"):
                if field not in node.extra_paths or not str(node.extra_paths[field]).strip():
                    missing.append(f"extra_paths.{field}")
        missing = list(dict.fromkeys(missing))
        if missing:
            return False, f"missing or invalid runtime fields: {', '.join(missing)}"
        return True, f"ready for {key}"

    def generate(self, request: GenerationRequest) -> GenerationResult:
        key = canonical_model_key(request.model)
        ok, reason = self.available_for(key)
        if not ok:
            return GenerationResult(success=False, message=reason)

        node = self._runtime.model(key)
        assert node is not None
        payload_dict = dict(request.payload.payload)
        output_path = Path(request.output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if key == "easyanimate-v51-camera":
            if not request.image_path:
                raise ValueError("easyanimate requires image_path")
            if not str(request.prompt).strip():
                raise ValueError("easyanimate-v51-camera requires prompt")
            cmd, cwd, env, _expected_output = build_easyanimate_command(
                model=key,
                payload=payload_dict,
                runtime=node,
                image_path=Path(request.image_path).resolve(),
                prompt=request.prompt,
                output_path=output_path,
            )
        elif key == "spatia":
            if not request.source_video_path:
                raise ValueError("spatia requires source_video_path")
            if not str(request.prompt).strip():
                raise ValueError("spatia requires prompt")
            record = model_record(key)
            cmd, cwd, env, frame_path = build_spatia_command(
                model=key,
                payload=payload_dict,
                runtime=node,
                source_video_path=Path(request.source_video_path).resolve(),
                prompt=request.prompt,
                output_path=output_path,
                width=record.default_width,
                height=record.default_height,
                max_frames=record.default_frames,
                fps=record.default_fps,
            )
            payload_dict = {**payload_dict, "first_frame_png": str(frame_path)}
        elif key == "minwm-hy-action2v":
            if not request.image_path:
                raise ValueError("minwm-hy-action2v requires image_path")
            if not str(request.prompt).strip():
                raise ValueError("minwm-hy-action2v requires prompt")
            cmd, cwd, env, output_dir = build_minwm_hy_command(
                model=key,
                payload=payload_dict,
                runtime=node,
                image_path=Path(request.image_path).resolve(),
                prompt=request.prompt,
                output_path=output_path,
            )
        elif key == "minwm-wan-action2v":
            cmd, cwd, env, output_dir = build_minwm_wan_command(
                model=key,
                payload=payload_dict,
                runtime=node,
                prompt=request.prompt,
                output_path=output_path,
            )
        else:
            raise ValueError(f"unsupported model {key}")

        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env={**dict(__import__("os").environ), **env},
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            tail = "\n".join(part for part in (proc.stdout, proc.stderr) if part)[-4096:]
            return GenerationResult(
                success=False,
                output_path=output_path if output_path.is_file() else None,
                message=f"subprocess failed (exit {proc.returncode}): {tail}",
            )

        produced = output_path
        if key == "easyanimate-v51-camera":
            produced = easyanimate_expected_output(output_path.parent)
            if produced.is_file() and produced != output_path:
                if output_path.is_file():
                    output_path.unlink()
                produced.replace(output_path)
            produced = output_path
        elif key == "minwm-wan-action2v":
            produced = minwm_wan_expected_output(output_dir)
            if produced is None:
                return GenerationResult(
                    success=False,
                    message=f"subprocess exited 0 but no minWM Wan mp4 found under: {output_dir}",
                )
            shutil.copy2(produced, output_path)
            produced = output_path
        elif key == "minwm-hy-action2v":
            produced = minwm_hy_expected_output(output_dir)
            if produced is None:
                return GenerationResult(
                    success=False,
                    message=f"subprocess exited 0 but no minWM HY mp4 found under: {output_dir}",
                )
            shutil.copy2(produced, output_path)
            produced = output_path

        if not produced.is_file():
            return GenerationResult(
                success=False,
                message=f"subprocess exited 0 but output missing: {output_path}",
            )
        return GenerationResult(
            success=True,
            output_path=output_path,
            message="generation completed",
            artifacts={"output_mp4": str(output_path), "command": " ".join(cmd[:8]) + " ..."},
        )
