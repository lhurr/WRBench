# Prompt generation

`wrbench.prompts` generates scene, task, and camera text prompts for benchmark runs.

## Camera text (stdlib, no extra deps)

Natural-language camera clauses and API-model assembly:

```python
from wrbench.prompts import preset_camera_text, assemble_ti2v_prompt, build_prompt_to_send

# Map wrbench preset → NL camera clause
text = preset_camera_text("yaw_LR", pronoun="she", offscreen_area="empty stone paving")

# Full TI2V prompt
prompt = assemble_ti2v_prompt(scene_start, event, "she", "empty floor", "yaw_LR")

# API model assembly (Hailuo vs copy-optimized)
api_prompt = build_prompt_to_send(base_prompt, "yaw_LR", model="hailuo-2.3")
```

```bash
wrbench prompt camera --preset yaw_LR --pronoun she --offscreen-area "empty floor"
wrbench prompt camera --model hailuo-2.3 --source-prompt "Scene. Action." --camera-motion yaw_LR
```

## Scene prompt (T2I / first-frame caption)

Requires `pip install 'wrbench[prompts]'` and an API key (`OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, or `WRBENCH_LLM_API_KEY`).

```python
from wrbench.prompts.scene import generate_t2i_scene

t2i_scene = generate_t2i_scene(family_dict, provider="dashscope", model="qwen-max")
```

```bash
wrbench prompt scene --family-json family.json --provider dashscope
```

System prompt templates live in `src/wrbench/prompts/templates/`.

## Task prompt (TI2V variants)

**Deterministic path** (no LLM): rebuild Natural-25 style variants from bundled data or custom inputs.

```bash
# Uses bundled Natural-25 data shipped inside the wrbench package by default
wrbench prompt task --deterministic --output variants.jsonl

# Or specify custom paths
wrbench prompt task --deterministic \
  --candidates-json candidates.json \
  --families-jsonl families.jsonl \
  --output variants.jsonl
```

**LLM path** (Python):

```python
from wrbench.prompts.task import generate_ti2v_variants_llm

variants = generate_ti2v_variants_llm(tier_variants, family, provider="dashscope")
```

## Providers

| Env var | Purpose |
|---|---|
| `WRBENCH_LLM_PROVIDER` | `openai` (default) or `dashscope` |
| `WRBENCH_LLM_MODEL` | Model name |
| `WRBENCH_LLM_API_KEY` | Override API key |
| `WRBENCH_LLM_BASE_URL` | OpenAI-compatible base URL |
