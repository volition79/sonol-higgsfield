#!/usr/bin/env python3
"""Command-line controller for a sonol-higgsfield production."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import project_state as state
import cinematography


SKILL_ROOT = Path(__file__).resolve().parent.parent


def json_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def json_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return value


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    cmd = sub.add_parser("init", help="initialize a production directory")
    cmd.add_argument("production")
    cmd.add_argument("--name", required=True)

    cmd = sub.add_parser("recommend-grammar", help="recommend intent-first shot grammar plans")
    cmd.add_argument("intent")
    cmd.add_argument("--genre", default="general")
    cmd.add_argument("--platform", default="general")
    cmd.add_argument("--subject-priority", choices=("balanced", "emotion", "space", "product", "action"), default="balanced")
    cmd.add_argument("--stability", choices=("balanced", "stable", "unstable"), default="balanced")
    cmd.add_argument("--provider")
    cmd.add_argument("--duration", type=float, default=5.0)
    cmd.add_argument("--top", type=int, choices=(1, 2, 3), default=3)

    for name in ("validate", "dashboard", "show"):
        cmd = sub.add_parser(name)
        cmd.add_argument("production")

    cmd = sub.add_parser("migrate", help="upgrade a v1-v3 production to the current schema")
    cmd.add_argument("production")

    cmd = sub.add_parser("validate-grammar", help="validate one production shot grammar")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("--complete", action="store_true")

    cmd = sub.add_parser("compile-grammar", help="compile and optionally apply one shot grammar")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("--provider", required=True)
    cmd.add_argument("--subject", required=True)
    cmd.add_argument("--setting", required=True)
    cmd.add_argument("--action", required=True)
    cmd.add_argument("--exit-state", required=True)
    cmd.add_argument("--invariant", action="append", default=[])
    cmd.add_argument("--live-schema", type=Path)
    cmd.add_argument("--apply", action="store_true")
    cmd.add_argument("--actor", default="agent")

    cmd = sub.add_parser("set-requirement")
    cmd.add_argument("production")
    cmd.add_argument("field", choices=state.REQUIRED_REQUIREMENTS)
    cmd.add_argument("value", type=json_value)
    cmd.add_argument("--status", choices=sorted(state.REQUIREMENT_STATES), required=True)
    cmd.add_argument("--actor", default="agent")
    cmd.add_argument("--source")

    cmd = sub.add_parser("lock-requirements")
    cmd.add_argument("production")
    cmd.add_argument("--actor", default="user")

    cmd = sub.add_parser("approve-budget")
    cmd.add_argument("production")
    cmd.add_argument("max_credits", type=float)
    cmd.add_argument("--actor", default="user")

    cmd = sub.add_parser("add-asset")
    cmd.add_argument("production")
    cmd.add_argument("asset_id")
    cmd.add_argument("asset_type")
    cmd.add_argument("label")

    cmd = sub.add_parser("update-asset")
    cmd.add_argument("production")
    cmd.add_argument("asset_id")
    cmd.add_argument("patch", type=json_object)
    cmd.add_argument("--actor", default="agent")

    cmd = sub.add_parser("transition-asset")
    cmd.add_argument("production")
    cmd.add_argument("asset_id")
    cmd.add_argument("target", choices=sorted(state.ASSET_STATES))
    cmd.add_argument("--actor", default="agent")
    cmd.add_argument("--reason", default="")

    cmd = sub.add_parser("add-scene")
    cmd.add_argument("production")
    cmd.add_argument("scene_id")
    cmd.add_argument("title")
    cmd.add_argument("order", type=int)

    cmd = sub.add_parser("add-shot")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("scene_id")
    cmd.add_argument("title")
    cmd.add_argument("order", type=int)

    cmd = sub.add_parser("update-shot")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("patch", type=json_object)
    cmd.add_argument("--actor", default="agent")

    cmd = sub.add_parser("set-boundary")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("strategy", choices=sorted(state.BOUNDARY_STRATEGIES))
    cmd.add_argument("--reason", required=True)
    cmd.add_argument("--previous-shot-id")
    cmd.add_argument("--previous-frame")
    cmd.add_argument("--planned-keyframe")
    cmd.add_argument("--cut-type")
    cmd.add_argument("--actor", default="agent")

    cmd = sub.add_parser("transition-shot")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("target", choices=sorted(state.SHOT_APPROVAL_STATES))
    cmd.add_argument("--actor", default="agent")
    cmd.add_argument("--reason", default="")

    cmd = sub.add_parser("transition-generation")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("target", choices=sorted(state.GENERATION_STATES))
    cmd.add_argument("--actor", default="agent")
    cmd.add_argument("--reason", default="")

    cmd = sub.add_parser("set-qc")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("check")
    cmd.add_argument("status", choices=sorted(state.QC_STATES))
    cmd.add_argument("--actor", default="agent")
    cmd.add_argument("--note", default="")

    cmd = sub.add_parser("record-job")
    cmd.add_argument("production")
    cmd.add_argument("shot_id")
    cmd.add_argument("job_id")
    cmd.add_argument("--result-path")
    cmd.add_argument("--actor", default="agent")

    cmd = sub.add_parser("record-cost")
    cmd.add_argument("production")
    cmd.add_argument("entity_id")
    cmd.add_argument("credits", type=float)
    cmd.add_argument("--job-id")
    cmd.add_argument("--actor", default="agent")
    return root


def execute(args: argparse.Namespace) -> Any:
    if args.command == "recommend-grammar":
        return cinematography.recommend(
            args.intent, genre=args.genre, platform=args.platform,
            subject_priority=args.subject_priority, stability=args.stability,
            provider=args.provider, duration_seconds=args.duration, top_n=args.top,
        )
    p = args.production
    if args.command == "init":
        return {"production": str(state.initialize(p, args.name, SKILL_ROOT / "assets" / "dashboard-template"))}
    if args.command == "validate":
        errors = state.validate(p)
        if errors:
            raise state.StateError("validation failed:\n- " + "\n- ".join(errors))
        return {"valid": True}
    if args.command == "migrate":
        return state.migrate(p)
    if args.command in {"validate-grammar", "compile-grammar"}:
        shots = state.read_json(state.data_dir(p) / "shots.json").get("items", [])
        shot = next((item for item in shots if item.get("id") == args.shot_id), None)
        if shot is None:
            raise state.StateError(f"unknown shot: {args.shot_id}")
        if args.command == "validate-grammar":
            errors, warnings = cinematography.validate_grammar(
                shot.get("shot_grammar", {}), require_complete=args.complete,
                shot_duration=shot.get("duration_seconds"),
            )
            return {"valid": not errors, "errors": errors, "warnings": warnings}
        live_schema = None
        if args.live_schema:
            try:
                live_schema = json.loads(args.live_schema.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise state.StateError(f"cannot read live schema: {exc}") from exc
        compiled = cinematography.compile_prompt(
            shot.get("shot_grammar", {}), provider=args.provider,
            subject=args.subject, setting=args.setting, action=args.action,
            exit_state=args.exit_state, invariants=args.invariant, live_schema=live_schema,
            seedance_plan=shot.get("seedance_plan"), references=shot.get("references"),
        )
        grammar = cinematography.apply_compilation(shot.get("shot_grammar", {}), compiled)
        if args.apply:
            state.update_shot(p, args.shot_id, {"shot_grammar": grammar}, args.actor)
        return {"applied": args.apply, "compiled": compiled, "shot_grammar": grammar}
    if args.command == "dashboard":
        return {"dashboard": str(state.sync_dashboard(p))}
    if args.command == "show":
        return state.aggregate(p)
    if args.command == "set-requirement":
        state.set_requirement(p, args.field, args.value, args.status, args.actor, args.source)
    elif args.command == "lock-requirements":
        state.lock_requirements(p, args.actor)
    elif args.command == "approve-budget":
        state.approve_budget(p, args.max_credits, args.actor)
    elif args.command == "add-asset":
        state.add_asset(p, args.asset_id, args.asset_type, args.label)
    elif args.command == "update-asset":
        state.update_asset(p, args.asset_id, args.patch, args.actor)
    elif args.command == "transition-asset":
        state.transition_asset(p, args.asset_id, args.target, args.actor, args.reason)
    elif args.command == "add-scene":
        state.add_scene(p, args.scene_id, args.title, args.order)
    elif args.command == "add-shot":
        state.add_shot(p, args.shot_id, args.scene_id, args.title, args.order)
    elif args.command == "update-shot":
        state.update_shot(p, args.shot_id, args.patch, args.actor)
    elif args.command == "set-boundary":
        state.set_boundary(
            p,
            args.shot_id,
            args.strategy,
            args.actor,
            reason=args.reason,
            previous_shot_id=args.previous_shot_id,
            previous_frame=args.previous_frame,
            planned_keyframe=args.planned_keyframe,
            cut_type=args.cut_type,
        )
    elif args.command == "transition-shot":
        state.transition_shot_approval(p, args.shot_id, args.target, args.actor, args.reason)
    elif args.command == "transition-generation":
        state.transition_generation(p, args.shot_id, args.target, args.actor, args.reason)
    elif args.command == "set-qc":
        state.set_qc(p, args.shot_id, args.check, args.status, args.actor, args.note)
    elif args.command == "record-job":
        state.record_job(p, args.shot_id, args.job_id, args.result_path, args.actor)
    elif args.command == "record-cost":
        state.record_actual_cost(p, args.entity_id, args.credits, args.actor, args.job_id)
    return {"ok": True, "command": args.command}


def main() -> int:
    args = parser().parse_args()
    try:
        result = execute(args)
    except (state.StateError, cinematography.CinematographyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
