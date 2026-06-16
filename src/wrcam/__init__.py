"""WRCam: out-of-the-box unified camera control for video-generation models.

Quickstart::

    import wrcam

    # Preset combination
    wrcam.compile_camera(model="wan22-fun-5b-cam", camera="yaw:left:60@40,yaw:right:60@41",
                         image="first.png", out="out.mp4")

    # Arbitrary angle, near-per-frame
    script = wrcam.presets.sweep("yaw", "left", 37, frames=49)
    wrcam.compile_camera(model="wan22-fun-5b-cam", camera=script, image="first.png", out="out.mp4")

By default this compiles the model-native payload and writes auditable sidecars
without running any heavy model (dry-run). See ``wrcam.backends`` for real
generation hooks.
"""

from __future__ import annotations

from wrcam import presets
from wrcam.actions import CameraScript, FrameAction, parse_camera_script
from wrcam.builder import build_camera_trajectory
from wrcam.registry import (
    active_model_keys,
    all_records,
    canonical_model_key,
    deferred_model_keys,
    model_record,
)
from wrcam.runner import compile_camera

__version__ = "0.1.0"


def list_models(include_deferred: bool = False) -> list[str]:
    """Canonical keys of supported models."""
    keys = active_model_keys()
    if include_deferred:
        keys = keys + deferred_model_keys()
    return keys


__all__ = [
    "__version__",
    "CameraScript",
    "FrameAction",
    "parse_camera_script",
    "build_camera_trajectory",
    "compile_camera",
    "presets",
    "list_models",
    "canonical_model_key",
    "model_record",
    "all_records",
    "active_model_keys",
    "deferred_model_keys",
]
