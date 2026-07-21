#!/usr/bin/env python3
"""Durable state and gate logic for sonol-higgsfield productions."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cinematography
import execution_contract


SCHEMA_VERSION = 4
REQUIRED_REQUIREMENTS = (
    "purpose",
    "core_message",
    "target_audience",
    "target_platform",
    "duration_seconds",
    "aspect_ratio",
    "resolution",
    "frame_rate",
    "language",
    "story_direction",
    "characters_products_brands",
    "copyright_constraints",
    "approval_method",
    "quality_cost_priority",
)
REQUIREMENT_STATES = {"CONFIRMED", "INFERRED", "UNKNOWN", "CONFLICT"}
ASSET_STATES = {
    "DRAFT",
    "INTERNAL_QC_PASSED",
    "USER_REVIEW",
    "USER_APPROVED",
    "LOCKED_FOR_VIDEO",
    "REVISION_REQUESTED",
}
ASSET_TRANSITIONS = {
    "DRAFT": {"INTERNAL_QC_PASSED", "REVISION_REQUESTED"},
    "INTERNAL_QC_PASSED": {"USER_REVIEW", "REVISION_REQUESTED"},
    "USER_REVIEW": {"USER_APPROVED", "REVISION_REQUESTED"},
    "USER_APPROVED": {"LOCKED_FOR_VIDEO", "REVISION_REQUESTED"},
    "LOCKED_FOR_VIDEO": {"REVISION_REQUESTED"},
    "REVISION_REQUESTED": {"DRAFT"},
}
SHOT_APPROVAL_STATES = {
    "DRAFT",
    "INTERNAL_QC_PASSED",
    "USER_REVIEW",
    "USER_APPROVED",
    "LOCKED_FOR_VIDEO",
    "REVISION_REQUESTED",
    "HOLD",
}
SHOT_APPROVAL_TRANSITIONS = {
    "DRAFT": {"INTERNAL_QC_PASSED", "HOLD", "REVISION_REQUESTED"},
    "INTERNAL_QC_PASSED": {"USER_REVIEW", "HOLD", "REVISION_REQUESTED"},
    "USER_REVIEW": {"USER_APPROVED", "HOLD", "REVISION_REQUESTED"},
    "USER_APPROVED": {"LOCKED_FOR_VIDEO", "HOLD", "REVISION_REQUESTED"},
    "LOCKED_FOR_VIDEO": {"HOLD", "REVISION_REQUESTED"},
    "REVISION_REQUESTED": {"DRAFT", "HOLD"},
    "HOLD": {"DRAFT", "USER_REVIEW"},
}
GENERATION_STATES = {
    "PLANNED",
    "READY",
    "QUEUED",
    "GENERATING",
    "GENERATED",
    "FAILED",
    "QC_FAILED",
    "FINAL_COMPLETE",
}
GENERATION_TRANSITIONS = {
    "PLANNED": {"READY", "FAILED"},
    "READY": {"QUEUED", "FAILED"},
    "QUEUED": {"GENERATING", "FAILED"},
    "GENERATING": {"GENERATED", "FAILED"},
    "GENERATED": {"QC_FAILED", "FINAL_COMPLETE", "READY"},
    "FAILED": {"READY"},
    "QC_FAILED": {"READY", "FINAL_COMPLETE"},
    "FINAL_COMPLETE": set(),
}
QC_STATES = {"PENDING", "PASSED", "FAILED", "MANUAL_REQUIRED", "NOT_APPLICABLE"}
BOUNDARY_STRATEGIES = {
    "continuous_match",
    "motivated_transition",
    "editorial_cut",
    "scene_reset",
}
KEYFRAME_ROLES = {"start_image", "end_image", "image_reference", "analysis_only", "none"}
AUDIO_ROUTES = {
    "NO_DIALOGUE_POST",
    "INTENTIONAL_SILENCE",
    "OFFSCREEN_NARRATION",
    "VISIBLE_DIALOGUE_ELEVENLABS_V3",
}
DATA_FILES = (
    "project.json",
    "requirements.json",
    "assets.json",
    "scenes.json",
    "shots.json",
    "costs.json",
    "history.json",
)


class StateError(RuntimeError):
    """Raised when a production invariant would be violated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _root(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def data_dir(root: str | Path) -> Path:
    return _root(root) / "data"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError(f"missing state file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StateError(f"state file must contain an object: {path}")
    return value


def atomic_write_json(path: Path, value: dict[str, Any], *, backup: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if backup and path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_all(root: str | Path) -> dict[str, dict[str, Any]]:
    base = data_dir(root)
    return {name[:-5]: read_json(base / name) for name in DATA_FILES}


def append_history(
    root: str | Path,
    event: str,
    actor: str,
    entity_type: str,
    entity_id: str,
    detail: dict[str, Any] | None = None,
) -> None:
    path = data_dir(root) / "history.json"
    history = read_json(path)
    history.setdefault("events", []).append(
        {
            "event_id": f"EVT_{len(history.get('events', [])) + 1:06d}",
            "timestamp": utc_now(),
            "event": event,
            "actor": actor,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "detail": detail or {},
        }
    )
    atomic_write_json(path, history)


def _base_document() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "updated_at": utc_now()}


def default_boundary_plan() -> dict[str, Any]:
    return {
        "strategy": "UNDECIDED",
        "previous_shot_id": None,
        "inherit_previous_last_frame": None,
        "previous_boundary_frame": None,
        "planned_keyframe": None,
        "planned_keyframe_role": "none",
        "cut_type": None,
        "reason": None,
    }


def default_audio_plan() -> dict[str, Any]:
    return {
        "route": "UNDECIDED",
        "has_visible_dialogue": None,
        "voice_provider": None,
        "voice_model": None,
        "voice_ids": [],
        "dialogue_master_path": None,
        "discard_generated_track": False,
        "final_mix_required": True,
        "final_mix_path": None,
    }


def initialize(root: str | Path, name: str, template_dir: Path) -> Path:
    production = _root(root)
    if production.exists() and any(production.iterdir()):
        raise StateError(f"production directory is not empty: {production}")
    production.mkdir(parents=True, exist_ok=True)
    (production / "data").mkdir(exist_ok=True)
    for media_type in ("images", "videos", "audio"):
        (production / "media" / media_type).mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_dir, production / "dashboard", dirs_exist_ok=True)

    project = _base_document() | {
        "project": {
            "id": "PROJECT_001",
            "name": name,
            "purpose": None,
            "target_platform": None,
            "duration_seconds": None,
            "aspect_ratio": None,
            "resolution": None,
            "frame_rate": None,
            "language": None,
        },
        "stage": "REQUIREMENTS_DRAFT",
        "requirements_lock": {
            "status": "UNLOCKED",
            "version": 0,
            "approved_by": None,
            "approved_at": None,
        },
        "cost_approval": {
            "status": "UNAPPROVED",
            "mode": "PROJECT_CEILING",
            "max_credits": None,
            "approved_by": None,
            "approved_at": None,
            "unpriced_job_risk_acknowledged": False,
        },
    }
    requirements = _base_document() | {
        "fields": {
            key: {
                "status": "UNKNOWN",
                "value": None,
                "source": None,
                "confirmed_by": None,
                "updated_at": utc_now(),
            }
            for key in REQUIRED_REQUIREMENTS
        }
    }
    assets = _base_document() | {"items": []}
    scenes = _base_document() | {"items": []}
    shots = _base_document() | {"items": []}
    costs = _base_document() | {
        "currency": "credits",
        "reference_estimates": {
            "method": "recent_actual_arithmetic",
            "status": "NOT_COMPUTED",
            "shots": [],
            "total_estimated_credits": None,
            "covered_shots": 0,
            "total_shots": 0,
        },
        "actual": {"credits": 0.0, "transactions": [], "reconciliation_required": False, "pending": []},
        "cash_value": {"status": "UNKNOWN", "value": None, "currency": None},
    }
    history = _base_document() | {"events": []}
    for name_, value in (
        ("project.json", project),
        ("requirements.json", requirements),
        ("assets.json", assets),
        ("scenes.json", scenes),
        ("shots.json", shots),
        ("costs.json", costs),
        ("history.json", history),
    ):
        atomic_write_json(production / "data" / name_, value, backup=False)
    append_history(production, "production_initialized", "agent", "project", "PROJECT_001")
    sync_dashboard(production)
    return production


def migrate(root: str | Path) -> dict[str, Any]:
    """Explicitly upgrade older productions to the current guarded schema."""
    production = _root(root)
    state = load_all(production)
    versions = {document.get("schema_version") for document in state.values()}
    if versions == {SCHEMA_VERSION}:
        return {"migrated": False, "schema_version": SCHEMA_VERSION}
    only_version = next(iter(versions)) if len(versions) == 1 else None
    if only_version not in {1, 2, 3}:
        raise StateError(f"cannot migrate mixed or unsupported schema versions: {sorted(versions, key=str)}")
    assert isinstance(only_version, int)
    from_version = only_version
    for shot in state["shots"].get("items", []):
        if "shot_grammar" not in shot:
            grammar = cinematography.empty_grammar()
            if shot.get("duration_seconds") is not None:
                grammar["duration_seconds"] = shot["duration_seconds"]
            shot["shot_grammar"] = grammar
        else:
            binding = shot["shot_grammar"].setdefault("provider_binding", {})
            binding.setdefault("schema_contract_hash", None)
        shot.setdefault("seedance_plan", cinematography.default_seedance_plan())
        if shot["seedance_plan"].get("audio_mode") == "none":
            shot["seedance_plan"]["audio_mode"] = "post_only"
        references = shot.setdefault("references", {})
        references.setdefault("manifest", [])
        shot.setdefault("boundary", default_boundary_plan())
        audio = shot.setdefault("audio", {})
        for key, value in default_audio_plan().items():
            audio.setdefault(key, deepcopy(value))
        generation = shot.setdefault("generation", {})
        generation.pop("cost_argv", None)
        generation.pop("cost_options", None)
        execution = generation.setdefault("execution", {"mode": None, "argv": []})
        execution.setdefault("fingerprint", None)
        shot.setdefault("qc", {})["cinematography"] = "PENDING"
    approval = state["project"].setdefault("cost_approval", {})
    approval.pop("scenario", None)
    approval.pop("task_contracts", None)
    approval.setdefault("mode", "PROJECT_CEILING")
    approval.setdefault("unpriced_job_risk_acknowledged", approval.get("status") == "APPROVED")
    costs = state["costs"]
    costs.pop("scenarios", None)
    costs.pop("task_estimates", None)
    costs.setdefault(
        "reference_estimates",
        {
            "method": "recent_actual_arithmetic",
            "status": "NOT_COMPUTED",
            "shots": [],
            "total_estimated_credits": None,
            "covered_shots": 0,
            "total_shots": len(state["shots"].get("items", [])),
        },
    )
    actual = costs.setdefault("actual", {"credits": 0.0, "transactions": []})
    actual.setdefault("reconciliation_required", False)
    actual.setdefault("pending", [])
    for name, document in state.items():
        document["schema_version"] = SCHEMA_VERSION
        document["updated_at"] = utc_now()
        atomic_write_json(data_dir(production) / f"{name}.json", document)
    append_history(production, "schema_migrated", "agent", "project", "PROJECT_001", {"from": from_version, "to": SCHEMA_VERSION})
    sync_dashboard(production)
    return {"migrated": True, "schema_version": SCHEMA_VERSION}


def _find(items: Iterable[dict[str, Any]], entity_id: str, kind: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == entity_id:
            return item
    raise StateError(f"unknown {kind}: {entity_id}")


def invalidate_reference_estimates(root: str | Path, actor: str, reason: str) -> None:
    """Clear arithmetic guidance when a planned execution profile changes.

    The user-approved project ceiling remains intact because it is a total spend
    limit, not approval of an exact provider quote.
    """
    costs_path = data_dir(root) / "costs.json"
    costs = read_json(costs_path)
    costs["reference_estimates"] = {
        "method": "recent_actual_arithmetic",
        "status": "STALE",
        "shots": [],
        "total_estimated_credits": None,
        "covered_shots": 0,
        "total_shots": len(read_json(data_dir(root) / "shots.json").get("items", [])),
    }
    costs["updated_at"] = utc_now()
    atomic_write_json(costs_path, costs)
    append_history(root, "reference_estimates_invalidated", actor, "cost", "production", {"reason": reason})


def set_requirement(
    root: str | Path,
    field: str,
    value: Any,
    status: str,
    actor: str,
    source: str | None = None,
) -> None:
    if status not in REQUIREMENT_STATES:
        raise StateError(f"invalid requirement state: {status}")
    path = data_dir(root) / "requirements.json"
    requirements = read_json(path)
    if field not in requirements.get("fields", {}):
        raise StateError(f"unknown requirement field: {field}")
    entry = requirements["fields"][field]
    previous = deepcopy(entry)
    entry.update(
        {
            "status": status,
            "value": value,
            "source": source,
            "confirmed_by": actor if status == "CONFIRMED" else None,
            "updated_at": utc_now(),
        }
    )
    requirements["updated_at"] = utc_now()
    atomic_write_json(path, requirements)

    project_path = data_dir(root) / "project.json"
    project = read_json(project_path)
    if field in project.get("project", {}):
        project["project"][field] = value
        project["updated_at"] = utc_now()
        atomic_write_json(project_path, project)
    invalidated = project["requirements_lock"]["status"] == "LOCKED" and previous != entry
    if invalidated:
        project["requirements_lock"].update(
            {"status": "UNLOCKED", "approved_by": None, "approved_at": None}
        )
        project["stage"] = "REQUIREMENTS_CHANGED"
        atomic_write_json(project_path, project)
        invalidate_reference_estimates(root, actor, f"requirement changed: {field}")
    append_history(root, "requirement_updated", actor, "requirement", field, {"status": status})
    sync_dashboard(root)


def lock_requirements(root: str | Path, actor: str) -> None:
    if actor != "user":
        raise StateError("only the user may lock requirements")
    state = load_all(root)
    missing = [
        key
        for key in REQUIRED_REQUIREMENTS
        if state["requirements"]["fields"].get(key, {}).get("status") != "CONFIRMED"
    ]
    if missing:
        raise StateError("requirements are not confirmed: " + ", ".join(missing))
    project = state["project"]
    project["requirements_lock"].update(
        {
            "status": "LOCKED",
            "version": int(project["requirements_lock"].get("version", 0)) + 1,
            "approved_by": actor,
            "approved_at": utc_now(),
        }
    )
    project["stage"] = "REQUIREMENTS_LOCKED"
    project["updated_at"] = utc_now()
    atomic_write_json(data_dir(root) / "project.json", project)
    append_history(root, "requirements_locked", actor, "project", project["project"]["id"])
    sync_dashboard(root)


def approve_budget(root: str | Path, max_credits: float, actor: str) -> None:
    if actor != "user":
        raise StateError("only the user may approve a project credit ceiling")
    if max_credits < 0:
        raise StateError("max_credits must be non-negative")
    project_path = data_dir(root) / "project.json"
    project = read_json(project_path)
    costs = read_json(data_dir(root) / "costs.json")
    if project.get("requirements_lock", {}).get("status") != "LOCKED":
        raise StateError("requirements must be locked before budget approval")
    actual = float(costs.get("actual", {}).get("credits", 0) or 0)
    if max_credits < actual:
        raise StateError("approved ceiling cannot be below credits already used")
    project["cost_approval"].update(
        {
            "status": "APPROVED",
            "mode": "PROJECT_CEILING",
            "max_credits": max_credits,
            "approved_by": actor,
            "approved_at": utc_now(),
            "unpriced_job_risk_acknowledged": True,
        }
    )
    project["updated_at"] = utc_now()
    atomic_write_json(project_path, project)
    append_history(
        root,
        "project_credit_ceiling_approved",
        actor,
        "project",
        project["project"]["id"],
        {"max_credits": max_credits, "live_quote_removed": True},
    )
    sync_dashboard(root)


def add_asset(root: str | Path, asset_id: str, asset_type: str, label: str) -> None:
    path = data_dir(root) / "assets.json"
    assets = read_json(path)
    if any(item.get("id") == asset_id for item in assets.get("items", [])):
        raise StateError(f"duplicate asset id: {asset_id}")
    assets.setdefault("items", []).append(
        {
            "id": asset_id,
            "type": asset_type,
            "label": label,
            "version": 1,
            "status": "DRAFT",
            "file_path": None,
            "thumbnail_path": None,
            "contains_korean_text": False,
            "ocr_status": "NOT_APPLICABLE",
            "approved_by": None,
            "approved_at": None,
            "updated_at": utc_now(),
        }
    )
    assets["updated_at"] = utc_now()
    atomic_write_json(path, assets)
    append_history(root, "asset_added", "agent", "asset", asset_id, {"type": asset_type})
    sync_dashboard(root)


def update_asset(root: str | Path, asset_id: str, patch: dict[str, Any], actor: str) -> None:
    """Update production metadata and invalidate approvals when content changes."""
    allowed = {
        "label",
        "file_path",
        "thumbnail_path",
        "contains_korean_text",
        "ocr_status",
        "prompt",
        "model",
        "job_id",
        "notes",
    }
    unknown = sorted(set(patch) - allowed)
    if unknown:
        raise StateError("unsupported asset fields: " + ", ".join(unknown))
    if "ocr_status" in patch and patch["ocr_status"] not in QC_STATES:
        raise StateError(f"invalid OCR state: {patch['ocr_status']}")
    path = data_dir(root) / "assets.json"
    assets = read_json(path)
    asset = _find(assets.get("items", []), asset_id, "asset")
    changed = any(asset.get(key) != value for key, value in patch.items())
    if changed and asset.get("status") not in {"DRAFT", "REVISION_REQUESTED"}:
        asset["version"] = int(asset.get("version", 1)) + 1
        asset["status"] = "DRAFT"
        asset["approved_by"] = None
        asset["approved_at"] = None
    asset.update(patch)
    asset["updated_at"] = utc_now()
    assets["updated_at"] = utc_now()
    atomic_write_json(path, assets)
    append_history(root, "asset_updated", actor, "asset", asset_id, {"fields": sorted(patch)})
    sync_dashboard(root)


def transition_asset(root: str | Path, asset_id: str, target: str, actor: str, reason: str = "") -> None:
    if target not in ASSET_STATES:
        raise StateError(f"invalid asset state: {target}")
    path = data_dir(root) / "assets.json"
    assets = read_json(path)
    asset = _find(assets.get("items", []), asset_id, "asset")
    current = asset["status"]
    if target not in ASSET_TRANSITIONS[current]:
        raise StateError(f"invalid asset transition: {current} -> {target}")
    if target in {"USER_APPROVED", "LOCKED_FOR_VIDEO"} and actor != "user":
        raise StateError("only the user may approve or lock an asset")
    if target == "LOCKED_FOR_VIDEO" and asset.get("contains_korean_text") and asset.get("ocr_status") != "PASSED":
        raise StateError("Korean-text asset must pass OCR before video lock")
    if target == "DRAFT" and current == "REVISION_REQUESTED":
        asset["version"] = int(asset.get("version", 1)) + 1
    if target in {"REVISION_REQUESTED", "DRAFT"}:
        asset.update({"approved_by": None, "approved_at": None})
    if target == "USER_APPROVED":
        asset.update({"approved_by": actor, "approved_at": utc_now()})
    asset.update({"status": target, "updated_at": utc_now()})
    assets["updated_at"] = utc_now()
    atomic_write_json(path, assets)
    append_history(root, "asset_transition", actor, "asset", asset_id, {"from": current, "to": target, "reason": reason})
    sync_dashboard(root)


def add_scene(root: str | Path, scene_id: str, title: str, order: int) -> None:
    path = data_dir(root) / "scenes.json"
    scenes = read_json(path)
    if any(item.get("id") == scene_id for item in scenes.get("items", [])):
        raise StateError(f"duplicate scene id: {scene_id}")
    scenes.setdefault("items", []).append(
        {"id": scene_id, "title": title, "order": order, "status": "PLANNED", "updated_at": utc_now()}
    )
    scenes["items"].sort(key=lambda item: (item.get("order", 0), item.get("id", "")))
    scenes["updated_at"] = utc_now()
    atomic_write_json(path, scenes)
    append_history(root, "scene_added", "agent", "scene", scene_id, {"order": order})
    sync_dashboard(root)


def add_shot(root: str | Path, shot_id: str, scene_id: str, title: str, order: int) -> None:
    state = load_all(root)
    _find(state["scenes"].get("items", []), scene_id, "scene")
    if any(item.get("id") == shot_id for item in state["shots"].get("items", [])):
        raise StateError(f"duplicate shot id: {shot_id}")
    shot = {
        "id": shot_id,
        "scene_id": scene_id,
        "title": title,
        "order": order,
        "duration_seconds": None,
        "purpose": None,
        "shot_grammar": cinematography.empty_grammar(),
        "continuity": {
            "previous_scene_context": None,
            "current_shot_goal": None,
            "emotional_continuity": None,
            "visual_continuity": None,
            "action_continuity": None,
            "camera_continuity": None,
            "audio_continuity": None,
            "next_scene_setup": None,
        },
        "boundary": default_boundary_plan(),
        "required_asset_ids": [],
        "references": {
            "start": None,
            "end": None,
            "images": [],
            "videos": [],
            "audios": [],
            "manifest": [],
        },
        "seedance_plan": cinematography.default_seedance_plan(),
        "approval_status": "DRAFT",
        "approved_by": None,
        "approved_at": None,
        "generation": {
            "status": "PLANNED",
            "model": None,
            "job_id": None,
            "version": 1,
            "retry_count": 0,
            "execution": {"mode": None, "argv": [], "fingerprint": None},
            "result_path": None,
        },
        "audio": default_audio_plan(),
        "qc": {
            "technical": "PENDING",
            "transcript": "PENDING",
            "korean_pronunciation": "PENDING",
            "lip_sync": "PENDING",
            "visual": "PENDING",
            "continuity": "PENDING",
            "cinematography": "PENDING",
            "user_review": "PENDING",
        },
        "final_included": False,
        "updated_at": utc_now(),
    }
    shots_path = data_dir(root) / "shots.json"
    shots = state["shots"]
    shots.setdefault("items", []).append(shot)
    shots["items"].sort(key=lambda item: (item.get("scene_id", ""), item.get("order", 0), item.get("id", "")))
    shots["updated_at"] = utc_now()
    atomic_write_json(shots_path, shots)
    append_history(root, "shot_added", "agent", "shot", shot_id, {"scene_id": scene_id, "order": order})
    invalidate_reference_estimates(root, "agent", f"shot added: {shot_id}")
    sync_dashboard(root)


def update_shot(root: str | Path, shot_id: str, patch: dict[str, Any], actor: str) -> None:
    """Update a shot plan using an explicit, shallow contract."""
    allowed = {
        "title",
        "duration_seconds",
        "purpose",
        "continuity",
        "boundary",
        "required_asset_ids",
        "references",
        "audio",
        "model",
        "execution",
        "shot_grammar",
        "seedance_plan",
    }
    unknown = sorted(set(patch) - allowed)
    if unknown:
        raise StateError("unsupported shot fields: " + ", ".join(unknown))
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    normalized = deepcopy(patch)
    if "model" in normalized:
        shot["generation"]["model"] = normalized.pop("model")
    if "execution" in normalized:
        value = normalized.pop("execution")
        if not isinstance(value, dict):
            raise StateError("execution must be a JSON object")
        mode = value.get("mode")
        argv = value.get("argv")
        if mode not in {"model", "workflow"}:
            raise StateError("execution.mode must be model or workflow")
        if not isinstance(argv, list) or not argv or not all(isinstance(part, str) for part in argv):
            raise StateError("execution.argv must be a non-empty array of strings")
        shot["generation"]["execution"] = {
            "mode": mode,
            "argv": argv,
            "fingerprint": execution_contract.fingerprint(mode, argv),
        }
    if "shot_grammar" in normalized:
        value = normalized.pop("shot_grammar")
        try:
            shot["shot_grammar"] = cinematography.merge_grammar(shot.get("shot_grammar"), value)
        except cinematography.CinematographyError as exc:
            raise StateError(str(exc)) from exc
    for nested in ("continuity", "boundary", "references", "audio", "seedance_plan"):
        if nested in normalized:
            value = normalized.pop(nested)
            if not isinstance(value, dict):
                raise StateError(f"{nested} must be a JSON object")
            shot[nested].update(value)
    if "required_asset_ids" in normalized:
        value = normalized["required_asset_ids"]
        if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
            raise StateError("required_asset_ids must be a JSON array of strings")
    shot.update(normalized)
    if shot.get("approval_status") not in {"DRAFT", "REVISION_REQUESTED"}:
        shot["approval_status"] = "DRAFT"
        shot.update({"approved_by": None, "approved_at": None})
        shot["generation"]["version"] = int(shot["generation"].get("version", 1)) + 1
    shot["generation"].update({"status": "PLANNED", "job_id": None, "result_path": None})
    shot["qc"] = {key: "PENDING" for key in shot["qc"]}
    shot["final_included"] = False
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "shot_updated", actor, "shot", shot_id, {"fields": sorted(patch)})
    cost_fields = {
        "duration_seconds", "references", "model",
        "execution", "seedance_plan", "shot_grammar",
    }
    if cost_fields & set(patch):
        invalidate_reference_estimates(root, actor, "shot execution profile changed: " + ", ".join(sorted(cost_fields & set(patch))))
    sync_dashboard(root)


def set_boundary(
    root: str | Path,
    shot_id: str,
    strategy: str,
    actor: str,
    *,
    reason: str,
    previous_shot_id: str | None = None,
    previous_frame: str | None = None,
    planned_keyframe: str | None = None,
    cut_type: str | None = None,
) -> None:
    if strategy not in BOUNDARY_STRATEGIES:
        raise StateError(f"invalid boundary strategy: {strategy}")
    if not reason.strip():
        raise StateError("boundary reason is required")
    shots = read_json(data_dir(root) / "shots.json")
    shot = _find(shots.get("items", []), shot_id, "shot")
    references = deepcopy(shot.get("references") or {})
    # Single-start-image video contract: the paid video call carries exactly
    # one start image; identity/location/prop references belong to the
    # start-frame composition step, never to the video generation call.
    references["images"] = []
    if strategy in {"continuous_match", "motivated_transition"}:
        if not previous_shot_id or not previous_frame:
            raise StateError("continuous boundary requires previous_shot_id and previous_frame")
        references["start"] = previous_frame
        inherit = True
    else:
        if not planned_keyframe:
            raise StateError("editorial cut or scene reset requires a composed planned_keyframe start image")
        previous_shot_id = None
        previous_frame = None
        references["start"] = planned_keyframe
        inherit = False
    if strategy == "motivated_transition":
        if not planned_keyframe:
            raise StateError("motivated transition requires planned_keyframe")
        references["end"] = planned_keyframe
        role = "end_image"
    elif strategy == "continuous_match":
        # A pre-designed keyframe may inform story re-alignment and the prompt,
        # but it is never transported in the video call.
        role = "analysis_only" if planned_keyframe else "none"
    else:
        role = "start_image"
    update_shot(
        root,
        shot_id,
        {
            "boundary": {
                "strategy": strategy,
                "previous_shot_id": previous_shot_id,
                "inherit_previous_last_frame": inherit,
                "previous_boundary_frame": previous_frame,
                "planned_keyframe": planned_keyframe,
                "planned_keyframe_role": role,
                "cut_type": cut_type,
                "reason": reason,
            },
            "references": references,
        },
        actor,
    )


def store_reference_estimates(root: str | Path, estimates: dict[str, Any], actor: str) -> None:
    """Store non-authoritative arithmetic guidance derived from actual jobs."""
    path = data_dir(root) / "costs.json"
    costs = read_json(path)
    if not isinstance(estimates, dict) or estimates.get("method") != "recent_actual_arithmetic":
        raise StateError("reference estimate must use recent_actual_arithmetic")
    costs["reference_estimates"] = deepcopy(estimates)
    costs["updated_at"] = utc_now()
    atomic_write_json(path, costs)
    append_history(
        root,
        "reference_costs_calculated",
        actor,
        "cost",
        "production",
        {"covered_shots": estimates.get("covered_shots"), "total_shots": estimates.get("total_shots")},
    )
    sync_dashboard(root)


def record_job(
    root: str | Path,
    shot_id: str,
    job_id: str,
    result_path: str | None,
    actor: str,
) -> None:
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    shot["generation"].update({"job_id": job_id, "result_path": result_path})
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "job_recorded", actor, "shot", shot_id, {"job_id": job_id})
    sync_dashboard(root)


