# hunyuanworld-voyager

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `hunyuanworld_voyager` |
| Payload type | `voyager_wrbench_rendered_camera_condition` |
| Default frames | `49` |
| Default fps | `24` |
| Resolution | `1280x720` |

## Dry-run compile (out of the box)

```bash
wrcam generate --model hunyuanworld-voyager --camera preset:yaw_LR --image first.png --out out/hunyuanworld-voyager.mp4
```

## Python

```python
import wrcam
wrcam.compile_camera(model="hunyuanworld-voyager", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/hunyuanworld-voyager.mp4")
```

## Real generation

WRCam compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrcam.backends.GenerationBackend` (Phase 3 scaffold).
