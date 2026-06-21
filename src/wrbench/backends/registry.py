"""Backend registry and resolution."""

from __future__ import annotations

from wrbench.backends.base import DryRunBackend, GenerationBackend
from wrbench.backends.local_subprocess import LocalSubprocessBackend
from wrbench.registry import canonical_model_key
from wrbench.runtime import RuntimeConfig, load_runtime_config


def resolve_backend(
    model: str,
    *,
    runtime: RuntimeConfig | None = None,
    backend_name: str | None = None,
) -> GenerationBackend:
    """Return the backend selected by explicit config and model support."""

    key = canonical_model_key(model)
    if backend_name in (None, "", "dry_run"):
        runtime = runtime if runtime is not None else load_runtime_config()
        if runtime is not None and runtime.model(key) is not None:
            return LocalSubprocessBackend(runtime)
        return DryRunBackend()
    if backend_name == "local_subprocess":
        runtime = runtime if runtime is not None else load_runtime_config()
        if runtime is None:
            raise RuntimeError("backend 'local_subprocess' requires an explicit wrbench.runtime.json")
        return LocalSubprocessBackend(runtime)
    raise ValueError(f"Unknown backend {backend_name!r}")


def list_backends(model: str, *, runtime: RuntimeConfig | None = None) -> list[tuple[str, bool, str]]:
    """Return ``(name, available, reason)`` tuples for *model*."""

    key = canonical_model_key(model)
    runtime = runtime if runtime is not None else load_runtime_config()
    rows: list[tuple[str, bool, str]] = []
    dry = DryRunBackend()
    ok, msg = dry.available()
    rows.append((dry.name, ok, msg))
    if runtime is not None:
        local = LocalSubprocessBackend(runtime)
        ok, msg = local.available_for(key)
        rows.append((local.name, ok, msg))
    else:
        rows.append(("local_subprocess", False, "explicit wrbench.runtime.json not provided"))
    return rows
