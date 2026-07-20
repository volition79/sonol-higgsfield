#!/usr/bin/env python3
"""Run Korean/English OCR and compare normalized expected strings."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z가-힣]+", "", value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--expected", action="append", required=True)
    parser.add_argument("--language", default="kor+eng")
    parser.add_argument("--psm", type=int, default=6, help="Tesseract page segmentation mode")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    source = args.image.expanduser().resolve()
    if not source.is_file():
        print(f"error: image not found: {source}", file=sys.stderr)
        return 2
    tesseract = shutil.which("tesseract")
    if not tesseract:
        print("error: tesseract not found", file=sys.stderr)
        return 2
    completed = subprocess.run(
        [tesseract, str(source), "stdout", "-l", args.language, "--psm", str(args.psm)],
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    recognized = completed.stdout.strip()
    haystack = normalize(recognized)
    checks = [
        {"expected": item, "normalized": normalize(item), "matched": normalize(item) in haystack}
        for item in args.expected
    ]
    result = {
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "image": str(source),
        "language": args.language,
        "psm": args.psm,
        "engine_exit_code": completed.returncode,
        "recognized_text": recognized,
        "checks": checks,
        "status": "PASSED" if completed.returncode == 0 and all(item["matched"] for item in checks) else "FAILED",
        "scope": "text-presence evidence only; spelling, layout, legibility, and visual quality still require review",
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        target = args.report.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
