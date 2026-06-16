"""Preset camera-motion combinations plus arbitrary go-return builders.

Presets return a :class:`~wrcam.actions.CameraScript`. They are thin, transparent
wrappers over the frame-action grammar so researchers can either use a named
combination (``yaw_LR``) or compose arbitrary angles/translations directly.

Go-return semantics: a ``*_LR`` preset rotates/translates one way for the first
half of the frames, then returns the opposite way for the rest, ending near the
original pose. Use :func:`sweep` for a one-directional motion of any angle.
"""

from __future__ import annotations

from typing import Callable

from wrcam.actions import CameraScript


DEFAULT_FRAMES = 81
DEFAULT_YAW_PEAK_DEG = 60.0
DEFAULT_PAN_AMOUNT = 0.5


def _split(frames: int) -> tuple[int, int]:
    half = max(1, int(frames) // 2)
    rest = max(1, int(frames) - half)
    return half, rest


def static(frames: int = DEFAULT_FRAMES) -> CameraScript:
    return CameraScript().static(frames=int(frames))


def yaw_LR(peak_deg: float = DEFAULT_YAW_PEAK_DEG, frames: int = DEFAULT_FRAMES) -> CameraScript:
    """Yaw left to ``peak_deg`` then return right (go-return)."""
    half, rest = _split(frames)
    return CameraScript().yaw("left", degrees=peak_deg, frames=half).yaw("right", degrees=peak_deg, frames=rest)


def yaw_RL(peak_deg: float = DEFAULT_YAW_PEAK_DEG, frames: int = DEFAULT_FRAMES) -> CameraScript:
    """Yaw right to ``peak_deg`` then return left (go-return)."""
    half, rest = _split(frames)
    return CameraScript().yaw("right", degrees=peak_deg, frames=half).yaw("left", degrees=peak_deg, frames=rest)


def pan_LR(amount: float = DEFAULT_PAN_AMOUNT, frames: int = DEFAULT_FRAMES) -> CameraScript:
    """Pan left then return right (go-return)."""
    half, rest = _split(frames)
    return CameraScript().pan("left", amount=amount, frames=half).pan("right", amount=amount, frames=rest)


def pan_RL(amount: float = DEFAULT_PAN_AMOUNT, frames: int = DEFAULT_FRAMES) -> CameraScript:
    """Pan right then return left (go-return)."""
    half, rest = _split(frames)
    return CameraScript().pan("right", amount=amount, frames=half).pan("left", amount=amount, frames=rest)


def sweep(kind: str, direction: str, value: float, frames: int = DEFAULT_FRAMES) -> CameraScript:
    """One-directional motion of any angle/amount, e.g. ``sweep('yaw', 'left', 37)``."""
    script = CameraScript()
    if kind in {"yaw", "pitch", "roll"}:
        getattr(script, kind)(direction, degrees=value, frames=int(frames))
    elif kind in {"pan", "dolly", "crane"}:
        getattr(script, kind)(direction, amount=value, frames=int(frames))
    else:
        raise ValueError(f"Unsupported sweep kind {kind!r}")
    return script


def go_return(kind: str, first: str, second: str, value: float, frames: int = DEFAULT_FRAMES) -> CameraScript:
    """Generic go-return for any rotation/translation kind and directions."""
    half, rest = _split(frames)
    script = CameraScript()
    is_rotation = kind in {"yaw", "pitch", "roll"}
    kw = "degrees" if is_rotation else "amount"
    getattr(script, kind)(first, frames=half, **{kw: value})
    getattr(script, kind)(second, frames=rest, **{kw: value})
    return script


PRESETS: dict[str, Callable[..., CameraScript]] = {
    "static": static,
    "yaw_LR": yaw_LR,
    "yaw_RL": yaw_RL,
    "pan_LR": pan_LR,
    "pan_RL": pan_RL,
}


def preset_names() -> list[str]:
    return list(PRESETS)


def build_preset(name: str, **kwargs) -> CameraScript:
    if name not in PRESETS:
        raise KeyError(f"Unknown preset {name!r}; valid: {preset_names()}")
    return PRESETS[name](**kwargs)