def record_actual_cost(
    root: str | Path,
    entity_id: str,
    credits: float,
    actor: str,
    job_id: str | None = None,
    execution_profile: dict[str, Any] | None = None,
) -> None:
    if credits < 0:
        raise StateError("actual credits must be non-negative")
    costs_path = data_dir(root) / "costs.json"
    costs = read_json(costs_path)
    transaction = {
        "entity_id": entity_id,
        "job_id": job_id,
        "credits": float(credits),
        "recorded_at": utc_now(),
        "execution_profile": deepcopy(execution_profile) if execution_profile else None,
    }
    actual = costs.setdefault("actual", {})
    transactions = actual.setdefault("transactions", [])
    projected = round(sum(float(item.get("credits", 0)) for item in transactions) + float(credits), 6)
    project = read_json(data_dir(root) / "project.json")
    ceiling = project.get("cost_approval", {}).get("max_credits")
    if ceiling is not None and projected > float(ceiling):
        raise StateError("recorded cost would exceed the approved ceiling")
    transactions.append(transaction)
    actual["credits"] = projected
    pending = actual.setdefault("pending", [])
    actual["pending"] = [
        item
        for item in pending
        if not (
            (job_id and item.get("job_id") == job_id)
            or (not job_id and item.get("entity_id") == entity_id)
        )
    ]
    actual["reconciliation_required"] = bool(actual["pending"])
    costs["updated_at"] = utc_now()
    atomic_write_json(costs_path, costs)
    append_history(root, "actual_cost_recorded", actor, "cost", entity_id, transaction)
    sync_dashboard(root)


