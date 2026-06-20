# Natural-25 prompt suite

This directory ships the **Natural-25** scene/event prompt grid used by WRBench.

| File | Description |
| --- | --- |
| `scene_events_25x4.csv` | 25 scene families × 4 event axes (none / spatial / state / full) |
| `families.jsonl` | Scene-family metadata and prompt variants |
| `variants.jsonl` | Pre-generated deterministic TI2V prompt variants: 25 families × 4 event tiers × 4 camera gaps |
| `first_frames/` | Released Natural-25 PNG first frames, one per `family_id` |
| `first_frames_manifest.json` | First-frame paths and source `t2i_scene` prompts |

The bundled first frames and prompt variants are released with the WRBench
repository under the repository Apache-2.0 license, so the open-source
camera-compile examples can run without generating a T2I image first. You can
also regenerate first-frame PNGs per family via `wrbench firstframe` (optional
extra) or substitute images from your own T2I pipeline. Human annotation
verdicts are released separately from this repository.

## Hugging Face release

- WRBench release collection:
  <https://huggingface.co/collections/WRBench/wrbench-current-world-models-lack-a-persistent-state-core-6a365c717251293c9fc2cc26>
- Natural-25 dataset card and viewer:
  <https://huggingface.co/datasets/WRBench/wrbench-natural25>
- Benchmark videos generated from Natural-25:
  <https://huggingface.co/datasets/WRBench/wrbench-videos>
- WRBench leaderboard:
  <https://huggingface.co/spaces/WRBench/wrbench-leaderboard>
- Paper page:
  <https://huggingface.co/papers/2606.20545>
