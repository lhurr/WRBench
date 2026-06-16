# hydra

| Field | Value |
|---|---|
| Input | `source_video` |
| Adapter | `hydra` |
| Payload type | `hydra_split_camera_json` |
| Default frames | `77` |
| Default fps | `15` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrcam generate --model hydra --camera preset:yaw_LR --source-video source.mp4 --out out/hydra.mp4
```

## Python

```python
import wrcam
wrcam.compile_camera(model="hydra", camera="yaw:left:60@40,yaw:right:60@41", source_video='source.mp4', out="out/hydra.mp4")
```

## Real generation

WRCam compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrcam.backends.GenerationBackend` (Phase 3 scaffold).
