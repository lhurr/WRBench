# lingbot-world

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `lingbot` |
| Payload type | `lingbot_pose_arrays` |
| Default frames | `81` |
| Default fps | `16` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrbench generate --model lingbot-world --camera preset:yaw_LR --image first.png --out out/lingbot-world.mp4
```

## Python

```python
import wrbench
wrbench.compile_camera(model="lingbot-world", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/lingbot-world.mp4")
```

## Real generation

WRBench compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrbench.backends.GenerationBackend` (Phase 3 scaffold).
