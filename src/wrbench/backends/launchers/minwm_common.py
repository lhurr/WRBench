"""Shared helpers for minWM subprocess launchers."""

from __future__ import annotations

from pathlib import Path

from wrbench.runtime import ModelRuntime


def runtime_value(runtime: ModelRuntime, key: str) -> str:
    value = runtime.extra_paths.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"{runtime.key}: runtime.extra_paths.{key} is required")
    return str(value)


def torchrun_bin(runtime: ModelRuntime) -> Path:
    return Path(runtime_value(runtime, "torchrun_bin"))


def torchrun_command(runtime: ModelRuntime) -> list[str]:
    return [str(torchrun_bin(runtime))]


def prepare_output_dir(output_path: Path, suffix: str) -> Path:
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir = Path(str(output_path.with_suffix("")) + suffix)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def expected_output(output_dir: Path, *, recursive: bool) -> Path | None:
    paths = output_dir.rglob("*.mp4") if recursive else output_dir.glob("*.mp4")
    mp4s = sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0] if mp4s else None


def runtime_env(runtime: ModelRuntime, *, pythonpath_entries: list[Path]) -> dict[str, str]:
    env = dict(runtime.env)
    env["CUDA_VISIBLE_DEVICES"] = str(runtime.gpu_id)
    env["PYTHONUNBUFFERED"] = "1"
    prefix = ":".join(str(entry) for entry in pythonpath_entries)
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = f"{prefix}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = prefix
    return env


def runtime_missing_fields(
    runtime: ModelRuntime,
    *,
    model_path_kind: str | None,
    entrypoint_rel: str,
    required_extra_paths: tuple[str, ...] = (),
    existing_extra_paths: tuple[str, ...] = (),
) -> list[str]:
    missing: list[str] = []
    if not runtime.python_bin or not Path(str(runtime.python_bin)).is_file():
        missing.append("python_bin")
    if not runtime.repo_root or not Path(str(runtime.repo_root)).is_dir():
        missing.append("repo_root")
        return missing

    repo = Path(str(runtime.repo_root))
    if not (repo / entrypoint_rel).is_file():
        missing.append(f"repo_root.{entrypoint_rel}")

    if model_path_kind == "file":
        if not runtime.model_path or not Path(str(runtime.model_path)).is_file():
            missing.append("model_path")
    elif model_path_kind == "dir":
        if not runtime.model_path or not Path(str(runtime.model_path)).is_dir():
            missing.append("model_path")

    for field in required_extra_paths:
        value = runtime.extra_paths.get(field)
        if value is None or not str(value).strip():
            missing.append(f"extra_paths.{field}")
    for field in existing_extra_paths:
        value = runtime.extra_paths.get(field)
        if value is None or not str(value).strip():
            missing.append(f"extra_paths.{field}")
            continue
        if not Path(str(value)).exists():
            missing.append(f"extra_paths.{field}")
    return missing
