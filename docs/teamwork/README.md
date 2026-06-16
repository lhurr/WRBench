# WRCam Teamwork Memory

Use this directory for cross-turn research, durable plans, and compact reports
for the `wrcam` package. It routes agents to evidence; it does not replace
`README.md`, registry JSON, tests, or adapter source as implementation truth.

## Read Order

1. `index.json` for active pointers.
2. `current.md` for the compact state digest.
3. Durable artifacts under `research/`, `plans/`, and `reports/` when indexed.

## Boundaries

- Do not store secrets, weights, or large media here.
- Do not treat artifact abstracts as proof that a model backend ran.
- Prefer registry JSON and pytest output before changing adapter claims.
