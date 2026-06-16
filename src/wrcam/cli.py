"""Command-line interface for wrcam.

Sub-commands
------------
models           List supported models.
presets          List preset camera motions.
actions          Parse and validate a frame-action camera script.
generate         Compile a camera script and write model-native payload sidecars.
doctor           Validate registry and adapter wiring for all (or one) model(s).
profile          Profile a generation command (wall time, GPU memory, stage spans).
profile-summary  Aggregate resource profile JSON files.
prompt           Generate scene/task/camera prompts.
firstframe       Generate first-frame images from T2I prompts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _col(value: Any, width: int) -> str:
    """Left-justify *value* in a field of *width* characters."""
    return str(value).ljust(width)


def _print_table(rows: list[list[str]], headers: list[str]) -> None:
    """Print a simple fixed-width table to stdout."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    sep = "  ".join("-" * w for w in widths)
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print(sep)
    for row in rows:
        print("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))


# ---------------------------------------------------------------------------
# Sub-command: models
# ---------------------------------------------------------------------------

def _cmd_models(args: argparse.Namespace) -> int:
    import wrcam

    records = wrcam.all_records()
    if not args.deferred:
        records = [r for r in records if not r.is_deferred]

    if args.json:
        data = []
        for r in records:
            data.append(
                {
                    "key": r.key,
                    "aliases": list(r.aliases),
                    "status": r.status,
                    "input_kind": r.input_kind,
                    "adapter": r.adapter,
                    "payload_type": r.payload_type,
                    "calibration_status": r.amplitude.calibration_status,
                    "rotation_gain": r.amplitude.rotation_gain,
                    "translation_gain": r.amplitude.translation_gain,
                    "max_amount": r.amplitude.max_amount,
                    "translation_unit": r.amplitude.translation_unit,
                    "capabilities": r.capabilities,
                    "notes": r.notes,
                    "is_deferred": r.is_deferred,
                }
            )
        print(json.dumps(data, indent=2))
        return 0

    rows = [
        [r.key, r.input_kind, r.adapter, r.payload_type, r.amplitude.calibration_status]
        for r in records
    ]
    _print_table(rows, ["key", "input_kind", "adapter", "payload_type", "calibration_status"])
    return 0


# ---------------------------------------------------------------------------
# Sub-command: presets
# ---------------------------------------------------------------------------

def _cmd_presets(args: argparse.Namespace) -> int:
    import wrcam

    names = wrcam.presets.preset_names()
    descriptions = {
        "static": "Hold the camera still for the entire clip.",
        "yaw_LR": "Yaw left to peak_deg, then return right (go-return).",
        "yaw_RL": "Yaw right to peak_deg, then return left (go-return).",
        "pan_LR": "Pan left then return right (go-return).",
        "pan_RL": "Pan right then return left (go-return).",
    }

    if args.json:
        data = []
        for name in names:
            script = wrcam.presets.build_preset(name)
            data.append(
                {
                    "name": name,
                    "description": descriptions.get(name, ""),
                    "default_script": script.to_string(),
                    "default_frame_count": script.frame_count,
                }
            )
        print(json.dumps(data, indent=2))
        return 0

    rows = []
    for name in names:
        script = wrcam.presets.build_preset(name)
        desc = descriptions.get(name, "")
        rows.append([name, desc, script.to_string()])
    _print_table(rows, ["name", "description", "default_expansion"])
    return 0


# ---------------------------------------------------------------------------
# Sub-command: actions
# ---------------------------------------------------------------------------

def _cmd_actions(args: argparse.Namespace) -> int:
    import wrcam

    camera_text: str = args.camera
    fps: int = args.fps

    try:
        script = wrcam.parse_camera_script(camera_text, fps=fps)
    except (ValueError, KeyError) as exc:
        print(f"error: invalid camera script: {exc}", file=sys.stderr)
        return 1

    normalized = script.to_string()
    frame_count = script.frame_count

    segments = []
    for action in script.actions:
        seg: dict[str, Any] = {
            "kind": action.kind,
            "direction": action.direction,
            "frames": action.frames,
        }
        if action.degrees is not None:
            seg["value"] = action.degrees
            seg["value_unit"] = "degrees"
        elif action.amount is not None:
            seg["value"] = action.amount
            seg["value_unit"] = "amount"
        else:
            seg["value"] = None
            seg["value_unit"] = None
        segments.append(seg)

    if args.json:
        print(
            json.dumps(
                {
                    "normalized_script": normalized,
                    "frame_count": frame_count,
                    "fps": fps,
                    "segments": segments,
                },
                indent=2,
            )
        )
        return 0

    print(f"normalized : {normalized}")
    print(f"frame_count: {frame_count if frame_count is not None else '(unset)'}")
    print(f"fps        : {fps}")
    print()
    rows = []
    for i, seg in enumerate(segments):
        value_str = str(seg["value"]) if seg["value"] is not None else "-"
        unit_str = seg["value_unit"] or "-"
        rows.append([str(i), seg["kind"], seg["direction"], value_str, unit_str, str(seg["frames"])])
    _print_table(rows, ["#", "kind", "direction", "value", "unit", "frames"])
    return 0


# ---------------------------------------------------------------------------
# Sub-command: generate
# ---------------------------------------------------------------------------

def _resolve_preset_camera(camera_str: str, args: argparse.Namespace):
    """Return a CameraScript or camera string for ``--camera preset:<name>``."""
    import wrcam

    if not camera_str.startswith("preset:"):
        return camera_str  # raw script string

    preset_name = camera_str[len("preset:"):]
    kwargs: dict[str, Any] = {}
    if args.peak_deg is not None:
        kwargs["peak_deg"] = args.peak_deg
    if args.amount is not None:
        kwargs["amount"] = args.amount
    if args.frames is not None:
        kwargs["frames"] = args.frames

    try:
        script = wrcam.presets.build_preset(preset_name, **kwargs)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        names = wrcam.presets.preset_names()
        print(f"  valid presets: {', '.join(names)}", file=sys.stderr)
        raise SystemExit(1)
    return script


def _cmd_generate(args: argparse.Namespace) -> int:
    import wrcam

    model_name: str = args.model
    camera_arg: str = args.camera
    out_path: str = args.out
    dry_run: bool = not args.no_dry_run

    # Resolve model key early so errors are clear
    try:
        key = wrcam.canonical_model_key(model_name)
    except KeyError:
        known = wrcam.list_models(include_deferred=True)
        print(f"error: unknown model {model_name!r}", file=sys.stderr)
        print(f"  known models: {', '.join(known)}", file=sys.stderr)
        return 1

    # Check deferred status
    record = wrcam.model_record(key)
    if record.is_deferred:
        print(
            f"error: model {key!r} is deferred (not yet dispatchable). "
            "Generation is not supported for deferred models.",
            file=sys.stderr,
        )
        return 1

    # Resolve camera
    camera = _resolve_preset_camera(camera_arg, args)

    # Validate inputs based on input_kind
    input_kind = record.input_kind
    image_path: str | None = args.image
    source_video_path: str | None = args.source_video

    if input_kind == "image":
        if source_video_path:
            print(
                f"error: model {key!r} is an image/TI2V model; use --image, not --source-video.",
                file=sys.stderr,
            )
            return 1
        if not image_path:
            print(
                f"error: model {key!r} is an image/TI2V model and requires --image <path>.",
                file=sys.stderr,
            )
            return 1
    elif input_kind == "source_video":
        if image_path:
            print(
                f"error: model {key!r} is a source-video/V2V model; use --source-video, not --image.",
                file=sys.stderr,
            )
            return 1
        if not source_video_path:
            print(
                f"error: model {key!r} is a source-video/V2V model and requires --source-video <path>.",
                file=sys.stderr,
            )
            return 1

    if args.no_dry_run:
        from wrcam.backends.registry import resolve_backend

        backend = resolve_backend(key)
        if hasattr(backend, "available_for"):
            ok, reason = backend.available_for(key)  # type: ignore[attr-defined]
        else:
            ok, reason = backend.available()
        if not ok:
            print(
                f"error: --no-dry-run requested but no real backend is available for {key!r}: {reason}",
                file=sys.stderr,
            )
            print(
                "  Configure wrcam.runtime.json (see wrcam.runtime.example.json) "
                "or omit --no-dry-run to compile sidecars only.",
                file=sys.stderr,
            )
            return 1
        dry_run = False

    try:
        result = wrcam.compile_camera(
            model=key,
            camera=camera,
            out=out_path,
            image=image_path,
            source_video=source_video_path,
            prompt=args.prompt,
            width=args.width,
            height=args.height,
            fps=args.fps,
            num_frames=args.num_frames,
            work_dir=args.work_dir,
            dry_run=dry_run,
        )
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    artifacts: dict[str, str] = result.get("artifacts", {})
    payload = result.get("payload")
    print(f"model    : {result['model']}")
    print(f"dry_run  : {result['dry_run']}")
    print("artifacts:")
    for name, path in artifacts.items():
        exists_mark = " (written)" if Path(path).exists() else " (missing)"
        print(f"  {name}: {path}{exists_mark}")
    generation = result.get("generation")
    if generation:
        print(f"generation: success={generation.get('success')} message={generation.get('message')}")
        if generation.get("output_path"):
            print(f"  output: {generation['output_path']}")
    return 0


# ---------------------------------------------------------------------------
# Sub-command: doctor
# ---------------------------------------------------------------------------

def _doctor_check_model(key: str) -> tuple[bool, list[str]]:
    """Run all doctor checks for one model key. Returns (pass, [lines])."""
    lines: list[str] = []

    # Import here to ensure adapter registry is populated
    import wrcam
    from wrcam.adapters.base import adapter_for_model, registered_model_keys

    # Check 1: registry record loads
    try:
        record = wrcam.model_record(key)
    except Exception as exc:
        lines.append(f"  FAIL  registry: {exc}")
        return False, lines

    lines.append(f"  pass  registry: record loaded (status={record.status})")

    # Deferred models: that is a pass for doctor
    if record.is_deferred:
        lines.append(f"  pass  deferred: model is deferred/not-dispatchable (expected)")
        lines.append(f"  PASS  {key}  [deferred]")
        return True, lines

    # Check 2: input_kind is valid
    from wrcam.registry import VALID_INPUT_KINDS
    if record.input_kind not in VALID_INPUT_KINDS:
        lines.append(f"  FAIL  input_kind: {record.input_kind!r} is not valid")
        return False, lines
    lines.append(f"  pass  input_kind: {record.input_kind}")

    # Check 3: adapter is registered
    if key not in registered_model_keys():
        lines.append(f"  FAIL  adapter: no adapter registered for {key!r}")
        return False, lines
    try:
        adapter = adapter_for_model(key)
        lines.append(f"  pass  adapter: {type(adapter).__name__}")
    except Exception as exc:
        lines.append(f"  FAIL  adapter: {exc}")
        return False, lines

    # Check 4: dry-run compile of static@16
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "doctor_test.mp4")
        dummy_image = os.path.join(tmp, "dummy_image.png")
        dummy_video = os.path.join(tmp, "dummy_video.mp4")
        # Create dummy files so path presence is satisfied
        Path(dummy_image).write_bytes(b"")
        Path(dummy_video).write_bytes(b"")

        caps = record.capabilities or {}
        if caps.get("supports_static", True):
            camera = "static@16"
        else:
            camera = wrcam.presets.yaw_LR(peak_deg=30, frames=int(record.default_frames)).to_string()

        compile_kwargs: dict[str, Any] = {
            "model": key,
            "camera": camera,
            "out": out,
            "dry_run": True,
        }
        if record.input_kind == "image":
            compile_kwargs["image"] = dummy_image
        else:
            compile_kwargs["source_video"] = dummy_video

        try:
            result = wrcam.compile_camera(**compile_kwargs)
            artifacts = result.get("artifacts", {})
            written = [p for p in artifacts.values() if Path(p).exists()]
            lines.append(f"  pass  dry-run: compile succeeded, {len(written)} artifacts written")
        except Exception as exc:
            lines.append(f"  FAIL  dry-run: {exc}")
            return False, lines

    lines.append(f"  PASS  {key}")
    return True, lines


