"""Tests for wrcam.actions: parse_camera_script, CameraScript, FrameAction."""

import pytest

from wrcam.actions import (
    CameraScript,
    FrameAction,
    parse_camera_script,
)


# ---------------------------------------------------------------------------
# Round-trip: parse → to_string should reproduce the canonical form.
# ---------------------------------------------------------------------------

ROUND_TRIP_CASES = [
    # (label, script_str)
    ("yaw_go_return", "yaw:left:60@40,yaw:right:60@41"),
    ("pan_single", "pan:left:0.5@40"),
    ("static_single", "static@81"),
    ("multi_with_static", "yaw:left:30@20,static@10,yaw:right:30@20"),
    ("pitch", "pitch:up:45@30"),
    ("roll", "roll:left:90@30"),
    ("dolly", "dolly:forward:0.3@30"),
    ("crane", "crane:up:0.2@30"),
]


@pytest.mark.parametrize("label,script_str", ROUND_TRIP_CASES, ids=[c[0] for c in ROUND_TRIP_CASES])
def test_round_trip(label, script_str):
    script = parse_camera_script(script_str)
    assert script.to_string() == script_str


# ---------------------------------------------------------------------------
# Invalid scripts must raise ValueError.
# ---------------------------------------------------------------------------

INVALID_CASES = [
    # (label, bad_str, match_fragment)
    ("empty_string", "", "empty"),
    ("bad_kind", "spin:left:60@40", "Unsupported action kind"),
    ("bad_yaw_direction", "yaw:forward:60@40", "Unsupported yaw direction"),
    ("bad_pan_direction", "pan:up:0.5@40", "Unsupported pan direction"),
    # wrong field count – only kind:direction provided (missing value)
    ("malformed_two_fields", "yaw:left@40", "camera action format"),
    # too many fields
    ("malformed_four_fields", "yaw:left:60:extra@40", "camera action format"),
    # static with extra fields
    ("static_extra_fields", "static:extra:thing@40", "static action format"),
    # non-positive frames
    ("zero_frames", "yaw:left:60@0", "positive"),
    ("negative_frames", "yaw:left:60@-1", "positive"),
]


@pytest.mark.parametrize("label,bad_str,match", INVALID_CASES, ids=[c[0] for c in INVALID_CASES])
def test_invalid_script_raises(label, bad_str, match):
    with pytest.raises(ValueError, match=match):
        parse_camera_script(bad_str)


def test_rotation_requires_degrees_via_frame_action():
    with pytest.raises(ValueError, match="requires degrees"):
        FrameAction("yaw", "left")


def test_translation_requires_amount_via_frame_action():
    with pytest.raises(ValueError, match="requires amount"):
        FrameAction("pan", "left")


def test_bad_kind_via_frame_action():
    with pytest.raises(ValueError, match="Unsupported action kind"):
        FrameAction("zoom", "in", degrees=10)


# ---------------------------------------------------------------------------
# Builder methods produce scripts equal to their parsed equivalents.
# ---------------------------------------------------------------------------

def test_builder_yaw_go_return():
    built = CameraScript().yaw("left", degrees=60, frames=40).yaw("right", degrees=60, frames=41)
    parsed = parse_camera_script("yaw:left:60@40,yaw:right:60@41")
    assert built == parsed


def test_builder_static():
    built = CameraScript().static(frames=81)
    parsed = parse_camera_script("static@81")
    assert built == parsed


def test_builder_pan():
    built = CameraScript().pan("left", amount=0.5, frames=40)
    parsed = parse_camera_script("pan:left:0.5@40")
    assert built == parsed


def test_builder_pitch():
    built = CameraScript().pitch("up", degrees=45, frames=30)
    parsed = parse_camera_script("pitch:up:45@30")
    assert built == parsed


def test_builder_roll():
    built = CameraScript().roll("left", degrees=90, frames=30)
    parsed = parse_camera_script("roll:left:90@30")
    assert built == parsed


def test_builder_dolly():
    built = CameraScript().dolly("forward", amount=0.3, frames=30)
    parsed = parse_camera_script("dolly:forward:0.3@30")
    assert built == parsed


def test_builder_crane():
    built = CameraScript().crane("up", amount=0.2, frames=30)
    parsed = parse_camera_script("crane:up:0.2@30")
    assert built == parsed


def test_builder_multi_segment_with_static():
    built = (
        CameraScript()
        .yaw("left", degrees=30, frames=20)
        .static(frames=10)
        .yaw("right", degrees=30, frames=20)
    )
    parsed = parse_camera_script("yaw:left:30@20,static@10,yaw:right:30@20")
    assert built == parsed


def test_frame_count_sums():
    script = parse_camera_script("yaw:left:60@40,yaw:right:60@41")
    assert script.frame_count == 81


def test_no_frames_gives_none_frame_count():
    script = CameraScript().yaw("left", degrees=60)
    assert script.frame_count is None
