# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Adding a model

See [docs/adding-a-model.md](docs/adding-a-model.md).

## Adding a generation backend

See [docs/backends/README.md](docs/backends/README.md).

## Open-source gate

Before release, run:

```bash
bash scripts/oss_verify.sh
```

This checks for private-path leakage, runs the full test suite, and validates a
clean editable install.

## License

Contributions are accepted under the Apache-2.0 license.
