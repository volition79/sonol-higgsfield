#!/usr/bin/env python3
"""Recommend one to three intent-first cinematography plans without generation."""

from __future__ import annotations

import argparse
import json
import sys

import cinematography


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("intent")
    parser.add_argument("--genre", default="general")
    parser.add_argument("--platform", default="general")
    parser.add_argument("--subject-priority", choices=("balanced", "emotion", "space", "product", "action"), default="balanced")
    parser.add_argument("--stability", choices=("balanced", "stable", "unstable"), default="balanced")
    parser.add_argument("--provider")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--top", type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    try:
        result = cinematography.recommend(
            args.intent, genre=args.genre, platform=args.platform,
            subject_priority=args.subject_priority, stability=args.stability,
            provider=args.provider, duration_seconds=args.duration, top_n=args.top,
        )
    except cinematography.CinematographyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
