# inspatio-world

| Field | Value |
|---|---|
| Input | `source_video` |
| Adapter | `inspatio` |
| Payload type | `inspatio_per_frame_action_txt` |
| Default frames | `81` |
| Default fps | `24` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrbench generate --model inspatio-world --camera preset:yaw_LR --source-video source.mp4 --out out/inspatio-world.mp4
```

## Python

```python
import wrbench
wrbench.compile_camera(model="inspatio-world", camera="yaw:left:60@40,yaw:right:60@41", source_video='source.mp4', out="out/inspatio-world.mp4")
```

## Real generation

WRBench compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrbench.backends.GenerationBackend` (Phase 3 scaffold).
