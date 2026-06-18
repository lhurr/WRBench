"""Single source of truth for supported models.

Each model is declared by exactly one JSON file in ``wrbench/models/<key>.json``.
That file carries everything the toolkit needs: canonical key, aliases, input
kind (image vs source video), adapter name, amplitude calibration, capabilities,
and status. This replaces the historical multi-file config chain (separate alias
map, contracts, capabilities, amplitude, shell lists, run specs) with one
authoritative record per model, validated on load.

Adding a model = drop one JSON here + one adapter module. ``wrbench doctor``
checks that the two agree.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


MODELS_DIR = Path(__file__).resolve().parent / "models"

VALID_INPUT_KINDS = {"image", "source_video"}

VALID_TRANSLATION_UNITS = {
    "canonical_scene",
    "cameractrl_scene",
    "blender_c2w_scene",
    "cache3d_scene",
    "relative_pose_embedding",
    "w2c_scene",
    "official_displacement_scale",
    "trajectory_template_c2w",
    "hydra_c2w_pre_div100",
}


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class CameraAmplitude:
    model_key: str
    rotation_gain: float
    translation_gain: float
    max_amount: float
    translation_unit: str
    calibration_status: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ModelRecord:
    key: str
    aliases: tuple[str, ...]
    status: str
    input_kind: str
    adapter: str
    payload_type: str
    amplitude: CameraAmplitude
    capabilities: dict[str, Any]
    notes: str
    default_width: int = 832
    default_height: int = 480
    default_frames: int = 81
    default_fps: int = 16
    execution_contract: dict[str, Any] | None = None

    @property
    def is_deferred(self) -> bool:
        return self.status == "deferred"


def _norm(name: str) -> str:
    return str(name).strip().lower().replace("_", "-")


def _parse_amplitude(key: str, record: dict[str, Any]) -> CameraAmplitude:
    amp = record.get("amplitude")
    if not isinstance(amp, dict):
        raise RegistryError(f"{key}: missing 'amplitude' object")
    unit = str(amp.get("translation_unit") or "")
    if unit not in VALID_TRANSLATION_UNITS:
        raise RegistryError(f"{key}: unsupported translation_unit {unit!r}")
    try:
        return CameraAmplitude(
            model_key=key,
            rotation_gain=float(amp.get("rotation_gain", 1.0)),
            translation_gain=float(amp["translation_gain"]),
            max_amount=float(amp["max_amount"]),
            translation_unit=unit,
            calibration_status=str(amp.get("calibration_status") or "uncalibrated"),
            metadata=dict(amp.get("metadata", {}) or {}),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RegistryError(f"{key}: invalid amplitude record: {exc}") from exc


def _parse_record(path: Path, payload: dict[str, Any]) -> ModelRecord:
    key = payload.get("key")
    if not isinstance(key, str) or not key:
        raise RegistryError(f"{path.name}: missing 'key'")
    status = str(payload.get("status") or "active")
    if status not in {"active", "deferred"}:
        raise RegistryError(f"{key}: status must be 'active' or 'deferred'")
    input_kind = str(payload.get("input_kind") or "")
    if status == "active" and input_kind not in VALID_INPUT_KINDS:
        raise RegistryError(f"{key}: input_kind must be one of {sorted(VALID_INPUT_KINDS)}")
    adapter = str(payload.get("adapter") or "")
    if status == "active" and not adapter:
        raise RegistryError(f"{key}: active model requires 'adapter'")
    aliases = tuple(dict.fromkeys([_norm(key)] + [_norm(a) for a in payload.get("aliases", []) or []]))
    amplitude = _parse_amplitude(key, payload) if status == "active" else CameraAmplitude(
        model_key=key,
        rotation_gain=1.0,
        translation_gain=1.0,
        max_amount=0.5,
        translation_unit="canonical_scene",
        calibration_status="deferred",
        metadata={},
    )
    execution_contract = payload.get("execution_contract")
    if execution_contract is not None and not isinstance(execution_contract, dict):
        raise RegistryError(f"{key}: execution_contract must be an object")
    return ModelRecord(
        key=key,
        aliases=aliases,
        status=status,
        input_kind=input_kind,
        adapter=adapter,
        payload_type=str(payload.get("payload_type") or ""),
        amplitude=amplitude,
        capabilities=dict(payload.get("capabilities", {}) or {}),
        notes=str(payload.get("notes") or ""),
        default_width=int(payload.get("default_width", 832)),
        default_height=int(payload.get("default_height", 480)),
        default_frames=int(payload.get("default_frames", 81)),
        default_fps=int(payload.get("default_fps", 16)),
        execution_contract=dict(execution_contract) if execution_contract else None,
    )


@lru_cache(maxsize=1)
def _load() -> tuple[dict[str, ModelRecord], dict[str, str]]:
    if not MODELS_DIR.exists():
        raise RegistryError(f"Missing models directory: {MODELS_DIR}")
    records: dict[str, ModelRecord] = {}
    alias_lookup: dict[str, str] = {}
    for path in sorted(MODELS_DIR.glob("*.json")):
        record = _parse_record(path, json.loads(path.read_text(encoding="utf-8")))
        if record.key in records:
            raise RegistryError(f"Duplicate model key: {record.key}")
        records[record.key] = record
        for alias in record.aliases:
            if alias in alias_lookup and alias_lookup[alias] != record.key:
                raise RegistryError(f"Alias collision {alias!r}: {alias_lookup[alias]} vs {record.key}")
            alias_lookup[alias] = record.key
    if not records:
        raise RegistryError(f"No model records found in {MODELS_DIR}")
    return records, alias_lookup


def reload() -> None:
    """Clear the cached registry (useful in tests after editing model files)."""
    _load.cache_clear()


def canonical_model_key(name: str) -> str:
    _, lookup = _load()
    key = _norm(name)
    if key in lookup:
        return lookup[key]
    raise KeyError(f"Unknown model key or alias: {name}")


def model_record(name: str) -> ModelRecord:
    records, _ = _load()
    return records[canonical_model_key(name)]


def all_records() -> list[ModelRecord]:
    records, _ = _load()
    return [records[k] for k in sorted(records)]


def active_model_keys() -> list[str]:
    return [r.key for r in all_records() if not r.is_deferred]


def deferred_model_keys() -> list[str]:
    return [r.key for r in all_records() if r.is_deferred]


def is_deferred_model(name: str) -> bool:
    return model_record(name).is_deferred


def input_kind(name: str) -> str:
    return model_record(name).input_kind


def adapter_name(name: str) -> str:
    return model_record(name).adapter


def resolve_model_amplitude(name: str) -> CameraAmplitude:
    return model_record(name).amplitude
