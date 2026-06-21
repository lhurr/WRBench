from __future__ import annotations

import pytest

from wrbench.prompts.camera_text import (
    anchor_subject_in_prompt,
    assemble_ti2v_prompt,
    build_prompt_to_send,
    camera_clause,
    extract_subject_phrase,
    preset_camera_text,
)
from wrbench.prompts.scene import load_t2i_scene_system_prompt
from wrbench.prompts.task import (
    build_scene_start,
    detect_pronoun,
    generate_variants_deterministic,
)


def test_camera_clause_yaw_lr() -> None:
    text = camera_clause("yaw_LR", pronoun="she", offscreen_area="empty stone paving")
    assert "she" in text
    assert "empty stone paving" in text
    assert "Single continuous shot" in text


def test_preset_camera_text() -> None:
    text = preset_camera_text("static")
    assert "fixed in place" in text


def test_assemble_ti2v_prompt() -> None:
    prompt = assemble_ti2v_prompt(
        "A cat sits on the left.",
        "Immediately, it jumps.",
        "it",
        "empty floor",
        "yaw_LR",
    )
    assert prompt.startswith("A cat sits on the left.")
    assert "Immediately, it jumps." in prompt
    assert "empty floor" in prompt


def test_assemble_ti2v_prompt_subject_anchored() -> None:
    prompt = assemble_ti2v_prompt(
        "Scene setup.",
        "Immediately, he walks toward the bed.",
        "he",
        "empty floor",
        "yaw_LR",
        subject_phrase="The adult person",
    )
    assert "Immediately, the adult person walks toward the bed." in prompt
    assert "until he is out of frame" in prompt


def test_extract_subject_phrase() -> None:
    assert extract_subject_phrase("The child walks toward the dining chair.") == "The child"
    assert extract_subject_phrase("An adult person stands on the bedroom floor, facing the bed.") == "An adult person"


def test_anchor_subject_in_prompt_noop_when_already_explicit() -> None:
    prompt = "Scene. Immediately, the adult sits on the floor."
    assert anchor_subject_in_prompt(prompt, "The adult person") == prompt


def test_hailuo_prompt_assembly() -> None:
    base = "Scene description. The cat jumps."
    out = build_prompt_to_send(base, "yaw_LR", model="hailuo-2.3")
    assert "[Pan left]" in out
    assert "Preserve the first-frame" in out
    assert "The cat jumps." in out


def test_copy_optimized_prompt_passthrough() -> None:
    base = "Full prompt with camera already embedded."
    out = build_prompt_to_send(base, "yaw_LR", model="veo-3.1-fast")
    assert out == base


def test_scene_system_prompt_template_exists() -> None:
    text = load_t2i_scene_system_prompt()
    assert "first-frame image caption" in text.lower() or "first frame" in text.lower()


def test_deterministic_variants_minimal() -> None:
    candidates = [
        {
            "candidate_id": "test_family",
            "offscreen_area": "empty concrete floor",
            "events": {
                "t0": "still",
                "t1": "The cat walks to the bowl.",
                "div_a_state_only": {"middle_sentence": "From the start, the cat stays alert.", "world_state": "alert"},
                "div_b": "The cat eats from the bowl.",
            },
        }
    ]
    families = {
        "test_family": {
            "family_id": "test_family",
            "scene": "a kitchen",
            "primary_object": {"name": "a cat"},
            "supporting_objects": [
                {"name": "a food bowl", "role": "interactor"},
                {"name": "a chair", "role": "anchor"},
            ],
            "t2i_scene": (
                "In a kitchen, a gray cat stands on the left third of the frame, "
                "facing a food bowl on the right side of the frame, several steps away."
            ),
        }
    }
    variants = generate_variants_deterministic(candidates, families)
    assert len(variants) == 16  # 4 tiers × 4 gaps
    assert all("ti2v_prompt" in v for v in variants)
    t1_yaw = next(v for v in variants if v["reasoning_tier"] == "T1" and v["oov_gap"] == "yaw_LR")
    assert "Immediately, it walks" in t1_yaw["ti2v_prompt"]
    assert detect_pronoun(families["test_family"]["t2i_scene"], "a cat") == "it"
    scene_start = build_scene_start(families["test_family"]["t2i_scene"], families["test_family"])
    assert "food bowl" in scene_start.lower()


def test_generate_t2i_scene_with_mock_llm() -> None:
    from wrbench.prompts.scene import generate_t2i_scene

    family = {
        "family_id": "x",
        "scene": "garden",
        "primary_object": {"name": "a person"},
        "supporting_objects": [],
        "first_frame_guidance": {"texture": "stone"},
    }

    def mock_llm(system: str, user: str) -> dict:
        return {"t2i_scene": "In a garden, a person stands on the left."}

    text = generate_t2i_scene(family, llm_call=mock_llm)
    assert "garden" in text


def test_call_llm_json_requires_explicit_provider() -> None:
    from wrbench.prompts.llm import call_llm_json

    with pytest.raises(RuntimeError, match="LLM provider required"):
        call_llm_json(
            system_prompt="system",
            user_message="user",
            model="test-model",
        )


def test_call_llm_json_requires_explicit_model() -> None:
    from wrbench.prompts.llm import call_llm_json

    with pytest.raises(RuntimeError, match="LLM model required"):
        call_llm_json(
            system_prompt="system",
            user_message="user",
            provider="openai",
        )
