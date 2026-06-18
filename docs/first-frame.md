# First-frame generation

`wrbench.firstframe` turns `t2i_scene` captions into PNG first frames for TI2V models.

## Quick start

```bash
# Mock provider (no API key, writes 1×1 PNG — good for dry-run)
wrbench firstframe --out first_frames/ --family-id demo --prompt "A cat on a bed." --provider mock

# Batch from families JSONL (uses t2i_scene field)
wrbench firstframe --out first_frames/ --families-jsonl families.jsonl --provider mock

# Real generation (DashScope)
pip install 'wrbench[firstframe]'
export DASHSCOPE_API_KEY=...
wrbench firstframe --out first_frames/ --families-jsonl families.jsonl --provider dashscope --model wan2.7-image-pro
```

Output layout:

```text
first_frames/
  bedroom_cat.png
  kitchen_dog.png
  first_frames_manifest.json
```

## Use with camera compile

```python
import wrbench

wrbench.compile_camera(
    model="wan22-fun-5b-cam",
    camera="preset:yaw_LR",
    image="first_frames/bedroom_cat.png",
    out="out.mp4",
    prompt="Your ti2v_prompt here",
)
```

## Python API

```python
from wrbench.firstframe import generate_first_frame, MockT2IProvider

manifest = generate_first_frame(
    family_id="demo",
    prompt="A sunny garden with a cat.",
    out_dir="first_frames/",
    provider="mock",
)
print(manifest.image_path)
```

## Providers

| Provider | Env | Notes |
|---|---|---|
| `mock` | none | Test placeholder PNG |
| `dashscope` | `DASHSCOPE_API_KEY` | wan2.7-image-pro, etc. |

Set `WRBENCH_T2I_PROVIDER` and `WRBENCH_T2I_MODEL` to override defaults.

## Dependencies

```bash
pip install 'wrbench[firstframe]'   # httpx + pillow
```

Core `import wrbench` does not require these extras.
