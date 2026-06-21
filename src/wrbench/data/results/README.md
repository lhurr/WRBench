# Published WRBench results (23 models)

Paper-facing diagnostic profile for the 23 evaluated models in the WRBench benchmark run.

| File | Description |
| --- | --- |
| `wrbench_23model_results.csv` | Main table columns: identity + `viewpoint_condition_type`, `model_input`, D1-CamPrec, D1-CamAlign, D2, D3–D6, gate rate |
| `wrbench_23model_results.json` | Same data in JSON (frozen legacy-pronoun prompt run) |
| `wrbench_t2v_results.json` | T2V-only intake/benchmark addendum, currently including minWM Wan Action2V; separate from the frozen 23-model main table |

These are **reference results** from the paper; reproduce fresh scores with
`wrbench eval run` on your own generated videos.

## Columns

Identity / grouping columns (before the numeric metrics):

| Column | Status | Meaning |
| --- | --- | --- |
| `model_id` | current | Canonical model key (matches the row order; do not reorder). |
| `display_name` | current | Human-readable model name. |
| `viewpoint_condition_type` | current | **Paper viewpoint condition type** (Table 2): `source-video`, `geometry-cache`, `model-inferred`, or `prompt-only` — see below. |
| `model_input` | current | **Model input modality**, one of `{T2V, TI2V, TV2V}` — see below. |
| `paper_group` | **deprecated** | Legacy grouping (`V2V` / `Camera` / `Interactive` / `API prompt-camera`). No longer used by the paper. |
| `source_group` | **deprecated** | Legacy provenance bucket (`local_deployed` / `api_prompt_camera`). |

The remaining columns are the diagnostic metrics (`D1_CamPrec`, `D1_CamAlign_*`,
`D2`, `D3`–`D6`, their `_n` counts, `gate_applicable_rate`, `low_n_flag`,
`metric_notes`, `Avg`) and are unchanged from the published release.

### `viewpoint_condition_type` (paper grouping)

`viewpoint_condition_type` is the **primary grouping axis** in the paper main
table (Table 2). It records the form of input that supplies information about
the requested viewpoint change:

| Value | Meaning | Example models |
| --- | --- | --- |
| `source-video` | A reference stream supplies appearance, layout, and partial event evidence | ReCamMaster, HyDRA, InSpatio World 14B |
| `geometry-cache` | A point cloud / 3D / 4D record makes camera-target access computable | Gen3C, Spatia, VerseCrafter |
| `model-inferred` | No external view-state reference; the new view is synthesized under local camera/action/state controls | Wan-Fun, LingBot, LiveWorld, Hunyuan GameCraft/WorldPlay, MagicWorld |
| `prompt-only` | Natural-language camera intent only (CamAlign, not strict CamPrec) | Hailuo, HappyHorse, Kling, Wan I2V APIs |

Values are derived from the canonical mapping in
`wrbench.eval.aggregate.build_wrbench_vnext_main_table.VIEWPOINT_CONDITION_BY_MODEL`.
Best/second-best marks in the paper are computed **within** each condition type,
not across the full table.

### `model_input` (input modality)

`model_input` records the **form of input each model consumes**, independent of
how it delivers the viewpoint change:

| Value | Meaning | Source rule |
| --- | --- | --- |
| `T2V` | Text-to-video (prompt only, no first frame, no source video) | registry `input_kind: none` |
| `TI2V` | Text + first-frame **image** to video | registry `input_kind: image`; API prompt-camera rows run with first-frame I2V anchoring |
| `TV2V` | Text + **source/reference video** to video | registry `input_kind: source_video` |

Values are derived from the single-source-of-truth model registry
(`wrbench/registry.py` / `wrbench/models/<key>.json` `input_kind`). API
prompt-camera rows have no local registry record and are classified by their
first-frame image-to-video input contract (`TI2V`). No `T2V` model appears in
this frozen 23-model table; the separate T2V intake table lives in
`wrbench_t2v_results.json`.

`model_input` is **orthogonal** to viewpoint grouping. For example Gen3C,
Spatia, InSpatio World, Hydra, ReCamMaster and LiveWorld are `TV2V` (they
consume a source video), while VerseCrafter is `TI2V` (image input) even though
it was historically filed under the deprecated `V2V` label.

### Deprecated grouping → current grouping

`paper_group` / `source_group` are **kept only to reproduce this frozen
artifact** and should not be used for new analysis. Use `viewpoint_condition_type`
for paper-aligned grouping and `model_input` for the benchmark input interface.
The live table builder (`wrbench.eval.aggregate.build_wrbench_vnext_main_table`)
emits the same `viewpoint_condition_type` values.

## Prompt-of-record (frozen)

The published 23-model table was produced with the **legacy pronoun-anchored**
Natural-25 prompts (event sentences used `He`/`She`/`It`, relying on first-frame
subject anchoring for I2V models). That prompt set is frozen in:

`src/wrbench/data/natural25/variants.legacy_pronoun_20260620.jsonl`

The bundled active prompt file `variants.jsonl` remains the TI2V/TV2V prompt
of record and preserves the pronoun-anchored event wording used by the released
main table. Prompt-only T2V runs must materialize an explicit prompt profile,
such as `t2v_layout_anchor`, so the initial subject/interactor/open-surface
layout is present without copying T2I style wording. The legacy snapshot is kept
to reproduce the published table numbers byte-for-byte.

## T2V addendum

`wrbench_t2v_results.json` tracks text-to-video camera-control models that do
not consume a first frame or source video. These rows use a separate prompt
profile, camera rotation scope, and leaderboard policy because prompt-only T2V
models are not directly comparable to the paper's TI2V/TV2V and API I2V rows.

Current public addendum:

| Model | Status | Public scope |
| --- | --- | --- |
| `minwm-wan-action2v` | generation complete; static/yaw smoke scored | T2V-only Natural-25 addendum, separate from the frozen 23-model table |

Interpretation notes:

- T2V rows use `model_input: T2V`. `minwm-wan-action2v` keeps the existing
  `viewpoint_condition_type: model-inferred` grouping and records its native
  camera-token interface as `control_condition_type: prompt-plus-trajectory`.
- New prompt-only Natural-25 promotion runs must record `prompt_profile_id` and
  the materialized `generation_prompt`; `ti2v_prompt` remains the source prompt
  of record for first-frame-anchored runs.
- The formal rotation-stress scope covers 100 active Natural-25 variants across
  `static`, `yaw30_LR`, `yaw30_RL`, `yaw60_LR`, and `yaw60_RL`, using
  `src/wrbench/data/natural25/camera_scopes/t2v_rotation_stress_30_60.json`.
- The current T2V addendum is a no-OoV scope, so D5/D6 are null rather than
  failed scores.
- D1-CamAlign is reported as a camera-response diagnostic for static/yaw
  probes. D1-CamPrec is not promoted until the T2V target-certification policy
  is finalized.

## Hugging Face release

- WRBench release collection:
  <https://huggingface.co/collections/WRBench/wrbench-current-world-models-lack-a-persistent-state-core-6a365c717251293c9fc2cc26>
- Published model scores:
  <https://huggingface.co/datasets/WRBench/wrbench-results>
- Interactive leaderboard:
  <https://huggingface.co/spaces/WRBench/wrbench-leaderboard>
- Per-video scores and videos:
  <https://huggingface.co/datasets/WRBench/wrbench-videos>
- Human annotation verdicts:
  <https://huggingface.co/datasets/WRBench/wrbench-human-annotations>
- Paper page:
  <https://huggingface.co/papers/2606.20545>
