# First-frame generation

WRBench ships released Natural-25 PNG first frames and also provides
`wrbench.firstframe` for regenerating frames from `t2i_scene` captions.

## Quick start

Use the bundled Natural-25 first frames:

```python
from wrbench.datasets import natural25_first_frame_path, natural25_first_frames_manifest_path

image = natural25_first_frame_path("bedroom_cat_bed_jump")
manifest = natural25_first_frames_manifest_path()
print(image)
print(manifest)
```

Generate your own first frames with explicit provider settings:

```bash
# Mock provider (writes a 1×1 placeholder PNG)
wrbench firstframe --out first_frames/ --family-id demo --prompt "A cat on a bed." \
  --provider mock --model mock --endpoint mock://local --size 1024x1024 --n 1 \
  --overwrite-existing

# Batch from families JSONL (uses t2i_scene field)
wrbench firstframe --out first_frames/ --families-jsonl families.jsonl \
  --provider mock --model mock --endpoint mock://local --size 1024x1024 --n 1 \
  --overwrite-existing

# Real generation (DashScope)
pip install 'wrbench[firstframe]'
wrbench firstframe --out first_frames/ --families-jsonl families.jsonl \
  --provider dashscope --model wan2.7-image-pro \
  --api-key YOUR_API_KEY \
  --endpoint https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation \
  --size 1024*1024 --n 1 --overwrite-existing
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
from wrbench.datasets import natural25_first_frame_path

wrbench.compile_camera(
    model="wan22-fun-5b-cam",
    camera="preset:yaw_LR",
    image=natural25_first_frame_path("bedroom_cat_bed_jump"),
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
    model="mock",
    endpoint="mock://local",
    size="1024x1024",
    n=1,
)
print(manifest.image_path)
```

## Providers

| Provider | Explicit inputs | Notes |
|---|---|---|
| `mock` | `provider="mock"`, `model="mock"`, `endpoint="mock://local"`, `size`, `n` | Test placeholder PNG |
| `dashscope` | `provider="dashscope"`, `model`, `api_key`, `endpoint`, `size`, `n` | Real image generation |

## Dependencies

```bash
pip install 'wrbench[firstframe]'   # httpx + pillow
```

Core `import wrbench` does not require these extras.
