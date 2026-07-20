#!/usr/bin/env python3
"""Serve the production dashboard and authenticated loopback approval actions."""

from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import project_state as state


class DashboardHandler(BaseHTTPRequestHandler):
    production: Path
    dashboard: Path
    action_token: str

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self) -> bool:
        query = parse_qs(urlparse(self.path).query)
        supplied = self.headers.get("X-Sonol-Token") or (query.get("token") or [None])[0]
        return bool(supplied and secrets.compare_digest(supplied, self.action_token))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self.send_json(state.aggregate(self.production))
            return
        relative = "index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/")
        candidate = (self.dashboard / relative).resolve()
        try:
            candidate.relative_to(self.dashboard)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/action":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not self.authorized():
            self.send_json({"error": "invalid action token"}, HTTPStatus.FORBIDDEN)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise state.StateError("invalid request size")
            payload = json.loads(self.rfile.read(length))
            self.apply_action(payload)
            self.send_json({"ok": True, "state": state.aggregate(self.production)})
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, state.StateError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def check_version(self, collection: str, entity_id: str, expected: int) -> None:
        document = state.read_json(state.data_dir(self.production) / f"{collection}.json")
        entity = next((item for item in document.get("items", []) if item.get("id") == entity_id), None)
        if entity is None:
            raise state.StateError(f"unknown entity: {entity_id}")
        current = entity.get("version", entity.get("generation", {}).get("version"))
        if int(current) != int(expected):
            raise state.StateError(f"stale approval version: expected {expected}, current {current}")

    @staticmethod
    def numeric(value: object, field: str) -> float:
        if not isinstance(value, (str, int, float)) or isinstance(value, bool):
            raise state.StateError(f"{field} must be numeric")
        return float(value)

    @classmethod
    def integer(cls, value: object, field: str) -> int:
        number = cls.numeric(value, field)
        if not number.is_integer():
            raise state.StateError(f"{field} must be an integer")
        return int(number)

    def apply_action(self, payload: dict[str, object]) -> None:
        action = payload["action"]
        if action == "lock_requirements":
            state.lock_requirements(self.production, "user")
        elif action == "approve_cost":
            state.approve_cost(
                self.production,
                str(payload["scenario"]),
                self.numeric(payload["max_credits"], "max_credits"),
                "user",
            )
        elif action == "asset_transition":
            target = str(payload["target"])
            if target not in {"USER_APPROVED", "LOCKED_FOR_VIDEO", "REVISION_REQUESTED"}:
                raise state.StateError("dashboard cannot apply this asset transition")
            asset_id = str(payload["id"])
            self.check_version("assets", asset_id, self.integer(payload["version"], "version"))
            state.transition_asset(self.production, asset_id, target, "user", str(payload.get("reason", "")))
        elif action == "shot_transition":
            target = str(payload["target"])
            if target not in {"USER_APPROVED", "LOCKED_FOR_VIDEO", "REVISION_REQUESTED", "HOLD"}:
                raise state.StateError("dashboard cannot apply this shot transition")
            shot_id = str(payload["id"])
            self.check_version("shots", shot_id, self.integer(payload["version"], "version"))
            state.transition_shot_approval(self.production, shot_id, target, "user", str(payload.get("reason", "")))
        elif action == "user_review_qc":
            shot_id = str(payload["id"])
            self.check_version("shots", shot_id, self.integer(payload["version"], "version"))
            state.set_qc(self.production, shot_id, "user_review", str(payload["status"]), "user", str(payload.get("note", "")))
        else:
            raise state.StateError(f"unsupported dashboard action: {action}")

    def log_message(self, format: str, *args: object) -> None:
        print(f"dashboard {self.address_string()}: {format % args}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("production", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token")
    args = parser.parse_args()
    production = args.production.expanduser().resolve()
    dashboard = (production / "dashboard").resolve()
    if not (dashboard / "index.html").is_file():
        print("error: dashboard not initialized", file=sys.stderr)
        return 2
    DashboardHandler.production = production
    DashboardHandler.dashboard = dashboard
    DashboardHandler.action_token = args.token or secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DashboardHandler)
    port = server.server_address[1]
    print(f"Dashboard: http://127.0.0.1:{port}/?token={DashboardHandler.action_token}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
