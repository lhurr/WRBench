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
wrbench generate --model hydra --camera preset:yaw_LR --source-video source.mp4 --out out/hydra.mp4
```

## Python

```python
import wrbench
wrbench.compile_camera(model="hydra", camera="yaw:left:60@40,yaw:right:60@41", source_video='source.mp4', out="out/hydra.mp4")
```

## Real generation

WRBench compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Use `wrbench doctor --model hydra` to inspect the current backend status and required runtime fields.
