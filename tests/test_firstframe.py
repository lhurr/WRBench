from __future__ import annotations

import json
from pathlib import Path

from wrbench.firstframe import (
    MockT2IProvider,
    generate_first_frame,
    generate_first_frames_from_families,
    write_manifest,
)


def test_mock_first_frame_generation(tmp_path: Path) -> None:
    provider = MockT2IProvider()
    manifest = generate_first_frame(
        family_id="bedroom_cat",
        prompt="A cat on a bed.",
        out_dir=tmp_path,
        provider="mock",
        t2i=provider,
    )
    assert Path(manifest.image_path).is_file()
    assert manifest.image_path.endswith("bedroom_cat.png")
    assert manifest.provider == "mock"


def test_generate_first_frames_from_families_skip_existing(tmp_path: Path) -> None:
    existing = tmp_path / "fam_a.png"
    existing.write_bytes(b"fake")

    families = [
        {"family_id": "fam_a", "t2i_scene": "scene a"},
        {"family_id": "fam_b", "t2i_scene": "scene b"},
        {"family_id": "fam_c"},  # no prompt
    ]
    provider = MockT2IProvider()
    manifests = generate_first_frames_from_families(
        families,
        out_dir=tmp_path,
        t2i=provider,
        skip_existing=True,
    )
    assert len(manifests) == 2
    assert (tmp_path / "fam_b.png").is_file()
    skipped = [m for m in manifests if m.metadata.get("skipped")]
    assert len(skipped) == 1


def test_write_manifest(tmp_path: Path) -> None:
    from wrbench.firstframe.generate import FirstFrameManifest

    manifests = [
        FirstFrameManifest("a", "prompt", str(tmp_path / "a.png"), "mock", "mock"),
    ]
    path = tmp_path / "manifest.json"
    write_manifest(path, manifests)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["family_id"] == "a"
