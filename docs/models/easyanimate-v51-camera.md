# easyanimate-v51-camera

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `easyanimate_v51_camera` |
| Payload type | `easyanimate_camera_txt` |
| Default frames | `49` |
| Default fps | `8` |
| Resolution | `672x384` |

## Dry-run compile (out of the box)

```bash
wrbench generate --model easyanimate-v51-camera --camera preset:yaw_LR --image first.png --out out/easyanimate-v51-camera.mp4
```

## Python

```python
import wrbench
wrbench.compile_camera(model="easyanimate-v51-camera", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/easyanimate-v51-camera.mp4")
```

## Real generation

WRBench compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrbench.backends.GenerationBackend` (Phase 3 scaffold).
