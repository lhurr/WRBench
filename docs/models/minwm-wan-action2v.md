# minwm-wan-action2v

| Field | Value |
|---|---|
| Input | `image` |
| Adapter | `minwm_wan_action2v` |
| Payload type | `minwm_wan_action2v_trajectory_json` |
| Default frames | `77` |
| Default fps | `16` |
| Resolution | `832x480` |
| Backbone | Wan 2.1 (T2V-1.3B), Action2V DMD 4-step |

minWM's Wan 2.1 backbone variant. Shares the native motion-token camera mapping
with [`minwm-hy-action2v`](minwm-hy-action2v.md); only the execution contract differs
(`Wan21/wan_inference.py`, config + checkpoint + `--trajectory_path` driven).

## Dry-run compile (out of the box)

```bash
IMAGE="$(python - <<'PY2'
from wrbench.datasets import natural25_first_frame_path
print(natural25_first_frame_path("bedroom_cat_bed_jump"))
PY2
)"

wrbench generate --model minwm-wan-action2v --camera preset:yaw_LR --image "$IMAGE" --out out/minwm-wan-action2v.mp4
```

## Python

```python
import wrbench
from wrbench.datasets import natural25_first_frame_path

wrbench.compile_camera(model="minwm-wan-action2v", camera="yaw:left:60@40,yaw:right:60@41", image=natural25_first_frame_path("bedroom_cat_bed_jump"), out="out/minwm-wan-action2v.mp4")
```

## Real generation

WRBench compiles the model-native payload and sidecars locally. Real video generation
requires the model's own environment (weights, GPU, venv). See the upstream minWM
repository (`Wan21/scripts/inference/run_infer_causal_camera.sh`) and use the compiled
`.payload.json` / `minwm_wan_action2v_run_request.json` sidecars as inputs.

Backend hook: `wrbench.backends.GenerationBackend` (Phase 3 scaffold).
