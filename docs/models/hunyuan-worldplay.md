# hunyuan-worldplay

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `hunyuan` |
| Payload type | `hunyuan_worldplay_pose_dict` |
| Default frames | `81` |
| Default fps | `16` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrcam generate --model hunyuan-worldplay --camera preset:yaw_LR --image first.png --out out/hunyuan-worldplay.mp4
```

## Python

```python
import wrcam
wrcam.compile_camera(model="hunyuan-worldplay", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/hunyuan-worldplay.mp4")
```

## Real generation

WRCam compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrcam.backends.GenerationBackend` (Phase 3 scaffold).
