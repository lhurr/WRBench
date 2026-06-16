# recammaster

| Field | Value |
|---|---|
| Input | `source_video` |
| Adapter | `recammaster` |
| Payload type | `recammaster_relative_pose_embedding` |
| Default frames | `81` |
| Default fps | `16` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrcam generate --model recammaster --camera preset:yaw_LR --source-video source.mp4 --out out/recammaster.mp4
```

## Python

```python
import wrcam
wrcam.compile_camera(model="recammaster", camera="yaw:left:60@40,yaw:right:60@41", source_video='source.mp4', out="out/recammaster.mp4")
```

## Real generation

WRCam compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrcam.backends.GenerationBackend` (Phase 3 scaffold).
