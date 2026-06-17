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


# ---------------------------------------------------------------------------
# Compound / simultaneous: segment() API and + string syntax.
# ---------------------------------------------------------------------------

def test_segment_produces_simultaneous_flag():
    script = CameraScript().segment(40, yaw_left=60, dolly_forward=1.0)
    assert len(script.actions) == 2
    assert script.actions[0].simultaneous is False
    assert script.actions[1].simultaneous is True


def test_segment_frame_count_not_doubled():
    script = CameraScript().segment(40, yaw_left=60, dolly_forward=1.0)
    assert script.frame_count == 40


def test_segment_chained_frame_count():
    script = (
        CameraScript()
        .segment(40, yaw_left=60, dolly_forward=1.0)
        .segment(41, yaw_right=60, dolly_back=1.0)
    )
    assert script.frame_count == 81


def test_segment_to_string():
    script = CameraScript().segment(40, yaw_left=60, dolly_forward=1.0)
    s = script.to_string()
    assert "+" in s
    assert "@40" in s
    assert "yaw:left:60" in s
    assert "dolly:forward:1" in s


def test_parse_compound_string():
    script = parse_camera_script("yaw:left:60+dolly:forward:1@40,yaw:right:60@41")
    assert script.frame_count == 81
    assert len(script.actions) == 3
    assert script.actions[0].simultaneous is False
    assert script.actions[1].simultaneous is True
    assert script.actions[2].simultaneous is False


def test_compound_round_trip():
    original = "yaw:left:60+dolly:forward:1@40,yaw:right:60@41"
    script = parse_camera_script(original)
    assert script.to_string() == original


def test_compound_round_trip_three_simultaneous():
    original = "yaw:left:30+pitch:down:15+pan:right:0.5@40"
    script = parse_camera_script(original)
    assert script.to_string() == original
    assert script.frame_count == 40
    assert len(script.actions) == 3


def test_segment_equals_parsed_compound():
    built = CameraScript().segment(40, yaw_left=60, dolly_forward=1.0)
    parsed = parse_camera_script("yaw:left:60+dolly:forward:1@40")
    assert built == parsed


def test_segment_bad_kwarg_no_underscore():
    with pytest.raises(ValueError, match="kind_direction"):
        CameraScript().segment(40, yaw=60)


def test_segment_bad_kind():
    with pytest.raises(ValueError, match="Unknown motion kind"):
        CameraScript().segment(40, zoom_in=2.0)


def test_segment_requires_kwargs():
    with pytest.raises(ValueError, match="requires at least one"):
        CameraScript().segment(40)


def test_compound_three_actions_frame_count():
    script = CameraScript().segment(40, yaw_left=30, pitch_down=15, crane_up=0.2)
    assert script.frame_count == 40
    assert len(script.actions) == 3


COMPOUND_ROUND_TRIP_CASES = [
    ("arc", "yaw:left:60+dolly:forward:1@40,yaw:right:60+dolly:back:1@41"),
    ("diagonal", "yaw:left:30+pitch:down:15@40"),
    ("three_motion", "yaw:left:30+pitch:down:15+pan:right:0.5@40"),
    ("single_then_compound", "static@10,yaw:left:60+dolly:forward:1@40"),
]


@pytest.mark.parametrize("label,s", COMPOUND_ROUND_TRIP_CASES, ids=[c[0] for c in COMPOUND_ROUND_TRIP_CASES])
def test_compound_round_trip_cases(label, s):
    assert parse_camera_script(s).to_string() == s
