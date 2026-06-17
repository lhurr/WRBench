"""Tests for wrcam.builder: math invariants of build_camera_trajectory."""

import math

import numpy as np
import pytest

from wrcam.builder import build_camera_trajectory, default_intrinsics
from wrcam.presets import sweep


W, H = 832, 480


# ---------------------------------------------------------------------------
# Helper: relative yaw in degrees from a C2W stack.
# ---------------------------------------------------------------------------

def _relative_yaw(c2w: np.ndarray) -> np.ndarray:
    rel = np.linalg.inv(c2w[0]) @ c2w
    return np.degrees(np.arctan2(rel[:, 0, 2], rel[:, 0, 0]))


# ---------------------------------------------------------------------------
# yaw:left:60@40,yaw:right:60@41  →  (81,4,4) C2W stack
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def yaw_go_return_traj():
    return build_camera_trajectory("yaw:left:60@40,yaw:right:60@41", width=W, height=H)


def test_yaw_go_return_shape(yaw_go_return_traj):
    assert yaw_go_return_traj.c2w.shape == (81, 4, 4)


def test_yaw_go_return_first_frame_identity(yaw_go_return_traj):
    np.testing.assert_allclose(yaw_go_return_traj.c2w[0], np.eye(4), atol=1e-5)


def test_yaw_go_return_peak_near_minus60(yaw_go_return_traj):
    yaw = _relative_yaw(yaw_go_return_traj.c2w)
    peak = yaw[np.argmax(np.abs(yaw))]
    # Peak (leftward) is negative yaw in this convention
    assert abs(peak) > 55, f"expected |peak| > 55°, got {peak:.2f}°"
    assert peak < 0, f"expected peak to be negative (left yaw), got {peak:.2f}°"


def test_yaw_go_return_peak_near_midpoint(yaw_go_return_traj):
    yaw = _relative_yaw(yaw_go_return_traj.c2w)
    peak_idx = int(np.argmax(np.abs(yaw)))
    # Midpoint of 81 frames is around index 39-40 (last frame of first segment)
    assert 35 <= peak_idx <= 45, f"expected peak near midpoint, got index {peak_idx}"


def test_yaw_go_return_ends_near_zero(yaw_go_return_traj):
    yaw = _relative_yaw(yaw_go_return_traj.c2w)
    assert abs(yaw[-1]) < 5, f"expected final yaw near 0°, got {yaw[-1]:.2f}°"


# ---------------------------------------------------------------------------
# One-way sweep: yaw left 37° over 49 frames reaches ~-37° at the last frame.
# ---------------------------------------------------------------------------

def test_sweep_yaw_left_reaches_target():
    script = sweep("yaw", "left", 37, frames=49)
    traj = build_camera_trajectory(script, width=W, height=H)
    assert traj.c2w.shape == (49, 4, 4)
    yaw = _relative_yaw(traj.c2w)
    assert abs(yaw[-1] - (-37.0)) < 1.5, f"expected final yaw ≈ -37°, got {yaw[-1]:.3f}°"


# ---------------------------------------------------------------------------
# Pan script: translation along x, ~zero rotation.
# ---------------------------------------------------------------------------

def test_pan_translation_and_zero_rotation():
    traj = build_camera_trajectory("pan:left:0.5@40", width=W, height=H)
    c2w = traj.c2w
    assert c2w.shape == (40, 4, 4)
    # Rotation part should remain identity for all frames
    eye3 = np.eye(3)
    for i in range(c2w.shape[0]):
        np.testing.assert_allclose(c2w[i, :3, :3], eye3, atol=1e-5,
                                   err_msg=f"rotation not identity at frame {i}")
    # Last-frame x-translation should be non-zero (pan left => negative x delta)
    assert abs(c2w[-1, 0, 3]) > 1e-4, "expected non-zero x translation at last pan frame"


# ---------------------------------------------------------------------------
# static@30 yields all-identity poses.
# ---------------------------------------------------------------------------

def test_static_all_identity():
    traj = build_camera_trajectory("static@30", width=W, height=H)
    assert traj.c2w.shape == (30, 4, 4)
    np.testing.assert_allclose(traj.c2w, np.tile(np.eye(4), (30, 1, 1)), atol=1e-6)


# ---------------------------------------------------------------------------
# default_intrinsics produces a sane 3x3 with positive focal lengths.
# ---------------------------------------------------------------------------

def test_default_intrinsics_shape_and_positive_focal():
    K = default_intrinsics(W, H)
    assert K.shape == (3, 3)
    assert float(K[0, 0]) > 0, "fx must be positive"
    assert float(K[1, 1]) > 0, "fy must be positive"
    assert float(K[2, 2]) == pytest.approx(1.0)


def test_default_intrinsics_principal_point():
    K = default_intrinsics(W, H)
    assert float(K[0, 2]) == pytest.approx(W / 2.0)
    assert float(K[1, 2]) == pytest.approx(H / 2.0)


