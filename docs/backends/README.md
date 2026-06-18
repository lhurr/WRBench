# Backends

WRBench compiles camera payloads and sidecars by default (`dry_run=True`). Real
video generation is optional and routes through a **backend**.

## Built-in backends

| Backend | Name | When used |
| --- | --- | --- |
| Compile-only | `dry_run` | Default; no GPU, no weights |
| Local subprocess | `local_subprocess` | When `wrbench.runtime.json` configures a supported model |

## Configure local subprocess generation

1. Copy [`wrbench.runtime.example.json`](../../wrbench.runtime.example.json) to
   `wrbench.runtime.json` (or set `WRBENCH_RUNTIME_CONFIG`).
2. Fill in `python_bin`, `repo_root`, and model-specific paths.
3. Run:

```bash
IMAGE="$(python - <<'PY'
from wrbench.datasets import natural25_first_frame_path
print(natural25_first_frame_path("bedroom_cat_bed_jump"))
PY
)"

wrbench generate \
  --model easyanimate-v51-camera \
  --camera preset:yaw_LR \
  --image "$IMAGE" \
  --prompt "A living room." \
  --out out.mp4 \
  --no-dry-run
```

## Reference models (v0.1)

| Model | Kind | Backend support |
| --- | --- | --- |
| `easyanimate-v51-camera` | TI2V | `local_subprocess` (EasyAnimate `predict_v2v_control.py`) |
| `spatia` | V2V | `local_subprocess` (Spatia `inference.py`) |
| `gen3c` | V2V | Documented `execution_contract`; backend planned (ViPE + in-process pipeline) |

### EasyAnimate notes

- Uses **script materialization** (patch top-level defaults in
  `predict_v2v_control.py`); CLI flags alone are not sufficient.
- Set `PYTHONPATH` to the EasyAnimate repo root and use the model-dedicated venv.
- Disable teacache via `extra_paths.enable_teacache: "false"` when `flash-attn`
  is unavailable.

### Spatia notes

- Requires **absolute** `--out` paths (subprocess cwd is the Spatia repo).
- Install `opencv-python-headless` in the WRBench venv when `ffmpeg` is not on `PATH`.

## `execution_contract` schema

Each model JSON may include an inline `execution_contract` (see
`easyanimate-v51-camera.json`, `spatia.json`). Contract-driven adapters use it
at compile time; backends use runtime paths to launch the upstream entrypoint.

Required runtime fields per model entry in `wrbench.runtime.json`:

- `python_bin` — venv Python for the upstream repo
- `repo_root` — upstream repository root (cwd for subprocess)
- `model_path` — weights/checkpoint root (TI2V models)
- `extra_paths` — model-specific artifacts (e.g. Spatia `vace_path`, `lora_path`)
- `gpu_id` — `CUDA_VISIBLE_DEVICES` value

## Adding a backend

1. Implement `GenerationBackend` in `src/wrbench/backends/`.
2. Add a launcher under `src/wrbench/backends/launchers/` if subprocess-based.
3. Register the model key in `LocalSubprocessBackend._SUPPORTED_MODELS` (or a
   dedicated backend class).
4. Document runtime fields here and in `wrbench.runtime.example.json`.
5. Add tests under `tests/test_backends*.py`.

## Python API

```python
import wrbench
from wrbench.datasets import natural25_first_frame_path

result = wrbench.compile_camera(
    model="easyanimate-v51-camera",
    camera="preset:yaw_LR",
    image=natural25_first_frame_path("bedroom_cat_bed_jump"),
    out="out.mp4",
    prompt="A scene.",
    dry_run=False,  # requires wrbench.runtime.json
)
print(result["generation"])
```
