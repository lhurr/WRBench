# Backends

WRCam compiles camera payloads and sidecars by default (`dry_run=True`). Real
video generation is optional and routes through a **backend**.

## Built-in backends

| Backend | Name | When used |
| --- | --- | --- |
| Compile-only | `dry_run` | Default; no GPU, no weights |
| Local subprocess | `local_subprocess` | When `wrcam.runtime.json` configures a supported model |

## Configure local subprocess generation

1. Copy [`wrcam.runtime.example.json`](../../wrcam.runtime.example.json) to
   `wrcam.runtime.json` (or set `WRCAM_RUNTIME_CONFIG`).
2. Fill in `python_bin`, `repo_root`, and model-specific paths.
3. Run:

```bash
wrcam generate \
  --model easyanimate-v51-camera \
  --camera preset:yaw_LR \
  --image first.png \
  --prompt "A living room." \
  --out out.mp4 \
  --no-dry-run
```

## GPU proof (2026-06-17)

End-to-end `--no-dry-run` validation on a reference GPU host (A800, dedicated model
venvs + `wrcam.runtime.json`):

| Model | Command | Result |
| --- | --- | --- |
| `easyanimate-v51-camera` | `wrcam generate --model easyanimate-v51-camera --camera preset:yaw_LR --peak-deg 30 --image <first_frame.png> --prompt "<scene>" --width 672 --height 384 --fps 8 --frames 49 --out easyanimate_yaw30.mp4 --no-dry-run` | **OK** — materialized `predict_v2v_control.py` + output mp4 (~401 KB) |
| `spatia` | `wrcam generate --model spatia --camera preset:yaw_LR --peak-deg 30 --source-video <source.mp4> --prompt "<scene>" --width 1248 --height 704 --fps 24 --frames 121 --out spatia_yaw30.mp4 --no-dry-run` | **OK** — Spatia `inference.py` + output mp4 (~449 KB) |

Notes:

- EasyAnimate uses **WRBench-style script materialization** (patch top-level defaults in
  `predict_v2v_control.py`); CLI flags alone are not sufficient.
- Set `PYTHONPATH` to the EasyAnimate repo root and prefer the model-dedicated venv
  (`easyanimate_v51_camera`); disable teacache via `extra_paths.enable_teacache: "false"`
  when `flash-attn` is unavailable.
- Spatia requires **absolute** `--out` paths (subprocess cwd is the Spatia repo).
- Install `opencv-python-headless` in the WRCam venv when `ffmpeg` is not on `PATH`.

## Reference models (v0.1)

| Model | Kind | Backend support |
| --- | --- | --- |
| `easyanimate-v51-camera` | TI2V | `local_subprocess` (EasyAnimate `predict_v2v_control.py`) |
| `spatia` | V2V | `local_subprocess` (Spatia `inference.py`) |
| `gen3c` | V2V | Documented `execution_contract`; backend planned (ViPE + in-process pipeline) |

## `execution_contract` schema

Each model JSON may include an inline `execution_contract` (see
`easyanimate-v51-camera.json`, `spatia.json`). Contract-driven adapters use it
at compile time; backends use runtime paths to launch the upstream entrypoint.

Required runtime fields per model entry in `wrcam.runtime.json`:

- `python_bin` — venv Python for the upstream repo
- `repo_root` — upstream repository root (cwd for subprocess)
- `model_path` — weights/checkpoint root (TI2V models)
- `extra_paths` — model-specific artifacts (e.g. Spatia `vace_path`, `lora_path`)
- `gpu_id` — `CUDA_VISIBLE_DEVICES` value

## Adding a backend

1. Implement `GenerationBackend` in `src/wrcam/backends/`.
2. Add a launcher under `src/wrcam/backends/launchers/` if subprocess-based.
3. Register the model key in `LocalSubprocessBackend._SUPPORTED_MODELS` (or a
   dedicated backend class).
4. Document runtime fields here and in `wrcam.runtime.example.json`.
5. Add tests under `tests/test_backends*.py`.

## Python API

```python
import wrcam

result = wrcam.compile_camera(
    model="easyanimate-v51-camera",
    camera="preset:yaw_LR",
    image="first.png",
    out="out.mp4",
    prompt="A scene.",
    dry_run=False,  # requires wrcam.runtime.json
)
print(result["generation"])
```
