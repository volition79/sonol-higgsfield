#!/usr/bin/env python3
"""Estimate three production scenarios through the live Higgsfield CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import project_state as state
import execution_contract


SCENARIOS = ("economy", "recommended", "highest_quality")
def local_media_args(argv: list[str]) -> list[str]:
    return execution_contract.local_media_args(argv)


def parse_credits(payload: Any) -> float:
    if isinstance(payload, dict):
        for key in ("credits", "estimated_credits", "cost"):
            if isinstance(payload.get(key), (int, float)):
                return float(payload[key])
    raise state.StateError("Higgsfield cost response does not contain numeric credits")


def quote(argv: list[str], executable: str) -> tuple[float, dict[str, Any]]:
    command = [executable, "--json", "generate", "cost", *argv]
    completed = subprocess.run(command, text=True, capture_output=True, timeout=120, check=False)
    if completed.returncode:
        raise state.StateError((completed.stderr or completed.stdout).strip())
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise state.StateError(f"invalid cost JSON: {exc}") from exc
    return parse_credits(payload), payload


def estimate(production: Path, executable: str, allow_media_upload: bool) -> dict[str, float]:
    shots = state.read_json(state.data_dir(production) / "shots.json").get("items", [])
    totals = {name: 0.0 for name in SCENARIOS}
    estimates: list[dict[str, Any]] = []
    for shot in shots:
        execution = shot.get("generation", {}).get("execution") or {}
        mode = execution.get("mode")
        if mode not in {"model", "workflow"}:
            raise state.StateError(f"{shot.get('id')} has no execution mode for cost binding")
        options = shot.get("generation", {}).get("cost_options") or {}
        default = shot.get("generation", {}).get("cost_argv") or []
        if default and "recommended" not in options:
            options["recommended"] = default
        for scenario in SCENARIOS:
            argv = options.get(scenario)
            if not argv:
                continue
            uploads = local_media_args(argv)
            if uploads and not allow_media_upload:
                raise state.StateError(
                    f"{shot.get('id')} {scenario} cost check references local media; "
                    "rerun with --allow-media-upload only after authorizing upload: " + ", ".join(uploads)
                )
            credits, response = quote(argv, executable)
            totals[scenario] += credits
            estimates.append(
                {
                    "shot_id": shot.get("id"),
                    "scenario": scenario,
                    "credits": credits,
                    "argv": argv,
                    "execution_fingerprint": execution_contract.fingerprint(mode, argv),
                    "provider_response": response,
                }
            )
    missing = [name for name in SCENARIOS if not any(item["scenario"] == name for item in estimates)]
    if missing:
        raise state.StateError("missing explicit cost options for scenarios: " + ", ".join(missing))
    for scenario, total in totals.items():
        state.set_cost_scenario(production, scenario, round(total, 6), "agent")
    state.replace_task_estimates(production, estimates, "agent")
    return {key: round(value, 6) for key, value in totals.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("production", type=Path)
    parser.add_argument("--higgsfield", default="higgsfield")
    parser.add_argument("--allow-media-upload", action="store_true")
    args = parser.parse_args()
    if not shutil.which(args.higgsfield):
        print(f"error: executable not found: {args.higgsfield}", file=sys.stderr)
        return 2
    try:
        totals = estimate(args.production.resolve(), args.higgsfield, args.allow_media_upload)
    except state.StateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"scenarios": totals}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
