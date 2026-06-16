# Camera-Control Grammar and Pipeline

Reference documentation for the `wrcam` frame-action camera grammar, the three-layer compilation pipeline, and amplitude calibration.

---

## Frame-action grammar

### Compact string format

The grammar is a comma-separated list of **action segments**:

```
kind:direction:value@frames[,kind:direction:value@frames,...]
```

Each segment covers a contiguous block of frames and expresses one camera intent. The full string is passed directly to `wrcam.compile_camera(camera=...)` or to `wrcam.parse_camera_script(...)`.

### Action kinds and valid directions

| Kind | Type | Valid directions | Value field | Notes |
|---|---|---|---|---|
| `yaw` | rotation | `left`, `right` | `degrees` (any float) | Horizontal pan around vertical axis |
| `pitch` | rotation | `up`, `down` | `degrees` (any float) | Tilt up or down |
| `roll` | rotation | `left`, `right`, `cw`, `ccw` | `degrees` (any float) | Rotate around optical axis |
| `pan` | translation | `left`, `right` | `amount` (any float) | Lateral slide |
| `dolly` | translation | `forward`, `back`, `backward` | `amount` (any float) | Push in or pull out along viewing axis |
| `crane` | translation | `up`, `down` | `amount` (any float) | Vertical lift |
| `static` | — | *(none)* | *(none)* | Hold the camera still |

### `@frames` semantics

The `@frames` suffix sets the number of frames this segment covers. It is optional for a single-segment script when `num_frames` is supplied to `compile_camera`; for multi-segment scripts each segment should carry its own `@frames` so the total is unambiguous.

**Segment frame counts are additive.** A script with two segments of 40 and 41 frames produces 81 total frames.

### Static format

`static` takes no direction or value:

```
static@81
```

### Rotation format

```
yaw:left:60@40
pitch:down:15@25
roll:cw:10@20
```

### Translation format

```
pan:left:0.5@40
dolly:forward:1.0@81
crane:up:0.3@30
```

---

## Worked examples

### 1. 60-degree go-return yaw over 81 frames

```
yaw:left:60@40,yaw:right:60@41
```

The camera yaws 60° left across 40 frames, then yaws 60° right across 41 frames, returning close to the original pose. This is equivalent to `wrcam.presets.yaw_LR(peak_deg=60, frames=81)`.

In Python:

```python
import wrcam

result = wrcam.compile_camera(
    model="wan22-fun-5b-cam",
    camera="yaw:left:60@40,yaw:right:60@41",
    image="first.png",
    out="out.mp4",
)
```

### 2. Arbitrary 37-degree one-way sweep

```
yaw:left:37@49
```

A one-directional yaw sweep of any angle. Using the preset builder:

```python
script = wrcam.presets.sweep("yaw", "left", 37, frames=49)
result = wrcam.compile_camera(
    model="wan22-fun-5b-cam",
    camera=script,
    image="first.png",
    out="out.mp4",
)
```

`sweep` works for all rotation and translation kinds:

```python
wrcam.presets.sweep("pan", "right", 0.4, frames=49)
wrcam.presets.sweep("dolly", "forward", 1.0, frames=49)
```

### 3. Pan go-return

```
pan:left:0.5@40,pan:right:0.5@41
```

Slides the camera left for 40 frames then back right for 41 frames. Equivalent to `wrcam.presets.pan_LR(amount=0.5, frames=81)`.

### 4. Multi-segment composite: yaw left, hold, pan right

```
yaw:left:60@27,static@27,pan:right:0.5@27
```

Three segments of 27 frames each, totalling 81 frames. The camera yaws left, holds still, then pans right. Composed in Python:

```python
from wrcam.actions import CameraScript

script = (
    CameraScript()
    .yaw("left", degrees=60, frames=27)
    .static(frames=27)
    .pan("right", amount=0.5, frames=27)
)
result = wrcam.compile_camera(
    model="wan22-fun-5b-cam",
    camera=script,
    image="first.png",
    out="out.mp4",
)
```

---

## Go-return semantics

Go-return presets (`yaw_LR`, `yaw_RL`, `pan_LR`, `pan_RL`) divide the total frame budget into two halves using:

```
half = max(1, frames // 2)
rest = max(1, frames - half)
```

For `frames=81`: `half=40`, `rest=41`. The first segment goes in the primary direction; the second returns in the opposite direction with the same value, so the pose at the end is close to the starting pose. Frame counts are integers, so for odd totals the return leg gets one extra frame.

Use `wrcam.presets.go_return(kind, first_direction, second_direction, value, frames)` for a generic go-return on any rotation or translation kind:

```python
# Pitch down then up
wrcam.presets.go_return("pitch", "down", "up", 20.0, frames=81)

# Dolly forward then back
wrcam.presets.go_return("dolly", "forward", "back", 1.0, frames=81)
```

---

## Three-layer contract

wrcam compiles camera control through three named layers:

### Layer 1 — `frame_action_script`

The compact string or `CameraScript` object. This is the benchmark / researcher intent: "yaw left 60° for 40 frames, then return 60° right for 41 frames". It is model-agnostic.

### Layer 2 — `target_c2w` (OpenCV C2W)

The builder converts the action sequence into a smooth OpenCV camera-to-world (C2W) matrix trajectory, shape `(F, 4, 4)`. This is the evaluation / sidecar trajectory: the `.target_c2w.npy` sidecar records exactly this array. All adapters receive this representation, so the same trajectory can be re-inspected or re-used regardless of which model was targeted.

### Layer 3 — `model_control_timeline`

The adapter translates the C2W trajectory into the model's native control representation and records it in `model_control_timeline` inside `.model_control_samples.json`. **Unified does not mean every model consumes per-frame action tokens.** Depending on the model, the native representation may be:

- **Pose matrices** — per-frame W2C or C2W rows (e.g. Wan Fun CameraCtrl pose text)
- **Latent pose embeddings** — e.g. 21 relative poses for sparse models
- **Geometry NPZ** — Blender C2W scene geometry
- **Action tokens** — numeric action segments
- **Pose text / JSONL** — per-frame JSON rows

Dense models have one control sample per target frame; sparse models may control every few frames. The `model_control_samples.json` sidecar records `control_sample_count`, `payload_type`, and `target_frame_count` so the mapping is always auditable.

---

## Amplitude and calibration

Each model has an `amplitude` block in its registry JSON that scales the model-agnostic motion into the model's native coordinate range:

| Field | Type | Meaning |
|---|---|---|
| `rotation_gain` | float | Multiplier applied to relative rotation in the resampled C2W trajectory |
| `translation_gain` | float | Multiplier applied to translation components in the resampled C2W trajectory |
| `max_amount` | float | Soft ceiling on translated distance in the model's coordinate space |
| `translation_unit` | string | Coordinate space identifier (e.g. `canonical_scene`, `cameractrl_scene`) |
| `calibration_status` | string | How the gains were determined (e.g. `initial_manual`, `uncalibrated`) |

These values are applied during `compile_camera` inside the adapter via `model_target_trajectory`. You can inspect them with:

```python
record = wrcam.model_record("wan22-fun-5b-cam")
print(record.amplitude)
```

Valid `translation_unit` values are defined in `registry.py` (`VALID_TRANSLATION_UNITS`). Adapters may interpret the translation unit to pick the correct coordinate conversion path.
