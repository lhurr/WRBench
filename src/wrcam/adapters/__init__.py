"""Camera adapters. Importing this package registers every adapter."""

from __future__ import annotations

import importlib

from wrcam.adapters.base import (
    adapter_for_model,
    compile_camera_payload,
    register,
    register_adapter,
    registered_model_keys,
)

_ADAPTER_MODULES = [
    "wrcam.adapters.wan_fun",
    "wrcam.adapters.hunyuan",
    "wrcam.adapters.recammaster",
    "wrcam.adapters.magicworld",
    "wrcam.adapters.versecrafter",
    "wrcam.adapters.lingbot",
    "wrcam.adapters.liveworld",
    "wrcam.adapters.gen3c",
    "wrcam.adapters.sana_wm",
    "wrcam.adapters.easyanimate",
    "wrcam.adapters.minwm",
    "wrcam.adapters.hydra",
    "wrcam.adapters.spatia_inspatio",
    "wrcam.adapters.action_candidate",
]

for _module in _ADAPTER_MODULES:
    importlib.import_module(_module)

__all__ = [
    "adapter_for_model",
    "compile_camera_payload",
    "register",
    "register_adapter",
    "registered_model_keys",
]
