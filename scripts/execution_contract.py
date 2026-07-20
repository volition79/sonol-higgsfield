#!/usr/bin/env python3
"""Canonicalize Higgsfield generation arguments for approval and execution gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


MEDIA_FLAGS = {
    "--audio",
    "--audio-reference",
    "--audio-references",
    "--end-image",
    "--image",
    "--image-reference",
    "--image-references",
    "--input-audio",
    "--input-image",
    "--input-video",
    "--reference-audio",
    "--reference-image",
    "--reference-video",
    "--start-image",
    "--video",
    "--video-reference",
    "--video-references",
}


def normalize_flag(value: str) -> str:
    if not value.startswith("--"):
        return value
    return "--" + value[2:].replace("_", "-")


def normalize_argv(argv: Iterable[str]) -> list[str]:
    """Normalize harmless CLI spelling differences without reordering arguments."""
    result: list[str] = []
    for raw in argv:
        part = str(raw)
        if part == "--wait":
            continue
        if part.startswith("--") and "=" in part:
            flag, value = part.split("=", 1)
            result.extend((normalize_flag(flag), value))
        else:
            result.append(normalize_flag(part))
    return result


def fingerprint(mode: str, argv: Iterable[str]) -> str:
    if mode not in {"model", "workflow"}:
        raise ValueError("execution mode must be model or workflow")
    payload = json.dumps(
        {"mode": mode, "argv": normalize_argv(argv)},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def parse_flags(argv: Iterable[str]) -> tuple[str | None, dict[str, Any]]:
    """Return provider and decoded long-option values from generation argv."""
    normalized = normalize_argv(argv)
    provider = normalized[0] if normalized and not normalized[0].startswith("--") else None
    flags: dict[str, Any] = {}
    index = 1 if provider else 0
    while index < len(normalized):
        part = normalized[index]
        if not part.startswith("--"):
            index += 1
            continue
        if index + 1 < len(normalized) and not normalized[index + 1].startswith("--"):
            raw: Any = normalized[index + 1]
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass
            flags[part[2:].replace("-", "_")] = raw
            index += 2
        else:
            flags[part[2:].replace("-", "_")] = True
            index += 1
    return provider, flags


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            yield value
        else:
            if decoded == value:
                yield value
            else:
                yield from _strings(decoded)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for key in ("path", "file", "url", "image", "video", "audio"):
            if key in value:
                yield from _strings(value[key])


def local_media_args(argv: Iterable[str]) -> list[str]:
    """Find existing local paths in singular/plural and equals-form media flags."""
    normalized = normalize_argv(argv)
    found: list[str] = []
    index = 0
    while index < len(normalized):
        part = normalized[index]
        if part in MEDIA_FLAGS and index + 1 < len(normalized):
            for candidate_value in _strings(normalized[index + 1]):
                candidate = Path(candidate_value).expanduser()
                if candidate.exists():
                    resolved = str(candidate.resolve())
                    if resolved not in found:
                        found.append(resolved)
            index += 2
        else:
            index += 1
    return found
