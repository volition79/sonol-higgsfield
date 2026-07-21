#!/usr/bin/env python3
"""Portable browser bootstrap and safe CDP bridge for Higgsfield web execution."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Sequence


SKILL_ROOT = Path(__file__).resolve().parent.parent
CDP_SCRIPT = SKILL_ROOT / "scripts" / "higgsfield_web_cdp.mjs"
HIGGSFIELD_URL = "https://higgsfield.ai/generate"


def host_platform(
    *,
    system: str | None = None,
    release: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    env = os.environ if environ is None else environ
    current_system = (system or platform.system()).casefold()
    current_release = (release or platform.release()).casefold()
    if current_system == "windows":
        return "windows"
    if current_system == "darwin":
        return "macos"
    if current_system == "linux" and (
        "microsoft" in current_release or env.get("WSL_DISTRO_NAME") or env.get("WSL_INTEROP")
    ):
        return "wsl"
    return "linux"


def candidate_browsers(kind: str, environ: Mapping[str, str] | None = None) -> list[str]:
    env = os.environ if environ is None else environ
    if kind == "windows":
        roots = [env.get("PROGRAMFILES"), env.get("PROGRAMFILES(X86)"), env.get("LOCALAPPDATA")]
        suffixes = [
            ("Google", "Chrome", "Application", "chrome.exe"),
            ("Microsoft", "Edge", "Application", "msedge.exe"),
        ]
        return [str(Path(root, *suffix)) for root in roots if root for suffix in suffixes]
    if kind == "wsl":
        return [
            "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files/Microsoft/Edge/Application/msedge.exe",
            "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        ]
    if kind == "macos":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    return ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]


def candidate_nodes(kind: str) -> list[str]:
    if kind == "wsl":
        return ["/mnt/c/Program Files/nodejs/node.exe", "node"]
    return ["node"]


def resolve_program(candidates: Sequence[str]) -> str | None:
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_absolute() and path.exists():
            return str(path)
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def windows_local_app_data() -> str | None:
    command = shutil.which("cmd.exe") or "/mnt/c/Windows/System32/cmd.exe"
    if not Path(command).exists() and not shutil.which(command):
        return None
    completed = subprocess.run(
        [command, "/d", "/c", "echo", "%LOCALAPPDATA%"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    value = completed.stdout.strip().replace("\r", "")
    return value if completed.returncode == 0 and value and "%LOCALAPPDATA%" not in value else None


def default_profile(kind: str) -> str:
    if kind == "windows":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return str(Path(root) / "SonolHiggsfield" / "BrowserProfile")
    if kind == "wsl":
        root = windows_local_app_data() or r"C:\Temp"
        return str(Path(root) / "SonolHiggsfield" / "BrowserProfile").replace("/", "\\")
    if kind == "macos":
        return str(Path.home() / "Library" / "Application Support" / "SonolHiggsfield" / "BrowserProfile")
    return str(Path.home() / ".local" / "share" / "sonol-higgsfield" / "browser-profile")


def browser_command(browser: str, profile_dir: str, port: int, url: str) -> list[str]:
    return [
        browser,
        f"--remote-debugging-port={port}",
        "--remote-debugging-address=127.0.0.1",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        url,
    ]


def cdp_targets(port: int) -> list[dict[str, Any]]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3) as response:
        value = json.load(response)
    return value if isinstance(value, list) else []


def node_version(node: str | None) -> str | None:
    if not node:
        return None
    completed = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else None


def cdp_script_arg(kind: str) -> str:
    if kind != "wsl":
        return str(CDP_SCRIPT)
    wslpath = shutil.which("wslpath")
    if not wslpath:
        return str(CDP_SCRIPT)
    completed = subprocess.run(
        [wslpath, "-w", str(CDP_SCRIPT)], capture_output=True, text=True, timeout=10, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else str(CDP_SCRIPT)


def run_cdp(kind: str, node: str, command: str, port: int, rest: Sequence[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [node, cdp_script_arg(kind), command, "--port", str(port), *rest],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "CDP command failed")
    value = json.loads(completed.stdout)
    return value if isinstance(value, dict) else {"result": value}


def doctor() -> dict[str, Any]:
    kind = host_platform()
    browser = resolve_program(candidate_browsers(kind))
    node = resolve_program(candidate_nodes(kind))
    version = node_version(node)
    major = None
    if version and version.lstrip("v").split(".", 1)[0].isdigit():
        major = int(version.lstrip("v").split(".", 1)[0])
    return {
        "platform": kind,
        "browser": browser,
        "node": node,
        "node_version": version,
        "cdp_fallback_ready": bool(browser and node and major is not None and major >= 22),
        "native_computer_use_preferred": True,
        "profile_dir": default_profile(kind),
        "login_policy": "USER_INTERACTIVE_REQUIRED",
    }


def launch(browser: str, profile_dir: str, port: int, url: str) -> dict[str, Any]:
    command = browser_command(browser, profile_dir, port, url)
    kwargs: dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(command, **kwargs)
    targets: list[dict[str, Any]] = []
    for _ in range(30):
        try:
            targets = cdp_targets(port)
            if targets:
                break
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            pass
        time.sleep(0.5)
    return {
        "launched": bool(targets),
        "port": port,
        "profile_dir": profile_dir,
        "url": url,
        "login_required": True,
        "user_message": (
            "Higgsfield 전용 브라우저에서 로그인과 2단계 인증을 직접 완료한 뒤 "
            "로그인했다고 알려주세요. 비밀번호나 인증 코드를 채팅에 보내지 마세요."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    launch_parser = subparsers.add_parser("launch")
    launch_parser.add_argument("--browser")
    launch_parser.add_argument("--profile-dir")
    launch_parser.add_argument("--port", type=int, default=9222)
    launch_parser.add_argument("--url", default=HIGGSFIELD_URL)
    for name in ("status", "login-status", "inspect-cinema"):
        command_parser = subparsers.add_parser(name)
        command_parser.add_argument("--port", type=int, default=9222)
    role_parser = subparsers.add_parser("set-start-role")
    role_parser.add_argument("image_job_id")
    role_parser.add_argument("--port", type=int, default=9222)
    text_parser = subparsers.add_parser("insert-text")
    text_parser.add_argument("--text-file", type=Path, required=True)
    text_parser.add_argument("--port", type=int, default=9222)
    submit_parser = subparsers.add_parser("submit-paid")
    submit_parser.add_argument("--confirm", required=True)
    submit_parser.add_argument("--port", type=int, default=9222)
    args = parser.parse_args()

    if args.command == "doctor":
        result = doctor()
    else:
        info = doctor()
        kind = info["platform"]
        if args.command == "launch":
            browser = args.browser or info["browser"]
            if not browser:
                raise RuntimeError("Chrome, Edge, or Chromium was not found")
            result = launch(browser, args.profile_dir or info["profile_dir"], args.port, args.url)
        else:
            node = info["node"]
            if not node or not info["cdp_fallback_ready"]:
                raise RuntimeError("CDP fallback requires Node.js 22 or newer; use native computer use instead")
            rest: list[str] = []
            if args.command == "set-start-role":
                rest = [args.image_job_id]
            elif args.command == "insert-text":
                rest = [args.text_file.read_text(encoding="utf-8")]
            elif args.command == "submit-paid":
                rest = [args.confirm]
            result = run_cdp(kind, node, args.command, args.port, rest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
