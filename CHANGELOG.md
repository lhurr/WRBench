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
