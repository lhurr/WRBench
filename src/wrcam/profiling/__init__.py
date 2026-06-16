"""Generation resource profiling for wrcam runs."""

from wrcam.profiling.monitor import (
    build_profile_summary,
    derive_metrics,
    run_profiled_command,
    sample_gpu_memory,
    summarize_gpu_samples,
    summarize_stage_events,
    update_summary_derived_metrics,
)
from wrcam.profiling.stage import StageRecorder, get_stage_recorder
from wrcam.profiling.summarize import format_rows, load_profiles, summarize

__all__ = [
    "StageRecorder",
    "build_profile_summary",
    "derive_metrics",
    "format_rows",
    "get_stage_recorder",
    "load_profiles",
    "run_profiled_command",
    "sample_gpu_memory",
    "summarize",
    "summarize_gpu_samples",
    "summarize_stage_events",
    "update_summary_derived_metrics",
]
