"""Generation backends (optional real inference)."""

from wrcam.backends.base import (
    DryRunBackend,
    GenerationBackend,
    GenerationRequest,
    GenerationResult,
    default_backend,
)
from wrcam.backends.local_subprocess import LocalSubprocessBackend
from wrcam.backends.registry import list_backends, resolve_backend

__all__ = [
    "DryRunBackend",
    "GenerationBackend",
    "GenerationRequest",
    "GenerationResult",
    "LocalSubprocessBackend",
    "default_backend",
    "list_backends",
    "resolve_backend",
]
