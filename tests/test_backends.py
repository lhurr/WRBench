from pathlib import Path

from wrcam.backends import DryRunBackend, GenerationRequest, default_backend
from wrcam.payload import CameraPayload
from wrcam.trajectory import CameraTrajectory
import numpy as np


def test_dry_run_backend_available():
    backend = default_backend()
    ok, msg = backend.available()
    assert ok
    assert "dry-run" in msg.lower()


def test_dry_run_backend_does_not_generate():
    traj = CameraTrajectory(
        c2w=np.repeat(np.eye(4, dtype=np.float32)[None], 4, axis=0),
        intrinsics=np.eye(3, dtype=np.float32),
        camera_type="static",
    )
    payload = CameraPayload(
        payload_type="test",
        payload={},
        target_trajectory=traj,
        official_camera_entrypoint="",
        coordinate_notes="",
        calibration_status="test",
    )
    result = DryRunBackend().generate(
        GenerationRequest(model="wan22-fun-5b-cam", prompt="p", payload=payload, output_path=Path("out.mp4"))
    )
    assert not result.success
    assert "Dry-run" in result.message
