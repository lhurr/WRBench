# WRCam Examples

Equivalent CLI commands for the three actions shown in `quickstart.py`.

---

## (a) List supported models

```bash
# Plain table (active models only)
wrcam models

# Include deferred models
wrcam models --deferred

# Full JSON output
wrcam models --json
```

---

## (b) Compile the `yaw_LR` preset for `wan22-fun-5b-cam`

```bash
wrcam generate \
  --model wan22-fun-5b-cam \
  --camera preset:yaw_LR \
  --image first.png \
  --out /tmp/wrcam_demo/yaw_lr_demo.mp4

# With custom peak angle and frame count:
wrcam generate \
  --model wan22-fun-5b-cam \
  --camera preset:yaw_LR \
  --peak-deg 45 \
  --frames 81 \
  --image first.png \
  --out /tmp/wrcam_demo/yaw_lr_demo.mp4
```

---

## (c) Compile an arbitrary sweep script

```bash
# Using the raw script grammar directly:
wrcam generate \
  --model wan22-fun-5b-cam \
  --camera "yaw:left:37@49" \
  --image first.png \
  --out /tmp/wrcam_demo/sweep_demo.mp4

# Inspect / validate the script before generating:
wrcam actions --camera "yaw:left:37@49"
```

---

## Other useful commands

```bash
# List preset names with default expansion
wrcam presets

# Validate registry and adapter wiring for all models
wrcam doctor --all

# Validate a specific model
wrcam doctor --model wan22-fun-5b-cam
```
