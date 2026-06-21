# Changelog

## Unreleased

### Added

- Separate Natural-25 T2V prompt profile for prompt-only models that do not
  receive a first-frame image.
- Legacy pronoun-anchored prompt snapshot:
  `src/wrbench/data/natural25/variants.legacy_pronoun_20260620.jsonl`.
- T2V rotation-stress camera scope:
  `src/wrbench/data/natural25/camera_scopes/t2v_rotation_stress_30_60.json`.
- T2V intake acceptance helpers (`wrbench.t2v`) for subject/scene/action/camera
  gates and minWM rotation-step calibration metadata.
- T2V results placeholder table:
  `src/wrbench/data/results/wrbench_t2v_results.json`.

### Changed

- Bundled `variants.jsonl` remains the TI2V/TV2V prompt-of-record. Prompt-only
  T2V models use the separate `t2v_layout_anchor` prompt profile and T2V event
  tails instead of mutating the main prompt file.
- Published 23-model results (`wrbench_23model_results.*`) are annotated as
  frozen legacy-pronoun prompt outputs; T2V addenda are maintained separately.
- README now links to `docs/eval/README.md` as the canonical public policy for
  re-observation scoring and prompt-only T2V scope; per-model pages point users
  to `wrbench doctor --model ...` instead of stale backend-status boilerplate.

## 0.1.0 — 2026-06-17

### Added

- D1 prompt-camera alignment (CamAlign) scorer: `wrbench eval d1-camalign` and `D1_camalign` contract/table column.
- Backend dispatcher (`resolve_backend`) wired into `compile_camera` and CLI `--no-dry-run`.
- `LocalSubprocessBackend` with reference launchers for `easyanimate-v51-camera` and `spatia`.
- `wrbench.runtime.example.json` runtime configuration schema.
- WRBench D1–D6 evaluation package (`wrbench eval`) with metric contract, scorers, and `wrbench eval run` one-command pipeline.
- Bundled Natural-25 prompts and published 23-model results in `src/wrbench/data/` (install-safe via package data).
- Backend docs under `docs/backends/`.
- Open-source verification script `scripts/oss_verify.sh`.
- CI workflow, `CODE_OF_CONDUCT.md`, and `SECURITY.md`.

### Changed

- `.payload.json` is always written alongside sidecars (not dry-run only).
- EasyAnimate launcher materializes `predict_v2v_control.py` instead of passing ineffective CLI flags.
- Public docs adopt WRBench paper terminology (diagnostic dimensions, viewpoint condition types, re-observation support).
- D3–D6 overlay scorers resolve the installed `wrbench.eval.scoring` package layout (no legacy metric tree required).

### Verified

- Editable install + full pytest suite on Python 3.10–3.12.
- `wrbench doctor`, dry-run `wrbench generate`, and `wrbench eval contract` work without a tracked runtime config file.