def test_default_intrinsics_fov_60():
    K = default_intrinsics(W, H, fov_deg=60.0)
    fx = float(K[0, 0])
    fov = math.degrees(2.0 * math.atan(W / (2.0 * fx)))
    assert abs(fov - 60.0) < 0.01, f"expected 60° FOV, got {fov:.3f}°"


# ---------------------------------------------------------------------------
# CameraTrajectory.resample(n) changes frame_count and keeps shape (n,4,4).
# ---------------------------------------------------------------------------

def test_resample_changes_frame_count():
    traj = build_camera_trajectory("yaw:left:60@40,yaw:right:60@41", width=W, height=H)
    assert traj.frame_count == 81
    resampled = traj.resample(49)
    assert resampled.frame_count == 49
    assert resampled.c2w.shape == (49, 4, 4)


def test_resample_preserves_start_and_end():
    traj = build_camera_trajectory("yaw:left:60@40,yaw:right:60@41", width=W, height=H)
    resampled = traj.resample(25)
    np.testing.assert_allclose(resampled.c2w[0], traj.c2w[0], atol=1e-5)
    np.testing.assert_allclose(resampled.c2w[-1], traj.c2w[-1], atol=1e-4)


def test_resample_identity_when_same_count():
    traj = build_camera_trajectory("static@30", width=W, height=H)
    same = traj.resample(30)
    assert same is traj


# ---------------------------------------------------------------------------
# Compound / simultaneous: rotation AND translation in the same frame window.
# ---------------------------------------------------------------------------

def test_compound_yaw_dolly_shape():
    traj = build_camera_trajectory("yaw:left:60+dolly:forward:1@40", width=W, height=H)
    assert traj.c2w.shape == (40, 4, 4)


def test_compound_yaw_dolly_first_frame_identity():
    traj = build_camera_trajectory("yaw:left:60+dolly:forward:1@40", width=W, height=H)
    np.testing.assert_allclose(traj.c2w[0], np.eye(4), atol=1e-5)


def test_compound_has_both_rotation_and_translation():
    """Last frame of a yaw+dolly segment must have non-identity rotation AND non-zero translation."""
    traj = build_camera_trajectory("yaw:left:60+dolly:forward:1@40", width=W, height=H)
    last = traj.c2w[-1]
    # Rotation part is not identity (yaw happened)
    assert not np.allclose(last[:3, :3], np.eye(3), atol=1e-3), "rotation should be non-identity"
    # Translation is non-zero (dolly happened)
    assert np.linalg.norm(last[:3, 3]) > 1e-3, "translation should be non-zero"


def test_compound_pure_rotation_only_no_translation():
    """A compound with only rotations must have zero translation at all frames."""
    traj = build_camera_trajectory("yaw:left:30+pitch:down:15@40", width=W, height=H)
    for i in range(traj.c2w.shape[0]):
        np.testing.assert_allclose(traj.c2w[i, :3, 3], np.zeros(3), atol=1e-5,
                                   err_msg=f"translation not zero at frame {i}")


def test_compound_pure_translation_only_no_rotation():
    """A compound with only translations must have identity rotation at all frames."""
    traj = build_camera_trajectory("pan:left:0.3+dolly:forward:1@40", width=W, height=H)
    for i in range(traj.c2w.shape[0]):
        np.testing.assert_allclose(traj.c2w[i, :3, :3], np.eye(3), atol=1e-5,
                                   err_msg=f"rotation not identity at frame {i}")


def test_compound_arc_go_return_shape():
    from wrcam.presets import arc_LR

    script = arc_LR(peak_deg=60, dolly_amount=1.0, frames=81)
    traj = build_camera_trajectory(script, width=W, height=H)
    assert traj.c2w.shape == (81, 4, 4)


def test_compound_arc_ends_near_start():
    """Arc go-return should bring camera close to identity pose at the end."""
    from wrcam.presets import arc_LR

    traj = build_camera_trajectory(arc_LR(peak_deg=60, dolly_amount=1.0, frames=81), width=W, height=H)
    # Translation should be close to zero at end (go-return cancels out)
    final_t = traj.c2w[-1, :3, 3]
    assert np.linalg.norm(final_t) < 0.2, f"expected near-zero final translation, got {final_t}"


def test_compound_segment_api_matches_string():
    """segment() API must produce the same trajectory as the equivalent + string."""
    from wrcam.actions import CameraScript

    script_py = CameraScript().segment(40, yaw_left=60, dolly_forward=1.0)
    script_str = "yaw:left:60+dolly:forward:1@40"
    traj_py = build_camera_trajectory(script_py, width=W, height=H)
    traj_str = build_camera_trajectory(script_str, width=W, height=H)
    np.testing.assert_allclose(traj_py.c2w, traj_str.c2w, atol=1e-6)
