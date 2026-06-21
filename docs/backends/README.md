# Backends

WRBench can either compile camera payloads/sidecars (`dry_run=True`) or launch a
configured generation backend (`dry_run=False`).

## Built-in backends

| Backend | Name | When used |
| --- | --- | --- |
| Compile-only | `dry_run` | No GPU, no weights |
| Local subprocess | `local_subprocess` | Requires an explicit `wrbench.runtime.json` for a supported model |

## Configure local subprocess generation

1. Copy [`wrbench.runtime.example.json`](../../wrbench.runtime.example.json) to
   a local runtime config file.
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
  --runtime-config /path/to/wrbench.runtime.json \
  --no-dry-run
```

## Reference Models

| Model | Kind | Backend support |
| --- | --- | --- |
| `easyanimate-v51-camera` | TI2V | `local_subprocess` (EasyAnimate `predict_v2v_control.py`) |
| `spatia` | TV2V | `local_subprocess` (Spatia `inference.py`) |
| `gen3c` | TV2V | Documented `execution_contract`; backend planned (ViPE + in-process pipeline) |

### EasyAnimate notes

- Uses **script materialization** (patch top-level defaults in
  `predict_v2v_control.py`); CLI flags alone are not sufficient.
- Set `PYTHONPATH` to the EasyAnimate repo root and use the model-dedicated venv.
- Disable teacache via `extra_paths.enable_teacache: "false"` when `flash-attn`
  is unavailable.

### Spatia notes

- Requires **absolute** `--out` paths (subprocess cwd is the Spatia repo).
- Configure `extra_paths.ffmpeg_bin` in `wrbench.runtime.json`; Spatia frame
  extraction does not fall back to ambient `PATH` tools.

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
