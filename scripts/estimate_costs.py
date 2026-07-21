#!/usr/bin/env python3
"""Calculate non-authoritative credit guidance from recent actual jobs only."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import execution_contract
import project_state as state


PROFILE_KEYS = ("provider", "mode", "resolution", "generate_audio")


def local_media_args(argv: list[str]) -> list[str]:
    return execution_contract.local_media_args(argv)


def execution_profile(mode: str, argv: list[str], *, fallback_duration: Any = None) -> dict[str, Any]:
    provider, flags = execution_contract.parse_flags(argv)
    duration = flags.get("duration", fallback_duration)
    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        duration_value = None
    if duration_value is not None and duration_value <= 0:
        duration_value = None
    return {
        "provider": provider,
        "mode": mode,
        "duration_seconds": duration_value,
        "resolution": flags.get("resolution"),
        "generate_audio": flags.get("generate_audio"),
    }


def profile_matches(sample: dict[str, Any], target: dict[str, Any]) -> bool:
    return all(sample.get(key) == target.get(key) for key in PROFILE_KEYS)


def calculate(production: Path, attempts: int = 1, recent_samples: int = 10) -> dict[str, Any]:
    if attempts < 1:
        raise state.StateError("attempts must be at least 1")
    if recent_samples < 1:
        raise state.StateError("recent_samples must be at least 1")
    documents = state.load_all(production)
    transactions = list(documents["costs"].get("actual", {}).get("transactions", []))
    rows: list[dict[str, Any]] = []
    numeric_totals: list[float] = []
    for shot in documents["shots"].get("items", []):
        execution = shot.get("generation", {}).get("execution") or {}
        mode, argv = execution.get("mode"), execution.get("argv") or []
        if mode not in {"model", "workflow"} or not argv:
            rows.append({"shot_id": shot.get("id"), "status": "UNAVAILABLE", "reason": "missing execution profile"})
            continue
        target = execution_profile(mode, argv, fallback_duration=shot.get("duration_seconds"))
        duration = target.get("duration_seconds")
        samples: list[tuple[str, float]] = []
        for transaction in reversed(transactions):
            profile = transaction.get("execution_profile") or {}
            sample_duration = profile.get("duration_seconds")
            credits = transaction.get("credits")
            if not profile_matches(profile, target):
                continue
            if not isinstance(credits, (int, float)) or isinstance(credits, bool):
                continue
            if not isinstance(sample_duration, (int, float)) or sample_duration <= 0:
                continue
            samples.append((str(transaction.get("recorded_at") or ""), float(credits) / float(sample_duration)))
            if len(samples) >= recent_samples:
                break
        if duration is None or not samples:
            rows.append(
                {
                    "shot_id": shot.get("id"),
                    "status": "UNAVAILABLE",
                    "reason": "no matching actual-credit samples",
                    "profile": target,
                }
            )
            continue
        rates = [rate for _, rate in samples]
        mean_rate = statistics.fmean(rates)
        estimate = mean_rate * float(duration) * attempts
        low = min(rates) * float(duration) * attempts
        high = max(rates) * float(duration) * attempts
        row = {
            "shot_id": shot.get("id"),
            "status": "REFERENCE_ONLY",
            "profile": target,
            "attempts": attempts,
            "sample_count": len(rates),
            "mean_credits_per_second": round(mean_rate, 6),
            "estimated_credits": round(estimate, 6),
            "observed_range_credits": [round(low, 6), round(high, 6)],
            "disclaimer": "Recent actual arithmetic only; not a live Higgsfield quote or spending guarantee.",
        }
        rows.append(row)
        numeric_totals.append(estimate)
    result = {
        "method": "recent_actual_arithmetic",
        "status": "REFERENCE_ONLY" if numeric_totals else "UNAVAILABLE",
        "shots": rows,
        "total_estimated_credits": round(sum(numeric_totals), 6) if numeric_totals else None,
        "covered_shots": len(numeric_totals),
        "total_shots": len(rows),
        "attempts_per_shot": attempts,
        "disclaimer": "No provider cost endpoint was called. Actual charges can differ and may exceed this reference.",
    }
    state.store_reference_estimates(production, result, "agent")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("production", type=Path)
    parser.add_argument("--attempts", type=int, default=1, help="planned candidates or retries per shot")
    parser.add_argument("--recent-samples", type=int, default=10)
    args = parser.parse_args()
    try:
        result = calculate(args.production.expanduser().resolve(), args.attempts, args.recent_samples)
    except state.StateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
