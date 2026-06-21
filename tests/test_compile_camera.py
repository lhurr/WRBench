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
    if kind == "none":
        return {"prompt": "A benchmark scene prompt."}
    if kind == "source_video":
        return {"source_video": "src.mp4"}
    raise RuntimeError(f"Unrecognised input_kind {kind!r} for {model_key}")


def _wrong_input_kwargs(model_key: str):
    """Return an *incorrect* input (wrong kind) to trigger ValueError."""
    kind = input_kind(model_key)
    if kind == "image":
        return {"source_video": "src.mp4"}
    if kind == "none":
        return {"image": "first.png"}
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
    if input_kind(key) == "none":
        result = wrbench.compile_camera(
            model=key,
            camera=CAMERA_SCRIPT,
            out=out,
            dry_run=True,
        )
        assert result["payload"].payload_type
        return
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


def test_minwm_wan_prompt_trajectory_payload(tmp_path):
    prompt = "A WRBench Natural-25 scene prompt for Wan."
    out = tmp_path / "wan.mp4"
    result = wrbench.compile_camera(
        model="minwm-wan-action2v",
        camera=CAMERA_SCRIPT,
        out=out,
        prompt=prompt,
        dry_run=True,
    )
    payload = result["payload"].payload
    assert payload["trajectory"] == "j*10,l*9"
    assert Path(payload["prompt_txt"]).read_text(encoding="utf-8") == prompt + "\n"
    assert Path(payload["trajectory_txt"]).read_text(encoding="utf-8") == "j*10,l*9\n"
    assert payload["token_mapping_details"]["runtime_yaw_deg_per_token"] == 6.0

    request = json.loads(Path(payload["request_json"]).read_text(encoding="utf-8"))
    assert request["model_key"] == "minwm-wan-action2v"
    assert request["input_contract"]["prompt_path"] == payload["prompt_txt"]
    assert request["input_contract"]["trajectory_path"] == payload["trajectory_txt"]
    assert request["input_contract"]["requires_first_frame_image"] is False
    assert request["input_contract"]["runtime_patch_applied"] is True
    assert result["payload"].target_trajectory.frame_count == 77
    assert result["payload"].target_trajectory.fps == 16


@pytest.mark.parametrize("model", ["minwm-hy-action2v", "minwm-wan-action2v"])
def test_minwm_yaw_rl_uses_right_then_left_tokens(tmp_path, model):
    out = tmp_path / f"{model}.mp4"
    kwargs = {
        "model": model,
        "camera": wrbench.presets.build_preset("yaw_RL", frames=77),
        "out": out,
        "prompt": "A WRBench prompt.",
        "dry_run": True,
    }
    if model == "minwm-hy-action2v":
        image = tmp_path / "first.png"
        image.write_bytes(b"png")
        kwargs["image"] = str(image)

    result = wrbench.compile_camera(**kwargs)
    payload = result["payload"].payload
    details = result["payload"].metadata["model_payload_summary"]["token_mapping_details"]

    assert payload["trajectory"] == "l*10,j*9"
    assert details["token_mapping_rule"] == "l_then_j_minwm_yaw_tokens"
    assert details["requested_yaw_peak_signed_deg"] == 60.0
    assert details["effective_yaw_peak_signed_deg"] == 60.0
    assert details["requires_runtime_rot_step_patch"] is True


def test_minwm_wan_yaw30_scope_uses_canonical_yaw_type_without_rotation_patch(tmp_path):
    out = tmp_path / "wan_yaw30.mp4"
    result = wrbench.compile_camera(
        model="minwm-wan-action2v",
        camera=wrbench.presets.yaw_LR(peak_deg=30, frames=77),
        camera_type="yaw_LR",
        out=out,
        prompt="A WRBench prompt.",
        dry_run=True,
    )
    details = result["payload"].metadata["model_payload_summary"]["token_mapping_details"]
    sidecar = json.loads(Path(result["artifacts"]["camera_sidecar_path"]).read_text(encoding="utf-8"))

    assert result["payload"].payload["trajectory"] == "j*10,l*9"
    assert details["runtime_yaw_deg_per_token"] == 3.0
    assert details["requested_yaw_peak_deg"] == 30.0
    assert details["requires_runtime_rot_step_patch"] is False
    assert result["payload"].payload["rotation_step_patch"] is None
    assert result["payload"].payload["token_mapping_details"]["requires_runtime_rot_step_patch"] is False
    assert sidecar["camera_type"] == "yaw_LR"
    assert sidecar["control_family"] == "rotation"
    assert sidecar["control_direction"] == "yaw_LR"
    assert sidecar["control_profile"] == "diagnostic_30deg"
    assert sidecar["yaw_peak_deg"] == 30.0


def test_minwm_wan_real_generation_requires_prompt(tmp_path):
    out = tmp_path / "wan.mp4"
    with pytest.raises(ValueError, match="requires prompt"):
        wrbench.compile_camera(
            model="minwm-wan-action2v",
            camera=CAMERA_SCRIPT,
            out=out,
            dry_run=False,
        )


def test_minwm_hy_real_generation_requires_prompt(tmp_path):
    image = tmp_path / "first.png"
    image.write_bytes(b"png")
    out = tmp_path / "hy.mp4"
    with pytest.raises(ValueError, match="requires prompt"):
        wrbench.compile_camera(
            model="minwm-hy-action2v",
            camera=CAMERA_SCRIPT,
            out=out,
            image=str(image),
            dry_run=False,
        )


def test_minwm_wan_static_payload_stays_static(tmp_path):
    out = tmp_path / "wan_static.mp4"
    result = wrbench.compile_camera(
        model="minwm-wan-action2v",
        camera="static@77",
        out=out,
        prompt="A static benchmark scene prompt.",
        dry_run=True,
    )
    payload = result["payload"].payload
    assert payload["trajectory"] == "z*19"
    assert Path(payload["trajectory_txt"]).read_text(encoding="utf-8") == "z*19\n"
    assert payload["rotation_step_patch"] is not None
    patch_root = Path(payload["rotation_step_patch"]["patch_root"])
    assert (patch_root / "wan_utils" / "camera_trajectory.py").exists()


def test_doctor_accepts_prompt_only_minwm_wan():
    from wrbench.cli import _doctor_check_model

    ok, lines = _doctor_check_model("minwm-wan-action2v")
    assert ok, "\n".join(lines)
