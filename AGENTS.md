# WRCam Project Instructions

## Scope

- Workspace root: `/Users/jinplu/Documents/WRCam`.
- Python package lives under `src/wrcam/`; run tests, packaging, and git from the
  repository root unless the user targets a specific artifact path.
- Default mode is dry-run camera compilation: sidecars and payloads only, no GPU
  or model weights unless the user explicitly opts into a backend.

## Teamwork And Platforms

- Portable workflow, evidence labels, dispatch, artifacts, and review gates come
  from installed Teamwork skills (`using-teamwork` and stage skills).
- Project Cursor delta: `CURSOR.md` (`Init Mode: cost-first`).
- Codex and Claude Code inherit global bootstrap policy from
  `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md`.
- Teamwork memory entrypoint: `docs/teamwork/README.md` and
  `docs/teamwork/index.json`. Do not inline volatile progress here.

## Evidence Sources

- `README.md` for install, CLI intent, grammar, and sidecar contract.
- `docs/camera-control.md` and `docs/adding-a-model.md` for control semantics
  and adapter registration.
- `src/wrcam/models/*.json` for model registry, gains, and capability flags.
- `src/wrcam/adapters/` and `tests/` for adapter behavior and verification.
- Treat README model lists as claims until confirmed against the registry JSON.

## Protected Boundaries

- Do not invent model keys, frame counts, image paths, or backend env values.
- Do not enable real generation backends or download weights without explicit
  user approval.
- Keep Apache 2.0 licensing intact; do not commit secrets or large media.

## Verification

```bash
pip install -e ".[dev]"
pytest
```

Use focused adapter or registry tests when changing one model surface.
