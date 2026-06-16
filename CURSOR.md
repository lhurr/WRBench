# WRCam Cursor Usage

Teamwork augments Cursor native tools. Portable workflow lives in installed
Teamwork skills; this file records WRCam-local Cursor deltas only.

## Project Entry

1. `AGENTS.md` for scope, dry-run default, evidence sources, and boundaries.
2. `docs/teamwork/index.json` and `docs/teamwork/current.md` for Teamwork
   routing when durable memory is relevant.
3. `README.md` and `docs/` for camera grammar and adapter onboarding.

## Init Mode

`Init Mode: cost-first`.

- Routine Explorer, Designer, and Worker -> `composer-2.5-fast`
- Judge, Reviewer, and Deep variants -> `claude-opus-4-8-thinking-high`

Role mapping: `skills/using-teamwork/references/subagent-dispatch.md`.

## Teamwork Memory

Use `docs/teamwork/` for cross-turn research, plans, and reports when artifact
triggers apply. The registry JSON and tests remain implementation truth.

## Goal Mode

Cursor has no native goal surface. Use chat `Goal Proposal` plus rolling reports
under `docs/teamwork/reports/` per Teamwork `goal-iteration.md`.
