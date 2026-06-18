"""Generation backends (optional real inference)."""

from wrbench.backends.base import (
    DryRunBackend,
    GenerationBackend,
    GenerationRequest,
    GenerationResult,
    default_backend,
)
from wrbench.backends.local_subprocess import LocalSubprocessBackend
from wrbench.backends.registry import list_backends, resolve_backend

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
