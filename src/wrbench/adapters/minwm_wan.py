from __future__ import annotations

from pathlib import Path

from wrbench.adapters._utils import adapter_taxonomy_metadata, ensure_work_dir, model_target_trajectory, write_json
from wrbench.adapters.base import register
from wrbench.adapters.minwm import _latent_frame_count, _trajectory_string
from wrbench.contracts import (
    build_command_template,
    require_execution_contract,
    require_int,
    require_mapping,
    require_str,
)
from wrbench.payload import CameraPayload
from wrbench.registry import canonical_model_key
from wrbench.trajectory import CameraTrajectory


@register("minwm-wan-action2v")
class MinWMWanAction2VAdapter:
    """minWM Wan 2.1 Action2V camera variant.

    Shares minWM's native motion-token mapping with the HY variant (see
    wrbench.adapters.minwm). Only the execution contract differs: Wan inference
    is config + checkpoint + data_path + trajectory driven via Wan21/wan_inference.py.
    """

    name = "minwm_wan_action2v"

    def compile(
        self,
        trajectory: CameraTrajectory,
        *,
        model_name: str,
        width: int,
        height: int,
        num_frames: int,
        work_dir: str | Path | None = None,
        device: str | None = None,
    ) -> CameraPayload:
        key = canonical_model_key(model_name)
        execution = require_execution_contract(key)
        runtime_parameters = require_mapping(execution, "runtime_parameters")
        benchmark_profile = require_mapping(execution, "wrbench_benchmark_profile")
        official_profile = require_mapping(execution, "official_inference_profile")
        benchmark_frames = require_int(benchmark_profile, "video_length")
        benchmark_fps = require_int(benchmark_profile, "fps")
        chunk_latent_frames = require_int(runtime_parameters, "chunk_latent_frames")
        entrypoint = require_str(execution, "entrypoint")
        out_dir = ensure_work_dir(work_dir)
        target, amp = model_target_trajectory(trajectory, key, num_frames)
        if int(target.frame_count) != benchmark_frames:
            raise ValueError(f"{key} requires contract video_length {benchmark_frames}, got {target.frame_count}")
        if int(target.fps) != benchmark_fps:
            raise ValueError(f"{key} requires contract fps {benchmark_fps}, got {target.fps}")

        trajectory_string, mapping_rule, token_details = _trajectory_string(target, latent_stride=chunk_latent_frames)
        latent_frames = _latent_frame_count(target.frame_count, latent_stride=chunk_latent_frames)
        action_token_count = sum(int(part.split("*", 1)[1]) for part in trajectory_string.split(","))

        # Wan reads the trajectory per-prompt from --trajectory_path (one line per prompt,
        # aligned with --data_path). WRBench compiles a single sample, so one line.
        trajectory_txt = out_dir / "minwm_wan_action2v_trajectory.txt"
        trajectory_txt.write_text(trajectory_string + "\n", encoding="utf-8")

        command_template = build_command_template(
            execution,
            values={
                "data_path": "<data_dir>",
                "output_folder": "<output_dir>",
                "trajectory_path": str(trajectory_txt),
            },
        )
        request_json = write_json(
            out_dir / "minwm_wan_action2v_run_request.json",
            {
                "entrypoint": entrypoint,
                "command_template": command_template,
                "model": require_str(runtime_parameters, "model"),
                "hf_revision": require_str(runtime_parameters, "hf_revision"),
                "transformer_subdir": require_str(runtime_parameters, "transformer_subdir"),
                "base_model": require_str(runtime_parameters, "base_model"),
                "input_contract": {
                    "data_dir": "<data_dir>",
                    "data_dir_layout": (
                        "Wan TextImagePairDataset directory: target_crop_info_<aspect>.json metadata "
                        "plus an aspect-ratio image subfolder holding the first-frame image(s). "
                        "Materialize from the WRBench first-frame image + dynamic-event prompt before a real run."
                    ),
                    "trajectory_path": str(trajectory_txt),
                    "trajectory_field": "minWM native motion token string (one line per prompt, aligned with data_path)",
                    "trajectory_string": trajectory_string,
                    "token_mapping_rule": mapping_rule,
                    "token_mapping_details": token_details,
                },
                "runtime_parameters": runtime_parameters,
                "official_runtime": require_mapping(execution, "official_runtime"),
                "official_inference_profile": official_profile,
                "wrbench_benchmark_profile": benchmark_profile,
                "wrbench_policy": require_mapping(execution, "wrbench_policy"),
            },
        )

        payload_type = "minwm_wan_action2v_trajectory_json"
        return CameraPayload(
            payload_type=payload_type,
            payload={
                "trajectory_txt": str(trajectory_txt),
                "request_json": str(request_json),
                "trajectory": trajectory_string,
                "command_template": command_template,
            },
            target_trajectory=target,
            official_camera_entrypoint="Wan21/wan_inference.py --i2v with per-prompt --trajectory_path",
            coordinate_notes=(
                "minWM Wan Action2V does not consume WRBench C2W directly. WRBench camera families are approximated "
                "as native minWM motion tokens: a/d lateral translation, w/s forward/back, j/l yaw, i/k pitch."
            ),
            calibration_status=amp.calibration_status,
            metadata=adapter_taxonomy_metadata(
                model_name=key,
                amp=amp,
                target=target,
                requested_frames=int(num_frames),
                payload_type=payload_type,
                certification_kind="native_motion_token_payload",
                model_payload_summary={
                    "entrypoint": entrypoint,
                    "model": require_str(runtime_parameters, "model"),
                    "hf_revision": require_str(runtime_parameters, "hf_revision"),
                    "transformer_subdir": require_str(runtime_parameters, "transformer_subdir"),
                    "official_video_length": require_int(official_profile, "video_length"),
                    "official_fps": require_int(official_profile, "fps"),
                    "trajectory": trajectory_string,
                    "latent_frame_count": latent_frames,
                    "action_token_count": action_token_count,
                    "token_mapping_rule": mapping_rule,
                    "token_mapping_details": token_details,
                },
                target_c2w_is_model_effective=False,
                control_sample_kind="action_matrix_or_pose",
                control_sample_count=max(1, action_token_count),
                sampling_rule="wrbench_camera_family_to_minwm_native_motion_tokens",
                model_control_extra={
                    "trajectory": trajectory_string,
                    "latent_frame_count": latent_frames,
                    "action_token_count": action_token_count,
                    "token_mapping_details": token_details,
                    "target_c2w_is_desired_wrbench_motion": True,
                    "model_effective_camera_requires_empirical_calibration": True,
                },
            ),
        )
