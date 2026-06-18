"""End-to-end dry-run tests for wrbench.compile_camera over all active models."""

import json
from pathlib import Path

import numpy as np
import pytest

import wrbench
from wrbench.registry import active_model_keys, input_kind


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CAMERA_SCRIPT = "yaw:left:60@40,yaw:right:60@41"
EXPECTED_SIDECAR_SUFFIXES = (
    ".target_c2w.npy",
    ".camera_trajectory.json",
    ".camera.json",
    ".model_control_samples.json",
    ".payload.json",
)
UNIFIED_SIDECAR_FIELDS = (
    "camera_control_source",
    "frame_action_script",
    "model_payload_type",
    "model_control_timeline",
)


def _input_kwargs(model_key: str):
    """Return the correct input keyword argument for this model."""
    kind = input_kind(model_key)
    if kind == "image":
        return {"image": "first.png"}
    if kind == "source_video":
        return {"source_video": "src.mp4"}
    raise RuntimeError(f"Unrecognised input_kind {kind!r} for {model_key}")


def _wrong_input_kwargs(model_key: str):
    """Return an *incorrect* input (wrong kind) to trigger ValueError."""
    kind = input_kind(model_key)
    if kind == "image":
        return {"source_video": "src.mp4"}
    return {"image": "first.png"}


# ---------------------------------------------------------------------------
# Parametric over all currently-registered active models.
# ---------------------------------------------------------------------------

@pytest.fixture(params=active_model_keys(), ids=active_model_keys())
def model_result(request, tmp_path):
    """Compile the standard camera script for each active model and return the result."""
    key = request.param
    out = tmp_path / "output.mp4"
    result = wrbench.compile_camera(
        model=key,
        camera=CAMERA_SCRIPT,
        out=out,
        **_input_kwargs(key),
        dry_run=True,
    )
    return key, out, result


def test_returns_dict_with_truthy_payload_type(model_result):
    _key, _out, result = model_result
    assert isinstance(result, dict)
    payload = result["payload"]
    assert payload.payload_type, "payload_type must be truthy"


def test_sidecar_files_exist(model_result):
    _key, out, _result = model_result
    for suffix in EXPECTED_SIDECAR_SUFFIXES:
        path = Path(str(out) + suffix)
        assert path.exists(), f"Expected sidecar {path.name!r} to exist"


def test_target_c2w_npy_shape(model_result):
    _key, out, _result = model_result
    npy_path = Path(str(out) + ".target_c2w.npy")
    arr = np.load(npy_path)
    assert arr.ndim == 3, f"Expected 3-D array, got {arr.ndim}-D"
    assert arr.shape[1] == 4 and arr.shape[2] == 4, (
        f"Expected (...,4,4), got {arr.shape}"
    )
    assert arr.shape[0] > 0, "target_c2w.npy must have at least one frame"


def test_target_c2w_npy_is_float(model_result):
    _key, out, _result = model_result
    npy_path = Path(str(out) + ".target_c2w.npy")
    arr = np.load(npy_path)
    assert np.issubdtype(arr.dtype, np.floating), (
        f"Expected floating dtype, got {arr.dtype}"
    )


def test_camera_json_unified_fields(model_result):
    _key, out, _result = model_result
    camera_json = Path(str(out) + ".camera.json")
    data = json.loads(camera_json.read_text(encoding="utf-8"))
    for field in UNIFIED_SIDECAR_FIELDS:
        assert field in data, (
            f"Unified sidecar field {field!r} missing from .camera.json"
        )


def test_camera_json_camera_control_source(model_result):
    _key, out, _result = model_result
    data = json.loads(Path(str(out) + ".camera.json").read_text())
    assert data["camera_control_source"] == "frame_action_script"


def test_camera_json_frame_action_script(model_result):
    _key, out, _result = model_result
    data = json.loads(Path(str(out) + ".camera.json").read_text())
    assert data["frame_action_script"] == CAMERA_SCRIPT


# ---------------------------------------------------------------------------
# Wrong / missing input raises ValueError.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", active_model_keys(), ids=active_model_keys())
def test_missing_input_raises(key, tmp_path):
    out = tmp_path / "output.mp4"
    with pytest.raises(ValueError):
        wrbench.compile_camera(
            model=key,
            camera=CAMERA_SCRIPT,
            out=out,
            # intentionally provide no image= or source_video=
        )


@pytest.mark.parametrize("key", active_model_keys(), ids=active_model_keys())
def test_wrong_input_kind_raises(key, tmp_path):
    out = tmp_path / "output.mp4"
    wrong_kwargs = _wrong_input_kwargs(key)
    with pytest.raises(ValueError):
        wrbench.compile_camera(
            model=key,
            camera=CAMERA_SCRIPT,
            out=out,
            **wrong_kwargs,
        )


# ---------------------------------------------------------------------------
# Passing a CameraScript object as camera= works the same as the string form.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", active_model_keys(), ids=active_model_keys())
def test_camera_script_object_equals_string(key, tmp_path):
    out_str = tmp_path / "from_str.mp4"
    out_obj = tmp_path / "from_obj.mp4"

    preset_script = wrbench.presets.yaw_LR(peak_deg=60, frames=81)

    result_str = wrbench.compile_camera(
        model=key,
        camera=CAMERA_SCRIPT,
        out=out_str,
        **_input_kwargs(key),
        dry_run=True,
    )
    result_obj = wrbench.compile_camera(
        model=key,
        camera=preset_script,
        out=out_obj,
        **_input_kwargs(key),
        dry_run=True,
    )

    # Both should succeed and yield the same payload type
    assert result_str["payload"].payload_type == result_obj["payload"].payload_type

    # Both sidecar .payload.json files must exist
    assert Path(str(out_str) + ".payload.json").exists()
    assert Path(str(out_obj) + ".payload.json").exists()

    # The compiled script strings should differ (different segment split) but
    # the shape of target_c2w must be the same (81 frames each)
    arr_str = np.load(str(out_str) + ".target_c2w.npy")
    arr_obj = np.load(str(out_obj) + ".target_c2w.npy")
    assert arr_str.shape == arr_obj.shape, (
        f"Shape mismatch: string={arr_str.shape}, object={arr_obj.shape}"
    )
