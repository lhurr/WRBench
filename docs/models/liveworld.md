# liveworld

| Field | Value |
|---|---|
| Input | `source_video` |
| Adapter | `liveworld` |
| Payload type | `liveworld_geometry_npz` |
| Default frames | `81` |
| Default fps | `16` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrbench generate --model liveworld --camera preset:yaw_LR --source-video source.mp4 --out out/liveworld.mp4
```

## Python

```python
import wrbench
wrbench.compile_camera(model="liveworld", camera="yaw:left:60@40,yaw:right:60@41", source_video='source.mp4', out="out/liveworld.mp4")
```

## Real generation

WRBench compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Use `wrbench doctor --model liveworld` to inspect the current backend status and required runtime fields.
