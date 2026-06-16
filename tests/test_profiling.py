from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from wrcam.profiling import run_profiled_command, summarize, update_summary_derived_metrics
from wrcam.profiling.monitor import summarize_stage_events
from wrcam.profiling.stage import StageRecorder


def test_stage_recorder_writes_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    recorder = StageRecorder(path, command_id="cmd1")

    with recorder.stage("preprocess", item_id="video.mp4", metadata={"x": 1}):
        pass

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["schema_version"] == "wrcam_stage_event_v1"
    assert rows[0]["command_id"] == "cmd1"
    assert rows[0]["stage"] == "preprocess"
    assert rows[0]["item_id"] == "video.mp4"
    assert rows[0]["status"] == "ok"
    assert rows[0]["duration_seconds"] >= 0


def test_profiled_command_records_stages_and_derived_metrics(tmp_path: Path) -> None:
    summary = tmp_path / "profile.json"
    trace = tmp_path / "trace.jsonl"
    events = tmp_path / "events.jsonl"
    log = tmp_path / "generation.log"

    code = (
        "import time\n"
        "from wrcam.profiling import get_stage_recorder\n"
        "r = get_stage_recorder()\n"
        "with r.stage('preprocess', item_id='video.mp4'):\n"
        "    time.sleep(0.01)\n"
        "with r.stage('inference', item_id='video.mp4'):\n"
        "    time.sleep(0.01)\n"
    )
    env = os.environ.copy()
    src = Path(__file__).resolve().parents[1] / "src"
    env["PYTHONPATH"] = f"{src}:{env.get('PYTHONPATH', '')}"

    profile = run_profiled_command(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        summary_path=summary,
        trace_path=trace,
        stage_events_path=events,
        log_path=log,
        run_identity={
            "model": "dummy",
            "profile": "unit",
            "camera": "yaw_LR",
            "scene_id": "scene",
            "gpu_width": 2,
            "output_video_seconds": 4.0,
        },
        sampling_interval_seconds=0.01,
        sampler=lambda gpu_ids: [
            {
                "gpu_id": "0",
                "gpu_uuid": "GPU-0",
                "gpu_name": "Fake GPU",
                "memory_used_mib": 123.0,
            }
        ],
    )

    assert profile["status"]["exit_code"] == 0
    assert profile["stage_summary"]["stage_status"] == "available"
    assert profile["stage_summary"]["benchmark_generation_seconds"] > 0
    assert profile["derived_metrics"]["gpu_width"] == 2
    assert profile["derived_metrics"]["benchmark_gpu_seconds"] > 0
    assert profile["derived_metrics"]["benchmark_gpu_seconds_per_output_second"] > 0
    assert profile["gpu_observation"]["peak_memory_mib_max"] == 123.0
    assert summary.is_file()
    assert trace.is_file()
    assert events.is_file()
    assert log.is_file()


def test_update_summary_derived_metrics_sets_generation_status(tmp_path: Path) -> None:
    summary = tmp_path / "profile.json"
    profile = {
        "run_identity": {"gpu_width": 1},
        "status": {"generation_status": "failed"},
        "stage_summary": {
            "benchmark_generation_seconds": 8.0,
            "preprocess_seconds": 2.0,
            "inference_seconds": 6.0,
        },
        "derived_metrics": {},
    }
    summary.write_text(json.dumps(profile), encoding="utf-8")

    updated = update_summary_derived_metrics(
        summary,
        output_video_seconds=4.0,
        generation_status="generated",
    )

    assert updated["status"]["generation_status"] == "generated"
    assert updated["derived_metrics"]["benchmark_generation_seconds_per_output_second"] == 2.0
    assert updated["derived_metrics"]["benchmark_gpu_seconds_per_output_second"] == 2.0
    assert updated["derived_metrics"]["preprocess_seconds_per_output_second"] == 0.5
    assert updated["derived_metrics"]["inference_seconds_per_output_second"] == 1.5


def test_stage_summary_uses_stage_presence_not_positive_duration(tmp_path: Path) -> None:
    events = tmp_path / "events.jsonl"
    rows = [
        {"stage": "preprocess", "duration_seconds": 0.0},
        {"stage": "inference", "duration_seconds": 0.0},
    ]
    events.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    summary = summarize_stage_events(events)

    assert summary["stage_status"] == "available"
    assert summary["benchmark_generation_seconds"] == 0.0


def test_summarize_resource_profiles_uses_generated_sum_over_sum() -> None:
    profiles = [
        {
            "run_identity": {"model": "m", "profile": "yaw60"},
            "status": {"generation_status": "generated", "ok": True},
            "stage_summary": {
                "stage_status": "available",
                "model_load_seconds": 10.0,
                "preprocess_seconds": 2.0,
                "inference_seconds": 6.0,
            },
            "gpu_observation": {"peak_memory_mib_max": 100.0, "peak_memory_mib_sum": 200.0},
            "derived_metrics": {
                "output_video_seconds": 4.0,
                "benchmark_generation_seconds": 8.0,
                "benchmark_gpu_seconds": 16.0,
            },
        },
        {
            "run_identity": {"model": "m", "profile": "yaw60"},
            "status": {"generation_status": "cache_reused", "ok": True},
            "stage_summary": {
                "stage_status": "available",
                "model_load_seconds": 0.0,
                "preprocess_seconds": 100.0,
                "inference_seconds": 100.0,
            },
            "gpu_observation": {"peak_memory_mib_max": 150.0, "peak_memory_mib_sum": 300.0},
            "derived_metrics": {
                "output_video_seconds": 1.0,
                "benchmark_generation_seconds": 200.0,
                "benchmark_gpu_seconds": 200.0,
            },
        },
    ]

    rows = summarize(profiles)

    assert len(rows) == 1
    row = rows[0]
    assert row["generated_rows"] == 1
    assert row["denominator_rows"] == 1
    assert row["status_counts"] == {"cache_reused": 1, "generated": 1}
    assert row["gpu_seconds_per_output_second"] == 4.0
    assert row["generation_seconds_per_output_second"] == 2.0
    assert row["peak_memory_mib_max"] == 150.0
