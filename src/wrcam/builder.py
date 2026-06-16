"""Integrate frame camera actions into a canonical OpenCV C2W trajectory.

Rotations accumulate about the running camera frame; translations accumulate in
the running camera basis. Within a segment the motion is linearly interpolated
across its frames, giving near-per-frame control for arbitrary angles and
arbitrary translation directions.
"""

from __future__ import annotations

import math

import numpy as np

from wrcam.actions import CameraScript, FrameAction, parse_camera_script
from wrcam.trajectory import CameraTrajectory


def default_intrinsics(width: int, height: int, *, fov_deg: float = 60.0) -> np.ndarray:
    fx = float(width) / (2.0 * math.tan(math.radians(float(fov_deg)) / 2.0))
    fy = fx
    return np.asarray([[fx, 0.0, width / 2.0], [0.0, fy, height / 2.0], [0.0, 0.0, 1.0]], dtype=np.float32)


def _rotation_matrix(kind: str, signed_degrees: float) -> np.ndarray:
    rad = math.radians(float(signed_degrees))
    c, s = math.cos(rad), math.sin(rad)
    if kind == "yaw":
        mat = [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]
    elif kind == "pitch":
        mat = [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]
    elif kind == "roll":
        mat = [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]
    else:
        raise ValueError(f"Unsupported rotation kind: {kind}")
    return np.asarray(mat, dtype=np.float32)


def _signed_rotation_degrees(action: FrameAction) -> float:
    deg = float(action.degrees or 0.0)
    if action.kind == "yaw":
        return -deg if action.direction == "left" else deg
    if action.kind == "pitch":
        return deg if action.direction == "up" else -deg
    if action.kind == "roll":
        return deg if action.direction in {"left", "ccw"} else -deg
    raise ValueError(f"{action.kind} is not a rotation action")


def _translation_delta(action: FrameAction) -> np.ndarray:
    amount = float(action.amount or 0.0)
    delta = np.zeros(3, dtype=np.float32)
    if action.kind == "pan":
        delta[0] = -amount if action.direction == "left" else amount
    elif action.kind == "dolly":
        delta[2] = amount if action.direction == "forward" else -amount
    elif action.kind == "crane":
        delta[1] = -amount if action.direction == "up" else amount
    else:
        raise ValueError(f"{action.kind} is not a translation action")
    return delta


def _expanded_actions(script: CameraScript) -> list[FrameAction]:
    expanded: list[FrameAction] = []
    for action in script.actions:
        if action.frames is None:
            raise ValueError("all camera actions must have explicit frame counts before trajectory build")
        expanded.append(action)
    if not expanded:
        raise ValueError("camera script has no actions")
    return expanded


def build_camera_trajectory(
    script: CameraScript | str,
    *,
    width: int,
    height: int,
    fps: int = 16,
    intrinsics: np.ndarray | None = None,
    camera_type: str | None = None,
) -> CameraTrajectory:
    """Integrate actions into a canonical normalized OpenCV C2W trajectory."""

    if isinstance(script, str):
        script = parse_camera_script(script, fps=fps)
    actions = _expanded_actions(script)
    frame_count = int(script.frame_count or 0)
    c2w = np.repeat(np.eye(4, dtype=np.float32)[None], frame_count, axis=0)
    current_r = np.eye(3, dtype=np.float32)
    current_t = np.zeros(3, dtype=np.float32)
    out_idx = 0

    for action in actions:
        n = int(action.frames or 0)
        start_r = current_r.copy()
        start_t = current_t.copy()
        if action.kind in {"yaw", "pitch", "roll"}:
            end_r = start_r @ _rotation_matrix(action.kind, _signed_rotation_degrees(action))
            end_t = start_t
        elif action.kind in {"pan", "dolly", "crane"}:
            end_r = start_r
            end_t = start_t + _translation_delta(action)
        else:
            end_r = start_r
            end_t = start_t

        for local_idx in range(n):
            alpha = 1.0 if n == 1 else float(local_idx) / float(n - 1)
            if action.kind in {"yaw", "pitch", "roll"}:
                step_deg = _signed_rotation_degrees(action) * alpha
                c2w[out_idx, :3, :3] = start_r @ _rotation_matrix(action.kind, step_deg)
                c2w[out_idx, :3, 3] = start_t
            else:
                c2w[out_idx, :3, :3] = start_r
                c2w[out_idx, :3, 3] = start_t + (end_t - start_t) * alpha
            out_idx += 1
        current_r, current_t = end_r, end_t

    k = default_intrinsics(width, height) if intrinsics is None else np.asarray(intrinsics, dtype=np.float32)
    if k.ndim == 2:
        k = np.repeat(k[None], frame_count, axis=0)
    return CameraTrajectory(
        c2w=c2w,
        intrinsics=k,
        camera_type=camera_type or script.to_string(),
        fps=int(fps),
        source="camera_action_script",
        conversion_mode="canonical_frame_actions_to_opencv_c2w",
    )