def require_cost_reconciliation(
    root: str | Path,
    entity_id: str,
    actor: str,
    *,
    job_id: str | None,
    reported_credits: float | None,
    reason: str,
) -> None:
    costs_path = data_dir(root) / "costs.json"
    costs = read_json(costs_path)
    actual = costs.setdefault("actual", {})
    pending = actual.setdefault("pending", [])
    entry = {
        "entity_id": entity_id,
        "job_id": job_id,
        "reported_credits": reported_credits,
        "reason": reason,
        "recorded_at": utc_now(),
    }
    if not any(item.get("job_id") == job_id and item.get("entity_id") == entity_id for item in pending):
        pending.append(entry)
    actual["reconciliation_required"] = True
    costs["updated_at"] = utc_now()
    atomic_write_json(costs_path, costs)
    append_history(root, "actual_cost_reconciliation_required", actor, "cost", entity_id, entry)
    sync_dashboard(root)


def transition_shot_approval(root: str | Path, shot_id: str, target: str, actor: str, reason: str = "") -> None:
    if target not in SHOT_APPROVAL_STATES:
        raise StateError(f"invalid shot approval state: {target}")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    current = shot["approval_status"]
    if target not in SHOT_APPROVAL_TRANSITIONS[current]:
        raise StateError(f"invalid shot approval transition: {current} -> {target}")
    if target in {"USER_APPROVED", "LOCKED_FOR_VIDEO"} and actor != "user":
        raise StateError("only the user may approve or lock a shot board")
    if target in {"INTERNAL_QC_PASSED", "USER_REVIEW", "USER_APPROVED", "LOCKED_FOR_VIDEO"}:
        grammar_errors, _ = cinematography.validate_grammar(
            shot.get("shot_grammar", {}), require_complete=True, shot_duration=shot.get("duration_seconds")
        )
        if grammar_errors:
            raise StateError("shot grammar gate failed: " + "; ".join(grammar_errors))
    shot["approval_status"] = target
    if target == "USER_APPROVED":
        shot.update({"approved_by": actor, "approved_at": utc_now()})
    if target in {"REVISION_REQUESTED", "DRAFT"}:
        shot.update({"approved_by": None, "approved_at": None})
    shot["updated_at"] = utc_now()
    if target == "REVISION_REQUESTED":
        shot["generation"]["version"] = int(shot["generation"].get("version", 1)) + 1
        shot["generation"].update({"status": "PLANNED", "job_id": None, "result_path": None})
        shot["qc"] = {key: "PENDING" for key in shot["qc"]}
        shot["final_included"] = False
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "shot_approval_transition", actor, "shot", shot_id, {"from": current, "to": target, "reason": reason})
    sync_dashboard(root)


