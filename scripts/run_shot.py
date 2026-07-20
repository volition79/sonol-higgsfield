#!/usr/bin/env python3
"""Execute one approved paid Higgsfield shot through the guarded CLI path."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import estimate_costs
import project_state as state
import cinematography
import execution_contract


def find_value(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and child is not None:
                return child
        for child in value.values():
            found = find_value(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_value(child, keys)
            if found is not None:
                return found
    return None


def provider_job_id(value: Any) -> str | None:
    """Accept only explicit job/generation identifiers in known response envelopes."""
    if not isinstance(value, dict):
        return None
    for key in ("job_id", "generation_id"):
        if isinstance(value.get(key), str) and value[key]:
            return value[key]
    for envelope in ("data", "result", "generation", "job"):
        child = value.get(envelope)
        if isinstance(child, dict):
            for key in ("job_id", "generation_id"):
                if isinstance(child.get(key), str) and child[key]:
                    return child[key]
    return None


def cli_json(command: list[str], timeout: int) -> Any:
    completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode:
        message = (completed.stderr or completed.stdout).strip()
        raise state.StateError(message[:1000] or f"provider command failed with {completed.returncode}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise state.StateError(f"provider returned invalid JSON: {exc}") from exc


def run_paid(
    production: Path,
    shot_id: str,
    executable: str,
    authorize_local_upload: bool,
    timeout: int,
) -> dict[str, Any]:
    documents = state.load_all(production)
    shot = next((item for item in documents["shots"].get("items", []) if item.get("id") == shot_id), None)
    if shot is None:
        raise state.StateError(f"unknown shot: {shot_id}")
    if shot.get("generation", {}).get("status") != "READY":
        raise state.StateError("shot generation status must be READY")
    if shot.get("generation", {}).get("job_id"):
        raise state.StateError("shot already has a provider job id")
    gates = state.shot_gate_errors(documents, shot)
    if gates:
        raise state.StateError("generation gate failed: " + "; ".join(gates))

    approval = documents["project"].get("cost_approval", {})
    scenario = approval.get("scenario")
    estimate = next(
        (
            item
            for item in documents["costs"].get("task_estimates", [])
            if item.get("shot_id") == shot_id and item.get("scenario") == scenario
        ),
        None,
    )
    if estimate is None:
        raise state.StateError("approved scenario has no exact per-shot estimate")
    estimated_credits = float(estimate.get("credits", 0))
    actual_so_far = float(documents["costs"].get("actual", {}).get("credits", 0) or 0)
    ceiling = float(approval.get("max_credits"))
    if actual_so_far + estimated_credits > ceiling:
        raise state.StateError("estimated shot cost exceeds the remaining approved ceiling")

    execution = shot.get("generation", {}).get("execution", {})
    mode, argv = execution.get("mode"), execution.get("argv") or []
    if mode not in {"model", "workflow"} or not argv:
        raise state.StateError("shot has no executable model/workflow arguments")
    execution_fingerprint = execution_contract.fingerprint(mode, argv)
    if execution.get("fingerprint") not in {None, execution_fingerprint}:
        raise state.StateError("stored execution fingerprint does not match execution arguments")
    if estimate.get("execution_fingerprint") != execution_fingerprint:
        raise state.StateError("approved cost quote does not match the execution arguments")
    if approval.get("task_contracts", {}).get(shot_id) != execution_fingerprint:
        raise state.StateError("cost approval is not bound to this execution contract")

    provider, flags = execution_contract.parse_flags(argv)
    binding = shot.get("shot_grammar", {}).get("provider_binding", {})
    if not provider or provider != binding.get("provider"):
        raise state.StateError("execution provider does not match the compiled shot grammar")
    if flags.get("prompt") != binding.get("compiled_prompt"):
        raise state.StateError("execution prompt does not match the compiled shot grammar")
    for key, value in (binding.get("native_params") or {}).items():
        if flags.get(key) != value:
            raise state.StateError(f"execution native param does not match compiled grammar: {key}")
    expected_schema_hash = binding.get("schema_contract_hash")
    if not expected_schema_hash:
        raise state.StateError("compiled shot grammar has no live schema contract fingerprint")

    contract_command = [executable, "--json", "workflow" if mode == "workflow" else "model", "get", provider]
    current_contract = cli_json(contract_command, min(timeout, 60))
    if cinematography.stable_hash(current_contract) != expected_schema_hash:
        raise state.StateError("live provider contract changed after shot compilation; recompile and requote")
    uploads = estimate_costs.local_media_args(argv)
    if uploads and not authorize_local_upload:
        raise state.StateError(
            "execution references local media; rerun with --authorize-local-upload after approval: "
            + ", ".join(uploads)
        )

    account = cli_json([executable, "--json", "account", "status"], min(timeout, 60))
    available = find_value(account, {"credits"})
    if not isinstance(available, (int, float)) or isinstance(available, bool):
        raise state.StateError("could not verify available Higgsfield credits")
    if float(available) < estimated_credits:
        raise state.StateError(
            f"available credits {available} are below this shot estimate {estimated_credits}"
        )

    command = [executable, "--json", "generate", "create" if mode == "model" else "workflow", *argv]
    if "--wait" not in argv:
        command.append("--wait")
    state.transition_generation(production, shot_id, "QUEUED", "agent", "guarded paid execution")
    state.transition_generation(production, shot_id, "GENERATING", "agent", "provider command started")
    try:
        response = cli_json(command, timeout)
    except (state.StateError, subprocess.TimeoutExpired) as exc:
        state.transition_generation(production, shot_id, "FAILED", "agent", str(exc)[:500])
        if isinstance(exc, subprocess.TimeoutExpired):
            raise state.StateError("provider wait timed out; reconcile by job id before retry") from exc
        raise

    job_id = provider_job_id(response)
    if not isinstance(job_id, str) or not job_id:
        state.transition_generation(production, shot_id, "FAILED", "agent", "provider JSON had no job id")
        raise state.StateError("provider response did not expose a job id")
    state.record_job(production, shot_id, job_id, None, "agent")
    state.transition_generation(production, shot_id, "GENERATED", "agent", "provider wait completed")

    charged = find_value(response, {"credits", "credits_used", "cost_credits"})
    recorded = False
    reconciliation = False
    if isinstance(charged, (int, float)) and not isinstance(charged, bool):
        try:
            state.record_actual_cost(production, shot_id, float(charged), "agent", job_id)
            recorded = True
        except state.StateError:
            state.append_history(
                production,
                "actual_cost_reconciliation_required",
                "agent",
                "cost",
                shot_id,
                {"job_id": job_id, "reported_credits": float(charged)},
            )
            state.sync_dashboard(production)
            reconciliation = True
    else:
        state.append_history(
            production,
            "actual_cost_pending",
            "agent",
            "cost",
            shot_id,
            {"job_id": job_id},
        )
        state.sync_dashboard(production)
    return {
        "shot_id": shot_id,
        "job_id": job_id,
        "status": "GENERATED",
        "estimated_credits": estimated_credits,
        "actual_credits_recorded": recorded,
        "cost_reconciliation_required": reconciliation or not recorded,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("production", type=Path)
    parser.add_argument("shot_id")
    parser.add_argument("--execute-paid", action="store_true", help="required explicit paid-operation acknowledgement")
    parser.add_argument("--authorize-local-upload", action="store_true")
    parser.add_argument("--higgsfield", default="higgsfield")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if not args.execute_paid:
        print("error: refusing paid operation without --execute-paid", file=sys.stderr)
        return 2
    executable = shutil.which(args.higgsfield)
    if not executable:
        print(f"error: executable not found: {args.higgsfield}", file=sys.stderr)
        return 2
    try:
        result = run_paid(
            args.production.expanduser().resolve(),
            args.shot_id,
            executable,
            args.authorize_local_upload,
            args.timeout,
        )
    except state.StateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
