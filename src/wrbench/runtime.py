"""Load optional local runtime paths for real generation backends."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_FILENAMES = ("wrbench.runtime.json", "wrbench.runtime.local.json")


@dataclass(frozen=True)
class ModelRuntime:
    """Per-model execution paths resolved from ``wrbench.runtime.json``."""

    key: str
    python_bin: str | None = None
    repo_root: str | None = None
    model_path: str | None = None
    gpu_id: int = 0
    extra_paths: dict[str, str] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeConfig:
    schema_version: int
    models: dict[str, ModelRuntime]
    defaults: dict[str, Any] = field(default_factory=dict)

    def model(self, key: str) -> ModelRuntime | None:
        return self.models.get(key)


def _resolve_runtime_path(explicit: Path | None) -> Path | None:
    if explicit is not None:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None
    env_path = os.environ.get("WRBENCH_RUNTIME_CONFIG")
    if env_path:
        path = Path(env_path).expanduser()
        if path.is_file():
            return path
    for name in DEFAULT_RUNTIME_FILENAMES:
        candidate = Path.cwd() / name
        if candidate.is_file():
            return candidate
    return None


def load_runtime_config(path: Path | None = None) -> RuntimeConfig | None:
    resolved = _resolve_runtime_path(path)
    if resolved is None:
        return None
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    defaults = dict(payload.get("defaults") or {})
    models: dict[str, ModelRuntime] = {}
    for key, node in sorted((payload.get("models") or {}).items()):
        if not isinstance(node, dict):
            continue
        models[str(key)] = ModelRuntime(
            key=str(key),
            python_bin=node.get("python_bin"),
            repo_root=node.get("repo_root"),
            model_path=node.get("model_path"),
            gpu_id=int(node.get("gpu_id", defaults.get("gpu_id", 0))),
            extra_paths={str(k): str(v) for k, v in (node.get("extra_paths") or {}).items()},
            env={str(k): str(v) for k, v in (node.get("env") or {}).items()},
        )
    return RuntimeConfig(
        schema_version=int(payload.get("schema_version", 1)),
        models=models,
        defaults=defaults,
    )
