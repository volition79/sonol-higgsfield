#!/usr/bin/env python3
"""Compile a shot_grammar JSON object into a provider-specific prompt contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cinematography


def load_object(raw: str) -> dict:
    path = Path(raw)
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("grammar must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grammar", type=load_object, help="JSON string or path")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--setting", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--exit-state", required=True)
    parser.add_argument("--invariant", action="append", default=[])
    parser.add_argument("--live-schema", type=Path)
    args = parser.parse_args()
    schema = json.loads(args.live_schema.read_text(encoding="utf-8")) if args.live_schema else None
    try:
        compiled = cinematography.compile_prompt(
            args.grammar, provider=args.provider, subject=args.subject, setting=args.setting,
            action=args.action, exit_state=args.exit_state, invariants=args.invariant,
            live_schema=schema,
        )
        result = {"compiled": compiled, "shot_grammar": cinematography.apply_compilation(args.grammar, compiled)}
    except (cinematography.CinematographyError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
