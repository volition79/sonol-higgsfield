#!/usr/bin/env python3
"""Execute one approved paid Higgsfield shot through the guarded CLI path."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
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
    if isinstance(value, list):
        value = value[0] if value and isinstance(value[0], dict) else None
    if not isinstance(value, dict):
        return None
    for key in ("job_id", "generation_id", "id"):
        if isinstance(value.get(key), str) and value[key]:
            return value[key]
    for envelope in ("data", "result", "generation", "job"):
        child = value.get(envelope)
        if isinstance(child, dict):
            for key in ("job_id", "generation_id", "id"):
                if isinstance(child.get(key), str) and child[key]:
                    return child[key]
    return None


def provider_job_objects(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    if provider_job_id(value):
        return [value]
    for envelope in ("data", "jobs", "results", "generations"):
        child = value.get(envelope)
        if isinstance(child, list):
            return [item for item in child if isinstance(item, dict)]
        if isinstance(child, dict):
            return [child]
    return []


def provider_status(value: Any) -> str | None:
    raw = find_value(value, {"status", "state"})
    return str(raw) if raw is not None else None


def normalize_provider_status(raw: str | None) -> str:
    value = (raw or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if value in {"completed", "complete", "succeeded", "success", "finished", "done"}:
        return "PROVIDER_COMPLETED"
    if value in {"failed", "failure", "error", "cancelled", "canceled", "rejected"}:
        return "FAILED"
    if value in {"running", "processing", "generating", "in_progress", "started"}:
        return "RUNNING"
    if value in {"queued", "pending", "created"}:
        return "QUEUED"
    if value in {"submitted", "accepted"}:
        return "SUBMITTED"
    return "REMOTE_UNKNOWN"


MATCH_FIELDS = ("duration", "aspect_ratio", "resolution", "generate_audio", "mode", "bitrate_mode")


def submission_match_signature(mode: str, argv: list[str]) -> dict[str, Any]:
    provider, flags = execution_contract.parse_flags(argv)
    prompt = flags.get("prompt")
    return {
        "provider": provider,
        "mode": mode,
        "prompt_sha256": (
            "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            if isinstance(prompt, str) and prompt
            else None
        ),
        "params": {key: flags[key] for key in MATCH_FIELDS if key in flags},
    }


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def candidate_matches_attempt(candidate: dict[str, Any], attempt: dict[str, Any]) -> bool:
    signature = attempt.get("match_signature")
    if not isinstance(signature, dict) or not signature.get("prompt_sha256"):
        return False
    if candidate.get("job_type") != signature.get("provider"):
        return False
    params = candidate.get("params")
    if not isinstance(params, dict):
        return False
    prompt = params.get("prompt")
    if not isinstance(prompt, str):
        return False
    prompt_hash = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if prompt_hash != signature.get("prompt_sha256"):
        return False
    expected_params = signature.get("params") or {}
    for key, expected in expected_params.items():
        if key not in params or params[key] != expected:
            return False
    started = _parse_time(attempt.get("started_at"))
    created = _parse_time(candidate.get("created_at"))
    if started is None or created is None:
        return False
    return started - timedelta(minutes=5) <= created <= started + timedelta(hours=2)


def without_wait_flags(argv: list[str]) -> list[str]:
    result: list[str] = []
    index = 0
    while index < len(argv):
        normalized = execution_contract.normalize_flag(argv[index])
        if normalized == "--wait":
            index += 1
            continue
        if normalized in {"--wait-timeout", "--wait-interval"}:
            index += 2
            continue
        result.append(argv[index])
        index += 1
    return result


def expand_media_args(argv: list[str]) -> list[str]:
    """Expand JSON-array media flag values into repeated CLI flags.

    The state contract stores list-valued media references as one JSON-array
    token so fingerprints and grammar bindings stay canonical, but the live
    Higgsfield CLI accepts one path or UUID per flag occurrence.
    """
    expanded: list[str] = []
    index = 0
    while index < len(argv):
        part = argv[index]
        normalized = execution_contract.normalize_flag(part) if part.startswith("--") else part
        if normalized in execution_contract.MEDIA_FLAGS and index + 1 < len(argv):
            try:
                decoded = json.loads(argv[index + 1])
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, list):
                for item in decoded:
                    expanded.extend((part, str(item)))
                index += 2
                continue
        expanded.append(part)
        index += 1
    return expanded


def cli_json(command: list[str], timeout: int) -> Any:
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise state.StateError(f"provider command timed out after {timeout}s") from exc
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
    acknowledge_pending_costs: bool = False,
) -> dict[str, Any]:
    documents = state.load_all(production)
    shot = next((item for item in documents["shots"].get("items", []) if item.get("id") == shot_id), None)
    if shot is None:
        raise state.StateError(f"unknown shot: {shot_id}")
    if shot.get("generation", {}).get("status") != "READY":
        raise state.StateError("shot generation status must be READY")
    if state.unresolved_submission(shot) or shot.get("generation", {}).get("job_id"):
        raise state.StateError("shot already has a provider attempt; reconcile it before another paid submission")
    gates = state.shot_gate_errors(documents, shot)
    if gates:
        raise state.StateError("generation gate failed: " + "; ".join(gates))

    approval = documents["project"].get("cost_approval", {})
    if approval.get("mode") != "PROJECT_CEILING" or not approval.get("unpriced_job_risk_acknowledged"):
        raise state.StateError("project ceiling does not acknowledge execution without a live quote")
    if (
        documents["costs"].get("actual", {}).get("reconciliation_required")
        and not acknowledge_pending_costs
    ):
        raise state.StateError(
            "actual credits are still unknown; reconcile them or rerun with --acknowledge-pending-costs"
        )
    actual_so_far = float(documents["costs"].get("actual", {}).get("credits", 0) or 0)
    ceiling = float(approval.get("max_credits"))
    remaining_ceiling = ceiling - actual_so_far
    if remaining_ceiling <= 0:
        raise state.StateError("approved project credit ceiling is exhausted")

    execution = shot.get("generation", {}).get("execution", {})
    mode, argv = execution.get("mode"), execution.get("argv") or []
    if mode not in {"model", "workflow"} or not argv:
        raise state.StateError("shot has no executable model/workflow arguments")
    execution_fingerprint = execution_contract.fingerprint(mode, argv)
    if execution.get("fingerprint") not in {None, execution_fingerprint}:
        raise state.StateError("stored execution fingerprint does not match execution arguments")
    profile = estimate_costs.execution_profile(mode, argv, fallback_duration=shot.get("duration_seconds"))
    reference_row = next(
        (
            item
            for item in documents["costs"].get("reference_estimates", {}).get("shots", [])
            if item.get("shot_id") == shot_id
            and item.get("status") == "REFERENCE_ONLY"
            and item.get("profile") == profile
        ),
        None,
    )
    reference_credits = float(reference_row["estimated_credits"]) if reference_row else None
    if reference_credits is not None and reference_credits > remaining_ceiling:
        raise state.StateError("reference arithmetic exceeds the remaining approved ceiling")

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
        raise state.StateError("live provider contract changed after shot compilation; recompile before execution")
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
    if float(available) <= 0:
        raise state.StateError("Higgsfield account has no available credits")
    if reference_credits is not None and float(available) < reference_credits:
        raise state.StateError(
            f"available credits {available} are below the reference arithmetic {reference_credits}"
        )

    command = [
        executable,
        "--json",
        "generate",
        "create" if mode == "model" else "workflow",
        *expand_media_args(without_wait_flags(argv)),
    ]
    attempt_id = state.start_submission_attempt(
        production,
        shot_id,
        "agent",
        provider=provider,
        mode=mode,
        execution_fingerprint=execution_fingerprint,
        match_signature=submission_match_signature(mode, argv),
        account_credits_before=float(available),
        cost_uncertainty_acknowledged=acknowledge_pending_costs,
    )
    try:
        response = cli_json(command, timeout)
    except KeyboardInterrupt:
        state.mark_submission_ambiguous(
            production,
            shot_id,
            "agent",
            "local execution was interrupted after the provider submission command started",
        )
        raise
    except (state.StateError, subprocess.TimeoutExpired) as exc:
        state.mark_submission_ambiguous(
            production,
            shot_id,
            "agent",
            "provider submission outcome is unknown: " + str(exc)[:500],
        )
        raise state.StateError(
            "provider submission outcome is ambiguous; reconcile provider history before retry"
        ) from exc

    job_id = provider_job_id(response)
    if not isinstance(job_id, str) or not job_id:
        state.mark_submission_ambiguous(
            production,
            shot_id,
            "agent",
            "provider accepted the command but its JSON exposed no recognized job id",
        )
        raise state.StateError("provider response did not expose a job id; reconcile provider history")
    state.record_job(production, shot_id, job_id, None, "agent")
    raw_status = provider_status(response)
    normalized_status = normalize_provider_status(raw_status)
    result_available = bool(find_value(response, {"result_url", "min_result_url", "output_url"}))
    if normalized_status == "REMOTE_UNKNOWN":
        normalized_status = "PROVIDER_COMPLETED" if result_available else "SUBMITTED"
    state.record_provider_observation(
        production,
        shot_id,
        normalized_status,
        "agent",
        raw_status=raw_status,
        result_available=result_available,
    )

    charged = find_value(response, {"credits", "credits_used", "cost_credits"})
    recorded = False
    if isinstance(charged, (int, float)) and not isinstance(charged, bool):
        state.record_actual_cost(
            production,
            shot_id,
            float(charged),
            "agent",
            job_id,
            execution_profile=profile,
        )
        recorded = True
    if normalized_status == "PROVIDER_COMPLETED" and not recorded:
        state.require_cost_reconciliation(
            production,
            shot_id,
            "agent",
            job_id=job_id,
            reported_credits=None,
            reason="provider response did not expose numeric credits",
        )
    if normalized_status == "PROVIDER_COMPLETED":
        state.finalize_provider_completion(production, shot_id, "agent")
    current = state.read_json(state.data_dir(production) / "shots.json")
    current_shot = next(item for item in current.get("items", []) if item.get("id") == shot_id)
    costs = state.read_json(state.data_dir(production) / "costs.json")["actual"]
    return {
        "shot_id": shot_id,
        "attempt_id": attempt_id,
        "job_id": job_id,
        "status": current_shot["generation"]["status"],
        "reference_estimated_credits": reference_credits,
        "remaining_ceiling_before_run": remaining_ceiling,
        "live_quote_used": False,
        "actual_credits_recorded": recorded,
        "cost_reconciliation_required": bool(costs.get("reconciliation_required")),
        "ceiling_breach": bool(costs.get("ceiling_breach")),
    }


def reconcile(
    production: Path,
    shot_id: str,
    executable: str,
    *,
    job_id: str | None,
    wait: bool,
    timeout: int,
    credits: float | None,
) -> dict[str, Any]:
    documents = state.load_all(production)
    shot = next((item for item in documents["shots"].get("items", []) if item.get("id") == shot_id), None)
    if shot is None:
        raise state.StateError(f"unknown shot: {shot_id}")
    existing_attempt = state.active_submission_attempt(production, shot_id)
    if existing_attempt is None and shot.get("generation", {}).get("status") in {"GENERATED", "FINAL_COMPLETE"}:
        existing_job_id = shot.get("generation", {}).get("job_id")
        if job_id and existing_job_id and job_id != existing_job_id:
            raise state.StateError("completed shot is already bound to a different provider job id")
        return {"shot_id": shot_id, "job_id": existing_job_id, "status": shot["generation"]["status"], "already_reconciled": True}
    if job_id:
        state.record_job(production, shot_id, job_id, None, "agent")
    attempt = state.active_submission_attempt(production, shot_id)
    if attempt is None:
        raise state.StateError("shot has no active provider attempt to reconcile")
    resolved_job_id = attempt.get("job_id")
    if not resolved_job_id:
        listing = cli_json([executable, "--json", "generate", "list", "--video", "--size", "100"], min(timeout, 60))
        linked_ids = set()
        for item in documents["shots"].get("items", []):
            if item.get("id") == shot_id:
                continue
            generation = item.get("generation") or {}
            linked_ids.add(generation.get("job_id"))
            linked_ids.update(
                attempt_item.get("job_id")
                for attempt_item in generation.get("attempts", [])
                if isinstance(attempt_item, dict)
            )
        candidates = [
            item
            for item in provider_job_objects(listing)
            if provider_job_id(item) not in linked_ids and candidate_matches_attempt(item, attempt)
        ]
        if len(candidates) != 1:
            reason = f"provider history match count is {len(candidates)}; manual --job-id is required"
            state.mark_submission_ambiguous(production, shot_id, "agent", reason)
            return {
                "shot_id": shot_id,
                "status": "SUBMISSION_AMBIGUOUS",
                "candidate_job_ids": [provider_job_id(item) for item in candidates if provider_job_id(item)],
                "message": reason,
            }
        resolved_job_id = provider_job_id(candidates[0])
        if not resolved_job_id:
            raise state.StateError("matched provider history item has no job id")
        state.record_job(production, shot_id, resolved_job_id, None, "agent")

    command = [executable, "--json", "generate", "wait" if wait else "get", str(resolved_job_id)]
    command_timeout = min(timeout, 60)
    if wait:
        command.extend(("--quiet", "--timeout", f"{timeout}s"))
        command_timeout = timeout + 10
    try:
        response = cli_json(command, command_timeout)
    except KeyboardInterrupt:
        state.record_provider_observation(
            production,
            shot_id,
            "REMOTE_UNKNOWN",
            "agent",
            raw_status=None,
            result_available=False,
        )
        raise
    except (state.StateError, subprocess.TimeoutExpired) as exc:
        state.record_provider_observation(
            production,
            shot_id,
            "REMOTE_UNKNOWN",
            "agent",
            raw_status=None,
            result_available=False,
        )
        raise state.StateError("provider observation was interrupted; the known job remains reconcilable") from exc

    raw_status = provider_status(response)
    normalized_status = normalize_provider_status(raw_status)
    result_available = bool(find_value(response, {"result_url", "min_result_url", "output_url"}))
    if normalized_status == "REMOTE_UNKNOWN" and result_available:
        normalized_status = "PROVIDER_COMPLETED"
    account_after = None
    try:
        account = cli_json([executable, "--json", "account", "status"], min(timeout, 60))
        available = find_value(account, {"credits"})
        if isinstance(available, (int, float)) and not isinstance(available, bool):
            account_after = float(available)
    except state.StateError:
        account_after = None
    state.record_provider_observation(
        production,
        shot_id,
        normalized_status,
        "agent",
        raw_status=raw_status,
        result_available=result_available,
        account_credits_after=account_after,
    )

    charged = credits if credits is not None else find_value(response, {"credits", "credits_used", "cost_credits"})
    recorded = isinstance(charged, (int, float)) and not isinstance(charged, bool)
    account_before = attempt.get("account_credits_before")
    balance_delta_candidate = None
    if (
        isinstance(account_before, (int, float))
        and not isinstance(account_before, bool)
        and isinstance(account_after, (int, float))
        and account_before >= account_after
    ):
        balance_delta_candidate = round(float(account_before) - float(account_after), 6)
    if recorded:
        execution = shot.get("generation", {}).get("execution", {})
        profile = estimate_costs.execution_profile(
            execution.get("mode"),
            execution.get("argv") or [],
            fallback_duration=shot.get("duration_seconds"),
        )
        state.record_actual_cost(
            production,
            shot_id,
            float(charged),
            "agent",
            str(resolved_job_id),
            execution_profile=profile,
        )
    if normalized_status in {"PROVIDER_COMPLETED", "FAILED"} and not recorded:
        state.require_cost_reconciliation(
            production,
            shot_id,
            "agent",
            job_id=str(resolved_job_id),
            reported_credits=balance_delta_candidate,
            reason=(
                "terminal provider response did not expose numeric credits; account-balance delta is only a candidate"
                if balance_delta_candidate is not None
                else "terminal provider response did not expose numeric credits"
            ),
        )
    if normalized_status == "PROVIDER_COMPLETED":
        state.finalize_provider_completion(production, shot_id, "agent")
    current = state.load_all(production)
    current_shot = next(item for item in current["shots"].get("items", []) if item.get("id") == shot_id)
    return {
        "shot_id": shot_id,
        "job_id": resolved_job_id,
        "provider_status": raw_status,
        "status": current_shot["generation"]["status"],
        "result_available": result_available,
        "actual_credits_recorded": bool(recorded),
        "balance_delta_candidate": balance_delta_candidate,
        "cost_reconciliation_required": bool(current["costs"].get("actual", {}).get("reconciliation_required")),
        "ceiling_breach": bool(current["costs"].get("actual", {}).get("ceiling_breach")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("production", type=Path)
    parser.add_argument("shot_id")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute-paid", action="store_true", help="submit one approved paid job without waiting")
    mode.add_argument("--reconcile", action="store_true", help="observe or recover an existing provider job")
    parser.add_argument("--authorize-local-upload", action="store_true")
    parser.add_argument("--acknowledge-pending-costs", action="store_true")
    parser.add_argument("--job-id", help="bind an exact provider job while reconciling")
    parser.add_argument("--wait", action="store_true", help="poll the known job during reconciliation")
    parser.add_argument("--credits", type=float, help="record known actual credits while reconciling")
    parser.add_argument("--higgsfield", default="higgsfield")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--submit-timeout", type=int, default=120, help="transport timeout for a non-waiting create call")
    args = parser.parse_args()
    executable = shutil.which(args.higgsfield)
    if not executable:
        print(f"error: executable not found: {args.higgsfield}", file=sys.stderr)
        return 2
    try:
        if args.execute_paid:
            if args.job_id or args.wait or args.credits is not None:
                raise state.StateError("--job-id, --wait, and --credits are reconciliation-only options")
            result = run_paid(
                args.production.expanduser().resolve(),
                args.shot_id,
                executable,
                args.authorize_local_upload,
                args.submit_timeout,
                args.acknowledge_pending_costs,
            )
        else:
            result = reconcile(
                args.production.expanduser().resolve(),
                args.shot_id,
                executable,
                job_id=args.job_id,
                wait=args.wait,
                timeout=args.timeout,
                credits=args.credits,
            )
    except KeyboardInterrupt:
        print("error: interrupted; submission state was preserved for reconciliation", file=sys.stderr)
        return 130
    except state.StateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
