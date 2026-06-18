# wan21-fun-1p3b-cam

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `wan_fun` |
| Payload type | `wan_fun_pose_txt` |
| Default frames | `81` |
| Default fps | `16` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrbench generate --model wan21-fun-1p3b-cam --camera preset:yaw_LR --image first.png --out out/wan21-fun-1p3b-cam.mp4
```

## Python

```python
import wrbench
wrbench.compile_camera(model="wan21-fun-1p3b-cam", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/wan21-fun-1p3b-cam.mp4")
```

## Real generation

WRBench compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrbench.backends.GenerationBackend` (Phase 3 scaffold).
