# hyworld-worldgen

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `hyworld_worldgen` |
| Payload type | `hyworld_worldgen_camera_json` |
| Default frames | `81` |
| Default fps | `16` |
| Resolution | `832x480` |

## Dry-run compile (out of the box)

```bash
wrcam generate --model hyworld-worldgen --camera preset:yaw_LR --image first.png --out out/hyworld-worldgen.mp4
```

## Python

```python
import wrcam
wrcam.compile_camera(model="hyworld-worldgen", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/hyworld-worldgen.mp4")
```

## Real generation

WRCam compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrcam.backends.GenerationBackend` (Phase 3 scaffold).
