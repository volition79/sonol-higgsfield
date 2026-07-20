#!/usr/bin/env python3
"""Validate a standalone shot_grammar JSON object against the knowledge contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cinematography


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grammar", help="JSON string or path")
    parser.add_argument("--complete", action="store_true")
    parser.add_argument("--shot-duration", type=float)
    args = parser.parse_args()
    try:
        path = Path(args.grammar)
        value = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else json.loads(args.grammar)
        errors, warnings = cinematography.validate_grammar(value, require_complete=args.complete, shot_duration=args.shot_duration)
    except (OSError, json.JSONDecodeError, cinematography.CinematographyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"valid": not errors, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
