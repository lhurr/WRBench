# sana-wm

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `sana_wm` |
| Payload type | `sana_wm_camera_npy` |
| Default frames | `129` |
| Default fps | `16` |
| Resolution | `1280x704` |

## Dry-run compile (out of the box)

```bash
wrcam generate --model sana-wm --camera preset:yaw_LR --image first.png --out out/sana-wm.mp4
```

## Python

```python
import wrcam
wrcam.compile_camera(model="sana-wm", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/sana-wm.mp4")
```

## Real generation

WRCam compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrcam.backends.GenerationBackend` (Phase 3 scaffold).
