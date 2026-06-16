"""Tests for wrcam.presets: preset names, frame counts, and script content."""

import pytest

from wrcam.actions import CameraScript
from wrcam.presets import (
    PRESETS,
    build_preset,
    go_return,
    pan_LR,
    pan_RL,
    preset_names,
    static,
    sweep,
    yaw_LR,
    yaw_RL,
)


# ---------------------------------------------------------------------------
# preset_names() includes the five canonical presets.
# ---------------------------------------------------------------------------

EXPECTED_PRESETS = {"static", "yaw_LR", "yaw_RL", "pan_LR", "pan_RL"}


def test_preset_names_includes_all():
    names = set(preset_names())
    assert EXPECTED_PRESETS <= names, (
        f"Missing preset names: {EXPECTED_PRESETS - names}"
    )


# ---------------------------------------------------------------------------
# Each preset returns a CameraScript whose frame_count equals `frames`.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", EXPECTED_PRESETS)
def test_preset_default_frame_count(name):
    script = PRESETS[name]()
    assert isinstance(script, CameraScript)
    assert script.frame_count == 81


@pytest.mark.parametrize("name", EXPECTED_PRESETS)
def test_preset_custom_even_frame_count(name):
    script = PRESETS[name](frames=60)
    assert script.frame_count == 60


def test_preset_odd_frame_count_81():
    """81 is odd: _split(81) = (40, 41), total = 81."""
    for name in {"yaw_LR", "yaw_RL", "pan_LR", "pan_RL"}:
        script = PRESETS[name](frames=81)
        assert script.frame_count == 81, f"{name}(frames=81) gave {script.frame_count}"


def test_preset_odd_frame_count_51():
    """51 is odd: _split(51) = (25, 26), total = 51."""
    for name in {"yaw_LR", "yaw_RL", "pan_LR", "pan_RL"}:
        script = PRESETS[name](frames=51)
        assert script.frame_count == 51, f"{name}(frames=51) gave {script.frame_count}"


def test_static_any_frame_count():
    for n in [1, 30, 81, 120]:
        assert static(n).frame_count == n


# ---------------------------------------------------------------------------
# yaw_LR / yaw_RL segment direction checks.
# ---------------------------------------------------------------------------

def test_yaw_LR_segments():
    script = yaw_LR(peak_deg=45)
    assert len(script.actions) == 2
    first, second = script.actions
    assert first.kind == "yaw" and first.direction == "left"
    assert float(first.degrees) == pytest.approx(45.0)
    assert second.kind == "yaw" and second.direction == "right"
    assert float(second.degrees) == pytest.approx(45.0)


def test_yaw_RL_segments():
    script = yaw_RL(peak_deg=30)
    assert len(script.actions) == 2
    first, second = script.actions
    assert first.kind == "yaw" and first.direction == "right"
    assert second.kind == "yaw" and second.direction == "left"


def test_yaw_LR_frame_split(frames=81):
    script = yaw_LR(frames=81)
    first, second = script.actions
    assert first.frames == 40
    assert second.frames == 41


# ---------------------------------------------------------------------------
# build_preset('yaw_LR', ...) matches yaw_LR(...).
# ---------------------------------------------------------------------------

def test_build_preset_matches_direct_call():
    via_build = build_preset("yaw_LR", peak_deg=30, frames=60)
    via_direct = yaw_LR(30, 60)
    assert via_build == via_direct


def test_build_preset_static():
    assert build_preset("static", frames=40) == static(40)


def test_build_preset_unknown_raises():
    with pytest.raises(KeyError, match="Unknown preset"):
        build_preset("not_a_preset")


# ---------------------------------------------------------------------------
# sweep and go_return produce valid CameraScript objects.
# ---------------------------------------------------------------------------

def test_sweep_yaw():
    script = sweep("yaw", "left", 37, frames=49)
    assert isinstance(script, CameraScript)
    assert script.frame_count == 49
    assert len(script.actions) == 1
    assert script.actions[0].kind == "yaw"
    assert script.actions[0].direction == "left"
    assert float(script.actions[0].degrees) == pytest.approx(37.0)


def test_sweep_pan():
    script = sweep("pan", "right", 0.3, frames=30)
    assert isinstance(script, CameraScript)
    assert script.frame_count == 30
    assert script.actions[0].kind == "pan"
    assert float(script.actions[0].amount) == pytest.approx(0.3)


def test_sweep_invalid_kind():
    with pytest.raises(ValueError, match="Unsupported sweep kind"):
        sweep("zoom", "in", 1.0, frames=30)


def test_go_return_produces_valid_script():
    script = go_return("yaw", "left", "right", 60, frames=81)
    assert isinstance(script, CameraScript)
    assert script.frame_count == 81
    assert len(script.actions) == 2


def test_go_return_frame_split_odd():
    script = go_return("pitch", "up", "down", 30, frames=81)
    first, second = script.actions
    assert first.frames + second.frames == 81


def test_go_return_translation():
    script = go_return("pan", "left", "right", 0.5, frames=60)
    assert script.frame_count == 60
    assert script.actions[0].kind == "pan"
    assert script.actions[0].direction == "left"
