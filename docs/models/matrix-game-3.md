# matrix-game-3

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `matrix_game_3` |
| Payload type | `matrix_game3_action_conditions` |
| Default frames | `497` |
| Default fps | `17` |
| Resolution | `1280x704` |

## Dry-run compile (out of the box)

```bash
wrcam generate --model matrix-game-3 --camera preset:yaw_LR --image first.png --out out/matrix-game-3.mp4
```

## Python

```python
import wrcam
wrcam.compile_camera(model="matrix-game-3", camera="yaw:left:60@40,yaw:right:60@41", image='first.png', out="out/matrix-game-3.mp4")
```

## Real generation

WRCam compiles the model-native payload and sidecars locally. Real video generation requires the model's own environment (weights, GPU, venv). See the upstream model repository and use the compiled `.payload.json` / sidecars as inputs.

Backend hook: `wrcam.backends.GenerationBackend` (Phase 3 scaffold).