def execution_binding_errors(shot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    execution = shot.get("generation", {}).get("execution") or {}
    mode, argv = execution.get("mode"), execution.get("argv") or []
    if mode not in {"model", "workflow"} or not isinstance(argv, list) or not argv:
        return ["shot has no executable model/workflow arguments"]
    expected = execution_contract.fingerprint(mode, argv)
    if execution.get("fingerprint") != expected:
        errors.append("execution fingerprint does not match execution arguments")
    provider, flags = execution_contract.parse_flags(argv)
    binding = shot.get("shot_grammar", {}).get("provider_binding", {})
    if provider != binding.get("provider"):
        errors.append("execution provider does not match compiled grammar")
    if flags.get("prompt") != binding.get("compiled_prompt"):
        errors.append("execution prompt does not match compiled grammar")
    for key, value in (binding.get("native_params") or {}).items():
        if flags.get(key) != value:
            errors.append(f"execution native param does not match compiled grammar: {key}")
    if not binding.get("schema_contract_hash"):
        errors.append("compiled grammar has no schema contract fingerprint")
    return errors


def boundary_plan_errors(shot: dict[str, Any]) -> list[str]:
    plan = shot.get("boundary") or {}
    strategy = plan.get("strategy")
    if strategy not in BOUNDARY_STRATEGIES:
        return ["boundary strategy is undecided or invalid"]
    role = plan.get("planned_keyframe_role")
    if role not in KEYFRAME_ROLES:
        return ["planned keyframe role is invalid"]
    errors: list[str] = []
    if not plan.get("reason"):
        errors.append("boundary director reason is missing")
    if role == "image_reference":
        errors.append("planned keyframe must not ride the video call as an image_reference; single-start-image policy")
    references = shot.get("references") or {}
    inherit = plan.get("inherit_previous_last_frame")
    if strategy in {"continuous_match", "motivated_transition"}:
        if inherit is not True:
            errors.append("continuous boundary must inherit the previous last frame")
        if not plan.get("previous_shot_id"):
            errors.append("continuous boundary is missing previous_shot_id")
        previous_frame = plan.get("previous_boundary_frame")
        if not previous_frame:
            errors.append("continuous boundary is missing the extracted previous frame")
        elif references.get("start") != previous_frame:
            errors.append("previous boundary frame must be transported as start_image")
    elif inherit is not False:
        errors.append("editorial cut or scene reset must not inherit the previous last frame")
    if strategy == "motivated_transition":
        if role != "end_image":
            errors.append("motivated transition must use the planned keyframe as end_image")
        if not plan.get("planned_keyframe") or references.get("end") != plan.get("planned_keyframe"):
            errors.append("motivated transition is missing its planned end keyframe")
    if strategy in {"editorial_cut", "scene_reset"}:
        if not plan.get("planned_keyframe") or references.get("start") != plan.get("planned_keyframe"):
            errors.append("cut/reset requires its composed planned keyframe as the start_image")
    return errors


def start_image_policy_errors(shot: dict[str, Any]) -> list[str]:
    """Enforce the single-start-image video contract.

    A paid video call carries exactly one start image, plus the locked dialogue
    master when the audio route requires it, plus an end image only for a
    motivated transition. Identity, location, and prop references belong to the
    start-frame composition step, never to the video generation call.
    """
    references = shot.get("references") or {}
    strategy = (shot.get("boundary") or {}).get("strategy")
    errors: list[str] = []
    if not references.get("start"):
        errors.append("video execution requires exactly one start image")
    if references.get("images"):
        errors.append("image references are reserved for start-frame composition, not the video call")
    if references.get("end") and strategy != "motivated_transition":
        errors.append("end image is allowed only for a motivated transition")
    execution = shot.get("generation", {}).get("execution") or {}
    argv = execution.get("argv") or []
    if isinstance(argv, list) and argv:
        _, flags = execution_contract.parse_flags(argv)
        if flags.get("image_references"):
            errors.append("execution argv must not carry image_references")
        if references.get("start") and flags.get("start_image") != references.get("start"):
            errors.append("execution start_image must match references.start")
        if flags.get("end_image") and strategy != "motivated_transition":
            errors.append("execution end_image is allowed only for a motivated transition")
    return errors


def audio_plan_errors(shot: dict[str, Any]) -> list[str]:
    audio = shot.get("audio") or {}
    route = audio.get("route")
    if route not in AUDIO_ROUTES:
        return ["audio route is undecided or invalid"]
    audio_mode = (shot.get("seedance_plan") or {}).get("audio_mode")
    errors: list[str] = []
    if route in {"NO_DIALOGUE_POST", "OFFSCREEN_NARRATION"} and audio_mode != "post_only":
        errors.append("non-visible speech routes must generate picture with audio_mode=post_only")
    if route == "INTENTIONAL_SILENCE" and audio_mode != "none":
        errors.append("intentional silence must use audio_mode=none")
    if route == "OFFSCREEN_NARRATION" and audio.get("has_visible_dialogue") is not False:
        errors.append("off-screen narration must declare has_visible_dialogue=false")
    if route == "VISIBLE_DIALOGUE_ELEVENLABS_V3":
        if audio_mode != "audio_reference":
            errors.append("visible dialogue must use the locked ElevenLabs master as audio_reference")
        if audio.get("voice_provider") != "elevenlabs" or audio.get("voice_model") != "eleven_v3":
            errors.append("visible dialogue must lock voice_provider=elevenlabs and voice_model=eleven_v3")
        master = audio.get("dialogue_master_path")
        if not master:
            errors.append("visible dialogue is missing the locked dialogue master")
        elif master not in (shot.get("references") or {}).get("audios", []):
            errors.append("dialogue master must be present in audio_references")
        if audio.get("discard_generated_track") is not True:
            errors.append("visible dialogue must discard the Seedance-rendered audio track")
        if audio.get("final_mix_required") is not True:
            errors.append("visible dialogue must require a final external mix")
    return errors


def shot_gate_errors(state: dict[str, dict[str, Any]], shot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = state["project"]
    if project.get("requirements_lock", {}).get("status") != "LOCKED":
        errors.append("requirements are not locked")
    if project.get("cost_approval", {}).get("status") != "APPROVED":
        errors.append("cost ceiling is not approved")
    if shot.get("approval_status") != "LOCKED_FOR_VIDEO":
        errors.append("shot board is not locked for video")
    assets = {item.get("id"): item for item in state["assets"].get("items", [])}
    for asset_id in shot.get("required_asset_ids", []):
        if assets.get(asset_id, {}).get("status") != "LOCKED_FOR_VIDEO":
            errors.append(f"required asset is not locked: {asset_id}")
    continuity = shot.get("continuity", {})
    missing_context = [key for key, value in continuity.items() if not value]
    if missing_context:
        errors.append("continuity context missing: " + ", ".join(missing_context))
    errors.extend(boundary_plan_errors(shot))
    errors.extend(start_image_policy_errors(shot))
    errors.extend(audio_plan_errors(shot))
    binding = shot.get("shot_grammar", {}).get("provider_binding", {})
    if binding.get("provider") in {"seedance_2_0", "seedance_2_0_mini"}:
        plan = shot.get("seedance_plan") or {}
        required_aspect = project.get("project", {}).get("aspect_ratio")
        required_resolution = project.get("project", {}).get("resolution")
        if required_aspect and plan.get("aspect_ratio") != required_aspect:
            errors.append("Seedance aspect ratio does not match locked project requirements")
        if required_resolution and plan.get("resolution") != required_resolution:
            errors.append("Seedance resolution does not match locked project requirements")
    grammar_errors, _ = cinematography.validate_grammar(
        shot.get("shot_grammar", {}), require_complete=True, shot_duration=shot.get("duration_seconds")
    )
    errors.extend(f"shot grammar: {message}" for message in grammar_errors)
    errors.extend(execution_binding_errors(shot))
    return errors


def transition_generation(root: str | Path, shot_id: str, target: str, actor: str, reason: str = "") -> None:
    if target not in GENERATION_STATES:
        raise StateError(f"invalid generation state: {target}")
    state = load_all(root)
    shot = _find(state["shots"].get("items", []), shot_id, "shot")
    current = shot["generation"]["status"]
    if target not in GENERATION_TRANSITIONS[current]:
        raise StateError(f"invalid generation transition: {current} -> {target}")
    if target in {"QUEUED", "GENERATING", "GENERATED"}:
        gates = shot_gate_errors(state, shot)
        if gates:
            raise StateError("generation gate failed: " + "; ".join(gates))
    if target == "FINAL_COMPLETE":
        required_qc = ("technical", "transcript", "lip_sync", "visual", "continuity", "cinematography", "user_review")
        bad = [key for key in required_qc if shot.get("qc", {}).get(key) not in {"PASSED", "NOT_APPLICABLE"}]
        if bad:
            raise StateError("final gate failed; QC incomplete: " + ", ".join(bad))
        shot["final_included"] = True
    shot["generation"]["status"] = target
    if target == "FAILED":
        shot["generation"]["retry_count"] = int(shot["generation"].get("retry_count", 0)) + 1
    shot["updated_at"] = utc_now()
    state["shots"]["updated_at"] = utc_now()
    atomic_write_json(data_dir(root) / "shots.json", state["shots"])
    append_history(root, "generation_transition", actor, "shot", shot_id, {"from": current, "to": target, "reason": reason})
    sync_dashboard(root)


def set_qc(root: str | Path, shot_id: str, check: str, status: str, actor: str, note: str = "") -> None:
    if status not in QC_STATES:
        raise StateError(f"invalid QC state: {status}")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    if check not in shot.get("qc", {}):
        raise StateError(f"unknown QC check: {check}")
    if check == "user_review" and status == "PASSED" and actor != "user":
        raise StateError("only the user may pass user_review QC")
    shot["qc"][check] = status
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "qc_updated", actor, "shot", shot_id, {"check": check, "status": status, "note": note})
    sync_dashboard(root)


def validate(root: str | Path) -> list[str]:
    state = load_all(root)
    errors: list[str] = []
    for name, document in state.items():
        if document.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{name}: unsupported schema_version")
    for collection in ("assets", "scenes", "shots"):
        ids = [item.get("id") for item in state[collection].get("items", [])]
        if len(ids) != len(set(ids)):
            errors.append(f"{collection}: duplicate ids")
    if state["project"].get("requirements_lock", {}).get("status") == "LOCKED":
        for field in REQUIRED_REQUIREMENTS:
            if state["requirements"]["fields"].get(field, {}).get("status") != "CONFIRMED":
                errors.append(f"locked requirements contain unconfirmed field: {field}")
    for asset in state["assets"].get("items", []):
        if asset.get("status") not in ASSET_STATES:
            errors.append(f"asset {asset.get('id')}: invalid status")
        if asset.get("status") == "LOCKED_FOR_VIDEO" and not asset.get("approved_by"):
            errors.append(f"asset {asset.get('id')}: locked without approval")
        if asset.get("contains_korean_text") and asset.get("status") == "LOCKED_FOR_VIDEO" and asset.get("ocr_status") != "PASSED":
            errors.append(f"asset {asset.get('id')}: Korean text not OCR-passed")
    for shot in state["shots"].get("items", []):
        if shot.get("approval_status") not in SHOT_APPROVAL_STATES:
            errors.append(f"shot {shot.get('id')}: invalid approval status")
        if shot.get("approval_status") == "LOCKED_FOR_VIDEO" and not shot.get("approved_by"):
            errors.append(f"shot {shot.get('id')}: locked without approval")
        if shot.get("generation", {}).get("status") not in GENERATION_STATES:
            errors.append(f"shot {shot.get('id')}: invalid generation status")
        if shot.get("generation", {}).get("status") in {"QUEUED", "GENERATING", "GENERATED", "FINAL_COMPLETE"}:
            errors.extend(f"shot {shot.get('id')}: {message}" for message in shot_gate_errors(state, shot))
        if "shot_grammar" not in shot:
            errors.append(f"shot {shot.get('id')}: missing shot_grammar")
        else:
            grammar_errors, _ = cinematography.validate_grammar(
                shot["shot_grammar"],
                require_complete=shot.get("approval_status") not in {"DRAFT", "REVISION_REQUESTED", "HOLD"},
                shot_duration=shot.get("duration_seconds"),
            )
            errors.extend(f"shot {shot.get('id')}: shot grammar: {message}" for message in grammar_errors)
        for key, value in shot.get("qc", {}).items():
            if value not in QC_STATES:
                errors.append(f"shot {shot.get('id')}: invalid QC state for {key}")
    approved = state["project"].get("cost_approval", {})
    actual = float(state["costs"].get("actual", {}).get("credits", 0) or 0)
    if approved.get("status") == "APPROVED" and approved.get("max_credits") is not None:
        if actual > float(approved["max_credits"]):
            errors.append("actual credits exceed the approved ceiling")
    return errors


def aggregate(root: str | Path) -> dict[str, Any]:
    state = load_all(root)
    shots = state["shots"].get("items", [])
    assets = state["assets"].get("items", [])
    completed = sum(1 for shot in shots if shot.get("generation", {}).get("status") == "FINAL_COMPLETE")
    generated = sum(1 for shot in shots if shot.get("generation", {}).get("status") in {"GENERATED", "FINAL_COMPLETE"})
    qc_passed = sum(
        1
        for shot in shots
        if all(value in {"PASSED", "NOT_APPLICABLE"} for value in shot.get("qc", {}).values())
    )
    grammar_validated = sum(
        1
        for shot in shots
        if not cinematography.validate_grammar(
            shot.get("shot_grammar", {}), require_complete=True, shot_duration=shot.get("duration_seconds")
        )[0]
    )
    blockers: list[str] = []
    if state["project"].get("requirements_lock", {}).get("status") != "LOCKED":
        blockers.append("요구사항 승인 필요")
    if state["project"].get("cost_approval", {}).get("status") != "APPROVED":
        blockers.append("비용 상한 승인 필요")
    if state["costs"].get("actual", {}).get("reconciliation_required"):
        blockers.append("실제 크레딧 사용량 대사 필요")
    blockers.extend(
        f"{shot.get('id')}: {message}"
        for shot in shots
        if shot.get("generation", {}).get("status") in {"READY", "QUEUED"}
        for message in shot_gate_errors(state, shot)
    )
    total = len(shots)
    progress = round((completed / total) * 100, 1) if total else 0.0
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "project": state["project"],
        "requirements": state["requirements"],
        "assets": assets,
        "scenes": state["scenes"].get("items", []),
        "shots": shots,
        "costs": state["costs"],
        "history": state["history"].get("events", []),
        "summary": {
            "progress_percent": progress,
            "total_shots": total,
            "generated_shots": generated,
            "qc_passed_shots": qc_passed,
            "validated_grammar_shots": grammar_validated,
            "completed_shots": completed,
            "locked_assets": sum(1 for asset in assets if asset.get("status") == "LOCKED_FOR_VIDEO"),
            "pending_approvals": sum(1 for asset in assets if asset.get("status") == "USER_REVIEW")
            + sum(1 for shot in shots if shot.get("approval_status") == "USER_REVIEW"),
            "blockers": blockers,
        },
    }


def sync_dashboard(root: str | Path) -> Path:
    production = _root(root)
    dashboard = production / "dashboard"
    dashboard.mkdir(parents=True, exist_ok=True)
    state = aggregate(production)
    payload = "window.SONOL_HIGGSFIELD_STATE = " + json.dumps(state, ensure_ascii=False, indent=2) + ";\n"
    target = dashboard / "project-data.js"
    fd, tmp_name = tempfile.mkstemp(prefix=".project-data.", dir=dashboard)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return target
