"""Frame-level camera action grammar for unified camera control.

A ``CameraScript`` is an ordered list of ``FrameAction`` segments. Each segment
covers a contiguous run of frames and expresses one camera intent:

- rotation: ``yaw`` / ``pitch`` / ``roll`` with ``degrees`` (any angle).
- translation: ``pan`` / ``dolly`` / ``crane`` with ``amount`` (any direction).
- ``static``: hold the camera still.

The compact string form is ``kind:direction:value@frames`` joined by commas,
e.g. ``yaw:left:60@40,yaw:right:60@41`` or ``static@81``. This grammar is the
single public surface for arbitrary, near-per-frame camera control.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


ROTATION_KINDS = {"yaw", "pitch", "roll"}
TRANSLATION_KINDS = {"pan", "dolly", "crane"}
ACTION_KINDS = ROTATION_KINDS | TRANSLATION_KINDS | {"static"}
ROTATION_DIRECTIONS = {
    "yaw": {"left", "right"},
    "pitch": {"up", "down"},
    "roll": {"left", "right", "cw", "ccw"},
}
TRANSLATION_DIRECTIONS = {
    "pan": {"left", "right"},
    "dolly": {"forward", "back", "backward"},
    "crane": {"up", "down"},
}


@dataclass(frozen=True)
class FrameAction:
    """One contiguous frame segment of camera intent."""

    kind: str
    direction: str = "none"
    frames: int | None = None
    degrees: float | None = None
    amount: float | None = None

    def __post_init__(self) -> None:
        kind = str(self.kind).strip().lower().replace("_", "-")
        direction = str(self.direction or "none").strip().lower()
        if kind not in ACTION_KINDS:
            raise ValueError(f"Unsupported action kind {self.kind!r}; valid choices: {sorted(ACTION_KINDS)}")
        if self.frames is not None and int(self.frames) <= 0:
            raise ValueError("frames must be positive when provided")
        if kind == "static":
            direction = "none"
        elif kind in ROTATION_KINDS:
            valid = ROTATION_DIRECTIONS[kind]
            if direction not in valid:
                raise ValueError(f"Unsupported {kind} direction {direction!r}; valid choices: {sorted(valid)}")
            if self.degrees is None:
                raise ValueError(f"{kind} action requires degrees")
        elif kind in TRANSLATION_KINDS:
            valid = TRANSLATION_DIRECTIONS[kind]
            if direction not in valid:
                raise ValueError(f"Unsupported {kind} direction {direction!r}; valid choices: {sorted(valid)}")
            if self.amount is None:
                raise ValueError(f"{kind} action requires amount")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "direction", direction)
        if self.frames is not None:
            object.__setattr__(self, "frames", int(self.frames))

    def with_frames(self, frames: int) -> "FrameAction":
        return replace(self, frames=int(frames))


class CameraScript:
    """Builder for a sequence of frame-level camera actions."""

    def __init__(self, fps: int = 16, actions: list[FrameAction] | None = None) -> None:
        self.fps = int(fps)
        self.actions: list[FrameAction] = list(actions or [])

    @property
    def frame_count(self) -> int | None:
        total = 0
        for action in self.actions:
            if action.frames is None:
                return None
            total += int(action.frames)
        return total

    def extend(self, action: FrameAction) -> "CameraScript":
        self.actions.append(action)
        return self

    def static(self, frames: int | None = None) -> "CameraScript":
        return self.extend(FrameAction("static", frames=frames))

    def yaw(self, direction: str, *, degrees: float, frames: int | None = None) -> "CameraScript":
        return self.extend(FrameAction("yaw", direction, frames=frames, degrees=float(degrees)))

    def pitch(self, direction: str, *, degrees: float, frames: int | None = None) -> "CameraScript":
        return self.extend(FrameAction("pitch", direction, frames=frames, degrees=float(degrees)))

    def roll(self, direction: str, *, degrees: float, frames: int | None = None) -> "CameraScript":
        return self.extend(FrameAction("roll", direction, frames=frames, degrees=float(degrees)))

    def pan(self, direction: str, *, amount: float, frames: int | None = None) -> "CameraScript":
        return self.extend(FrameAction("pan", direction, frames=frames, amount=float(amount)))

    def dolly(self, direction: str, *, amount: float, frames: int | None = None) -> "CameraScript":
        return self.extend(FrameAction("dolly", direction, frames=frames, amount=float(amount)))

    def crane(self, direction: str, *, amount: float, frames: int | None = None) -> "CameraScript":
        return self.extend(FrameAction("crane", direction, frames=frames, amount=float(amount)))

    def to_string(self) -> str:
        parts = []
        for action in self.actions:
            suffix = f"@{action.frames}" if action.frames is not None else ""
            if action.kind == "static":
                parts.append(f"static{suffix}")
            elif action.kind in ROTATION_KINDS:
                parts.append(f"{action.kind}:{action.direction}:{action.degrees:g}{suffix}")
            else:
                parts.append(f"{action.kind}:{action.direction}:{action.amount:g}{suffix}")
        return ",".join(parts)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CameraScript) and self.fps == other.fps and self.actions == other.actions

    def __repr__(self) -> str:
        return f"CameraScript(fps={self.fps}, actions={self.to_string()!r})"


def parse_camera_script(text: str, *, fps: int = 16) -> CameraScript:
    """Parse the compact ``kind:direction:value@frames`` grammar into a script."""

    script = CameraScript(fps=fps)
    if not str(text).strip():
        raise ValueError("camera script must not be empty")
    for raw_part in str(text).split(","):
        part = raw_part.strip()
        if not part:
            continue
        body, sep, frame_text = part.partition("@")
        frames = int(frame_text) if sep else None
        fields = body.split(":")
        kind = fields[0].strip().lower()
        if kind == "static":
            if len(fields) != 1:
                raise ValueError("static action format is static@N")
            script.static(frames=frames)
            continue
        if len(fields) != 3:
            raise ValueError("camera action format is kind:direction:value@frames")
        direction, value = fields[1], float(fields[2])
        if kind in ROTATION_KINDS:
            getattr(script, kind)(direction, degrees=value, frames=frames)
        elif kind in TRANSLATION_KINDS:
            getattr(script, kind)(direction, amount=value, frames=frames)
        else:
            raise ValueError(f"Unsupported action kind {kind!r}")
    return script
