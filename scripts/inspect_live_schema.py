#!/usr/bin/env python3
"""Capture a redacted, read-only snapshot of the live Higgsfield CLI contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MODELS = (
    "seedance_2_0",
    "seedance_2_0_mini",
    "wan2_6",
    "wan2_7",
    "veo3_1",
    "kling3_0",
    "gpt_image_2",
    "nano_banana_flash",
    "seed_audio",
    "text2speech_v2",
    "inworld_text_to_speech",
    "speech2text",
    "cinematic_studio_video_3_5",
)
DEFAULT_WORKFLOWS = (
    "voice_change", "dubbing", "reframe", "draw_to_video",
    "cinematic_studio_3_0", "cinematic_studio_image",
)
SECRET_KEYS = {"email", "token", "access_token", "refresh_token", "authorization", "cookie"}


class ProbeError(RuntimeError):
    pass


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def run_json(argv: list[str]) -> Any:
    completed = subprocess.run(argv, text=True, capture_output=True, timeout=45, check=False)
    if completed.returncode:
        message = (completed.stderr or completed.stdout).strip()
        raise ProbeError(f"{' '.join(argv[:3])}: {message}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"invalid JSON from {' '.join(argv[:3])}: {exc}") from exc


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            lowered = key.lower()
            if lowered in SECRET_KEYS or "secret" in lowered or "password" in lowered:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact(child)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def mcp_status() -> dict[str, Any]:
    if not shutil.which("codex"):
        return {"configured": False, "reason": "codex command not found"}
    try:
        completed = subprocess.run(
            ["codex", "mcp", "get", "higgsfield"], text=True, capture_output=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        # On Windows a codex .ps1/.cmd shim is visible to shutil.which but not
        # executable through CreateProcess; the MCP probe must degrade instead
        # of crashing the whole preflight.
        return {"configured": False, "reason": f"codex probe not executable: {exc}"}
    output = (completed.stdout + "\n" + completed.stderr).strip()
    match = re.search(r"^\s*url:\s*(\S+)", output, re.MULTILINE)
    url = match.group(1) if match else None
    return {
        "configured": completed.returncode == 0,
        "url": url,
        "url_contract_valid": bool(url and url.rstrip("/").endswith("/mcp")),
    }


def capture(models: tuple[str, ...], workflows: tuple[str, ...]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    version = subprocess.run(
        ["higgsfield", "--version"], text=True, capture_output=True, timeout=10, check=False
    )
    snapshot: dict[str, Any] = {
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "cli_version": version.stdout.strip() or version.stderr.strip(),
        "account": {},
        "workspace": {},
        "models": [],
        "workflows": [],
        "model_contracts": {},
        "workflow_contracts": {},
        "mcp": mcp_status(),
        "discovery_warnings": [],
    }
    for key, argv in (
        ("account", ["higgsfield", "--json", "account", "status"]),
        ("workspace", ["higgsfield", "--json", "workspace", "status"]),
        ("models", ["higgsfield", "--json", "model", "list"]),
        ("workflows", ["higgsfield", "--json", "workflow", "list"]),
    ):
        try:
            snapshot[key] = redact(run_json(argv))
        except ProbeError as exc:
            errors.append(str(exc))
    available_models = {item.get("job_type") for item in snapshot.get("models", [])}
    available_workflows = {item.get("job_type") for item in snapshot.get("workflows", [])}
    for model in models:
        try:
            snapshot["model_contracts"][model] = redact(
                run_json(["higgsfield", "--json", "model", "get", model])
            )
            if model not in available_models:
                snapshot["discovery_warnings"].append(
                    f"model contract is directly inspectable but absent from model list: {model}"
                )
        except ProbeError as exc:
            prefix = f"requested model is absent: {model}; " if model not in available_models else ""
            errors.append(prefix + str(exc))
    for workflow in workflows:
        try:
            snapshot["workflow_contracts"][workflow] = redact(
                run_json(["higgsfield", "--json", "workflow", "get", workflow])
            )
            if workflow not in available_workflows:
                snapshot["discovery_warnings"].append(
                    f"workflow contract is directly inspectable but absent from workflow list: {workflow}"
                )
        except ProbeError as exc:
            prefix = f"requested workflow is absent: {workflow}; " if workflow not in available_workflows else ""
            errors.append(prefix + str(exc))
    snapshot["contract_fingerprints"] = {
        "models": {
            name: stable_hash(contract)
            for name, contract in snapshot["model_contracts"].items()
        },
        "workflows": {
            name: stable_hash(contract)
            for name, contract in snapshot["workflow_contracts"].items()
        },
    }
    snapshot["schema_fingerprint"] = stable_hash(
        {
            "cli_version": snapshot["cli_version"],
            "model_contracts": snapshot["model_contracts"],
            "workflow_contracts": snapshot["workflow_contracts"],
        }
    )
    snapshot["preflight"] = {
        "authenticated": bool(snapshot.get("account", {}).get("credits") is not None),
        "workspace_selected": bool(snapshot.get("workspace", {}).get("is_selected")),
        "available_credits": snapshot.get("workspace", {}).get("credits", snapshot.get("account", {}).get("credits")),
        "errors": errors,
    }
    return snapshot, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--workflow", action="append", default=[])
    args = parser.parse_args()
    if not shutil.which("higgsfield"):
        print("error: higgsfield command not found", file=sys.stderr)
        return 2
    snapshot, errors = capture(tuple(args.model or DEFAULT_MODELS), tuple(args.workflow or DEFAULT_WORKFLOWS))
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(json.dumps({"output": str(args.output), "errors": errors}, ensure_ascii=False, indent=2))
    else:
        print(payload, end="")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