def _cmd_doctor(args: argparse.Namespace) -> int:
    import wrcam

    if args.all:
        all_rec = wrcam.all_records()
        targets = [r.key for r in all_rec]
    elif args.model:
        try:
            targets = [wrcam.canonical_model_key(args.model)]
        except KeyError:
            known = wrcam.list_models(include_deferred=True)
            print(f"error: unknown model {args.model!r}", file=sys.stderr)
            print(f"  known models: {', '.join(known)}", file=sys.stderr)
            return 1
    else:
        # Default: active models only
        targets = wrcam.list_models(include_deferred=False)

    if not targets:
        print("No models to check.")
        return 0

    total = len(targets)
    passed = 0
    failed_keys: list[str] = []

    for key in targets:
        print(f"\n[{key}]")
        ok, lines = _doctor_check_model(key)
        for line in lines:
            print(line)
        if ok:
            passed += 1
        else:
            failed_keys.append(key)

    print(f"\n{'='*60}")
    print(f"Summary: {passed}/{total} passed")
    if failed_keys:
        print(f"Failed:  {', '.join(failed_keys)}")
        return 1
    print("All checks passed.")
    return 0


# ---------------------------------------------------------------------------
# Sub-command: profile
# ---------------------------------------------------------------------------

def _cmd_profile(args: argparse.Namespace) -> int:
    from wrcam.profiling import run_profiled_command

    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("profile: missing command after --", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or "run"
    summary = out_dir / f"{stem}.resource_profile.json"
    trace = out_dir / f"{stem}.resource_trace.jsonl" if not args.no_trace else None
    events = out_dir / f"{stem}.stage_events.jsonl"
    log = out_dir / f"{stem}.generation.log" if args.log else None

    profile = run_profiled_command(
        cmd,
        cwd=args.cwd,
        summary_path=summary,
        trace_path=trace,
        stage_events_path=events,
        log_path=log,
        run_identity={
            "model": args.model or "",
            "profile": args.profile or "",
            "camera": args.camera or "",
            "scene_id": args.scene_id or "",
            "gpu_width": args.gpu_width,
            "output_video_seconds": args.output_video_seconds,
        },
        sampling_interval_seconds=args.sampling_interval,
        generation_status=args.generation_status,
    )
    if args.json:
        print(json.dumps(profile, indent=2))
    else:
        dm = profile.get("derived_metrics", {})
        print(f"Summary: {summary}")
        print(f"exit_code={profile['status']['exit_code']} wall={profile['status']['wall_time_seconds']:.3f}s")
        bg = dm.get("benchmark_generation_seconds")
        if bg is not None:
            print(f"benchmark_generation_seconds={bg:.3f}")
        gpus = dm.get("benchmark_gpu_seconds_per_output_second")
        if gpus is not None:
            print(f"benchmark_gpu_seconds_per_output_second={gpus:.3f}")
    return int(profile["status"]["exit_code"])


# ---------------------------------------------------------------------------
# Sub-command: profile-summary
# ---------------------------------------------------------------------------

def _cmd_profile_summary(args: argparse.Namespace) -> int:
    from wrcam.profiling import format_rows, load_profiles, summarize

    rows = summarize(load_profiles([Path(p) for p in args.paths]))
    text = format_rows(rows, args.format)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


# ---------------------------------------------------------------------------
# Sub-command: prompt
# ---------------------------------------------------------------------------

def _cmd_prompt(args: argparse.Namespace) -> int:
    if args.prompt_command == "camera":
        from wrcam.prompts.camera_text import (
            assemble_ti2v_prompt,
            build_prompt_to_send,
            preset_camera_text,
        )

        if args.preset:
            text = preset_camera_text(args.preset, pronoun=args.pronoun, offscreen_area=args.offscreen_area)
            result = {"preset": args.preset, "camera_text": text}
        elif args.assemble:
            result = {
                "ti2v_prompt": assemble_ti2v_prompt(
                    args.scene_start,
                    args.event,
                    args.pronoun,
                    args.offscreen_area,
                    args.gap,
                )
            }
        elif args.model and args.source_prompt:
            result = {
                "prompt_to_send": build_prompt_to_send(
                    args.source_prompt,
                    args.camera_motion,
                    model=args.model,
                )
            }
        else:
            print("prompt camera: use --preset, --assemble, or --model + --source-prompt", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if args.prompt_command == "scene":
        from wrcam.prompts.scene import enrich_family_with_t2i_scene

        family = json.loads(Path(args.family_json).read_text(encoding="utf-8"))
        enriched = enrich_family_with_t2i_scene(
            family,
            model=args.model,
            temperature=args.temperature,
            provider=args.provider,
        )
        print(json.dumps(enriched, indent=2, ensure_ascii=False))
        return 0

    if args.prompt_command == "task":
        from wrcam.prompts.task import (
            generate_variants_deterministic,
            load_jsonl,
            write_jsonl,
        )

        if args.deterministic:
            candidates = json.loads(Path(args.candidates_json).read_text(encoding="utf-8"))
            families = {r["family_id"]: r for r in load_jsonl(args.families_jsonl)}
            variants = generate_variants_deterministic(candidates, families)
            if args.output:
                write_jsonl(args.output, variants)
                print(f"Wrote {len(variants)} variants to {args.output}")
            else:
                print(json.dumps(variants[:3], indent=2, ensure_ascii=False))
                if len(variants) > 3:
                    print(f"... and {len(variants) - 3} more")
            return 0

        print("prompt task: only --deterministic path is implemented without LLM; use scene+LLM for tier groups", file=sys.stderr)
        return 2

    print(f"Unknown prompt subcommand: {args.prompt_command}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Sub-command: firstframe
# ---------------------------------------------------------------------------

def _cmd_firstframe(args: argparse.Namespace) -> int:
    from wrcam.firstframe import generate_first_frame, generate_first_frames_from_families, write_manifest
    from wrcam.prompts.task import load_jsonl

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.families_jsonl:
        families = list(load_jsonl(args.families_jsonl))
        manifests = generate_first_frames_from_families(
            families,
            out_dir=out_dir,
            provider=args.provider,
            model=args.model,
            skip_existing=not args.force,
        )
    elif args.prompt and args.family_id:
        manifests = [
            generate_first_frame(
                family_id=args.family_id,
                prompt=args.prompt,
                out_dir=out_dir,
                provider=args.provider,
                model=args.model,
            )
        ]
    else:
        print("firstframe: provide --families-jsonl or --family-id + --prompt", file=sys.stderr)
        return 2

    manifest_path = out_dir / "first_frames_manifest.json"
    write_manifest(manifest_path, manifests)
    print(f"Generated {len(manifests)} frame(s); manifest: {manifest_path}")
    for m in manifests:
        print(f"  {m.family_id} -> {m.image_path}")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wrcam",
        description="Unified camera control for video-generation models.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    # models
    p_models = sub.add_parser("models", help="List supported models.")
    p_models.add_argument(
        "--json", action="store_true", help="Output full records as a JSON array."
    )
    p_models.add_argument(
        "--deferred", action="store_true", help="Include deferred (not-yet-dispatchable) models."
    )

    # presets
    p_presets = sub.add_parser("presets", help="List preset camera motions.")
    p_presets.add_argument("--json", action="store_true", help="Output as JSON.")

    # actions
    p_actions = sub.add_parser(
        "actions", help="Parse and validate a frame-action camera script."
    )
    p_actions.add_argument(
        "--camera",
        required=True,
        metavar="SCRIPT",
        help='Camera script, e.g. "yaw:left:60@40,yaw:right:60@41".',
    )
    p_actions.add_argument(
        "--fps", type=int, default=16, metavar="N", help="Frames per second (default: 16)."
    )
    p_actions.add_argument("--json", action="store_true", help="Output as JSON.")

    # generate
    p_gen = sub.add_parser(
        "generate", help="Compile a camera script and write model-native payload sidecars."
    )
    p_gen.add_argument("--model", required=True, metavar="MODEL", help="Target model key.")
    p_gen.add_argument(
        "--camera",
        required=True,
        metavar="SCRIPT",
        help=(
            'Camera script or "preset:<name>", e.g. "yaw:left:60@40" or "preset:yaw_LR". '
            "Combine with --peak-deg, --amount, --frames to parametrize presets."
        ),
    )
    p_gen.add_argument("--out", required=True, metavar="PATH", help="Output file path (e.g. out.mp4).")
    p_gen.add_argument("--image", metavar="PATH", help="Input image (required for TI2V models).")
    p_gen.add_argument(
        "--source-video", metavar="PATH", dest="source_video",
        help="Input source video (required for V2V models).",
    )
    p_gen.add_argument("--prompt", default="", metavar="TEXT", help="Text prompt.")
    p_gen.add_argument("--width", type=int, default=832, metavar="N", help="Frame width (default: 832).")
    p_gen.add_argument("--height", type=int, default=480, metavar="N", help="Frame height (default: 480).")
    p_gen.add_argument("--fps", type=int, default=16, metavar="N", help="Frames per second (default: 16).")
    p_gen.add_argument(
        "--num-frames", type=int, default=None, dest="num_frames",
        metavar="N", help="Override total frame count.",
    )
    p_gen.add_argument("--work-dir", metavar="DIR", dest="work_dir", help="Working directory for scratch files.")
    p_gen.add_argument(
        "--no-dry-run",
        action="store_true",
        dest="no_dry_run",
        help=(
            "Disable dry-run mode. NOTE: real generation requires a backend that is not yet "
            "wired; this flag currently behaves like dry-run and emits a warning."
        ),
    )
    # Preset parametrisation flags
    p_gen.add_argument(
        "--peak-deg", type=float, default=None, dest="peak_deg",
        metavar="DEG", help="Override preset peak_deg (yaw/pitch presets).",
    )
    p_gen.add_argument(
        "--amount", type=float, default=None,
        metavar="A", help="Override preset amount (translation presets).",
    )
    p_gen.add_argument(
        "--frames", type=int, default=None,
        metavar="N", help="Override preset total frame count.",
    )

    # profile
    p_prof = sub.add_parser("profile", help="Profile a generation command.")
    p_prof.add_argument("--out-dir", default=".", metavar="DIR", help="Output directory for profile artifacts.")
    p_prof.add_argument("--name", default="run", metavar="NAME", help="Artifact filename stem.")
    p_prof.add_argument("--model", default="", metavar="MODEL")
    p_prof.add_argument("--profile", default="", metavar="PROFILE")
    p_prof.add_argument("--camera", default="", metavar="CAMERA")
    p_prof.add_argument("--scene-id", default="", dest="scene_id", metavar="ID")
    p_prof.add_argument("--gpu-width", type=int, default=1, dest="gpu_width")
    p_prof.add_argument("--output-video-seconds", type=float, default=None, dest="output_video_seconds")
    p_prof.add_argument("--generation-status", default=None, dest="generation_status")
    p_prof.add_argument("--sampling-interval", type=float, default=0.5, dest="sampling_interval")
    p_prof.add_argument("--cwd", default=os.getcwd(), metavar="DIR")
    p_prof.add_argument("--log", action="store_true", help="Capture command stdout/stderr to a log file.")
    p_prof.add_argument("--no-trace", action="store_true", help="Skip GPU trace JSONL.")
    p_prof.add_argument("--json", action="store_true", help="Print full profile JSON to stdout.")
    p_prof.add_argument("cmd", nargs=argparse.REMAINDER, help="Command after --")

    # profile-summary
    p_psum = sub.add_parser("profile-summary", help="Summarize resource profile JSON files.")
    p_psum.add_argument("paths", nargs="+", metavar="PATH", help="Profile JSON, JSONL, or directory.")
    p_psum.add_argument("--format", choices=("json", "csv", "markdown"), default="json")
    p_psum.add_argument("--output", metavar="PATH")

    # prompt
    p_prompt = sub.add_parser("prompt", help="Generate scene/task/camera prompts.")
    p_prompt_sub = p_prompt.add_subparsers(dest="prompt_command", metavar="<kind>")
    p_prompt_sub.required = True

    p_cam = p_prompt_sub.add_parser("camera", help="Camera prompt text or API assembly.")
    p_cam.add_argument("--preset", metavar="NAME", help="wrcam preset name (yaw_LR, static, …).")
    p_cam.add_argument("--pronoun", default="they")
    p_cam.add_argument("--offscreen-area", default="empty floor space", dest="offscreen_area")
    p_cam.add_argument("--assemble", action="store_true", help="Assemble ti2v_prompt from parts.")
    p_cam.add_argument("--scene-start", default="", dest="scene_start")
    p_cam.add_argument("--event", default="")
    p_cam.add_argument("--gap", default="yaw_LR")
    p_cam.add_argument("--model", metavar="API_MODEL", help="API model for prompt_to_send assembly.")
    p_cam.add_argument("--source-prompt", dest="source_prompt", metavar="TEXT")
    p_cam.add_argument("--camera-motion", default="yaw_LR", dest="camera_motion")

    p_scene = p_prompt_sub.add_parser("scene", help="Generate t2i_scene via LLM (requires wrcam[prompts]).")
    p_scene.add_argument("--family-json", required=True, dest="family_json", metavar="PATH")
    p_scene.add_argument("--model", default=None)
    p_scene.add_argument("--provider", default=None)
    p_scene.add_argument("--temperature", type=float, default=0.2)

    p_task = p_prompt_sub.add_parser("task", help="Generate ti2v variant prompts.")
    p_task.add_argument("--deterministic", action="store_true", help="Deterministic Natural-25 style path.")
    p_task.add_argument("--candidates-json", dest="candidates_json", metavar="PATH")
    p_task.add_argument("--families-jsonl", dest="families_jsonl", metavar="PATH")
    p_task.add_argument("--output", metavar="PATH")

    # firstframe
    p_ff = sub.add_parser("firstframe", help="Generate first-frame images.")
    p_ff.add_argument("--out", required=True, metavar="DIR", help="Output directory for PNGs.")
    p_ff.add_argument("--families-jsonl", dest="families_jsonl", metavar="PATH")
    p_ff.add_argument("--family-id", dest="family_id", metavar="ID")
    p_ff.add_argument("--prompt", metavar="TEXT", help="T2I prompt (with --family-id).")
    p_ff.add_argument("--provider", default="mock", help="T2I provider: dashscope, mock (default: mock).")
    p_ff.add_argument("--model", default=None, help="T2I model name.")
    p_ff.add_argument("--force", action="store_true", help="Regenerate even if PNG exists.")

    # doctor
    p_doc = sub.add_parser(
        "doctor", help="Validate registry and adapter wiring."
    )
    model_group = p_doc.add_mutually_exclusive_group()
    model_group.add_argument(
        "--model", metavar="MODEL", help="Check a single model."
    )
    model_group.add_argument(
        "--all", action="store_true", help="Check all models including deferred."
    )

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

_DISPATCH = {
    "models": _cmd_models,
    "presets": _cmd_presets,
    "actions": _cmd_actions,
    "generate": _cmd_generate,
    "doctor": _cmd_doctor,
    "profile": _cmd_profile,
    "profile-summary": _cmd_profile_summary,
    "prompt": _cmd_prompt,
    "firstframe": _cmd_firstframe,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _DISPATCH.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
