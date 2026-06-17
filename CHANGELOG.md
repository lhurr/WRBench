# Changelog

## 0.1.0 — 2026-06-17

### Added

- Backend dispatcher (`resolve_backend`) wired into `compile_camera` and CLI
  `--no-dry-run`.
- `LocalSubprocessBackend` with reference launchers for `easyanimate-v51-camera`
  and `spatia`.
- `wrcam.runtime.example.json` runtime configuration schema.
- `execution_contract` on `spatia` and documentation stub on `gen3c`.
- Backend docs under `docs/backends/`.
- Open-source verification script `scripts/oss_verify.sh`.
- Fairness verification wrapper `scripts/run_fairness_verification.sh`.

### Changed

- `.payload.json` is always written alongside sidecars (not dry-run only).
- EasyAnimate launcher now **materializes** `predict_v2v_control.py` (WRBench-style
  default patching) instead of passing ineffective CLI flags.
- `oss_verify.sh` fails hard on editable-install failure; selects Python ≥3.10
  explicitly.
- Cost table docs: removed private host references; added single-sample and
  `gpu_width` normalization caveats.

### Verified

- GPU `--no-dry-run` proof for `easyanimate-v51-camera` and `spatia` on reference
  host (see `docs/backends/README.md`).
- Full-model cost table refreshed (`docs/data/resource_profile_summary.all.*`).
- `hunyuan-game-craft` resource profile re-run with stage-accurate timing.
