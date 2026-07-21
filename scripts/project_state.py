#!/usr/bin/env python3
"""Durable state and gate logic for sonol-higgsfield productions."""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cinematography
import director_intelligence
import execution_contract


SCHEMA_VERSION = 9
PRODUCTION_MODES = {
    "QUICK_CLIP",
    "NATIVE_MULTISHOT",
    "CONTROLLED_SHOT",
    "SERIAL_STORY",
    "OFFICIAL_WORKFLOW",
}
APPROVAL_PROFILES = {"LIGHT", "TARGETED", "FULL"}
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
    "SUBMITTING",
    "SUBMISSION_AMBIGUOUS",
    "SUBMITTED",
    "QUEUED",
    "RUNNING",
    "REMOTE_UNKNOWN",
    "PROVIDER_COMPLETED",
    "GENERATED",
    "FAILED",
    "QC_FAILED",
    "FINAL_COMPLETE",
}
GENERATION_TRANSITIONS = {
    "PLANNED": {"READY", "FAILED"},
    "READY": {"SUBMITTING", "FAILED"},
    "SUBMITTING": {"SUBMITTED", "SUBMISSION_AMBIGUOUS", "FAILED"},
    "SUBMISSION_AMBIGUOUS": {"SUBMITTED", "FAILED"},
    "SUBMITTED": {"QUEUED", "RUNNING", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED", "FAILED"},
    "QUEUED": {"SUBMITTED", "RUNNING", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED", "FAILED"},
    "RUNNING": {"SUBMITTED", "QUEUED", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED", "FAILED"},
    "REMOTE_UNKNOWN": {"SUBMITTED", "QUEUED", "RUNNING", "PROVIDER_COMPLETED", "FAILED"},
    "PROVIDER_COMPLETED": {"GENERATED"},
    "GENERATED": {"QC_FAILED", "FINAL_COMPLETE", "READY"},
    "FAILED": {"READY", "SUBMITTED", "QUEUED", "RUNNING", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED"},
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
    "NO_DIALOGUE_NATIVE_SOUND",
    "NO_DIALOGUE_POST",
    "INTENTIONAL_SILENCE",
    "OFFSCREEN_NARRATION",
    "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO",
}
BOUNDARY_OBSERVATION_FIELDS = ("pose", "gaze", "hands", "props", "framing", "lighting", "emotion")
START_IMAGE_REVIEW_FIELDS = (
    "final_first_frame",
    "aspect_ratio_match",
    "no_collage_or_labels",
    "key_subject_readable",
    "action_compatible",
)
OFF_FRAME_REVEAL_RISKS = {"LOW", "MEDIUM", "HIGH"}
DIALOGUE_IMPACTS = {"NOT_APPLICABLE", "UNCHANGED", "RERECORDED"}
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
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
        "end_keyframe": None,
        "end_keyframe_role": "none",
        "cut_type": None,
        "reason": None,
        "start_image_provenance": {
            "mode": None,
            "created_after_shot_id": None,
            "created_at": None,
        },
    }


def default_audio_plan() -> dict[str, Any]:
    return {
        "route": "UNDECIDED",
        "has_visible_dialogue": None,
        "voice_provider": None,
        "voice_model": None,
        "voice_ids": [],
        "dialogue_reference_path": None,
        "dialogue_reference_sha256": None,
        "narration_master_path": None,
        "narration_master_sha256": None,
        "generated_track_policy": "UNDECIDED",
        "final_mix_required": None,
        "final_mix_path": None,
    }


def default_story_contract() -> dict[str, Any]:
    return {
        "status": "DRAFT",
        "version": 0,
        "anchor_beats": [],
        "locked_by": None,
        "locked_at": None,
    }


def default_shot_story() -> dict[str, Any]:
    return {
        "anchor_beat_ids": [],
        "story_contract_version": None,
        "adaptive_revision": 0,
        "based_on_previous_shot_id": None,
        "based_on_boundary_analysis_id": None,
        "adjustment_reason": None,
        "dialogue_impact": "NOT_APPLICABLE",
        "dialogue_reference_sha256": None,
        "recorded_audio_sha256": None,
    }


def default_boundary_analysis() -> dict[str, Any]:
    return {
        "status": "PENDING",
        "analysis_id": None,
        "frame_path": None,
        "observations": {key: None for key in BOUNDARY_OBSERVATION_FIELDS},
        "technical": {
            "selection_method": None,
            "window_seconds": None,
            "selected_timestamp": None,
            "selected_blur_score": None,
            "selected_candidate_path": None,
            "selection_reason": None,
            "candidates": [],
        },
        "next_story_adjustment": None,
        "analyzed_by": None,
        "analyzed_at": None,
    }


def default_start_frame_qc() -> dict[str, Any]:
    return {
        "status": "PENDING",
        "submitted_start_path": None,
        "rendered_first_frame_path": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "notes": None,
        "comparison": None,
    }


def default_start_image_review() -> dict[str, Any]:
    return {
        "status": "PENDING",
        "start_image_path": None,
        "assessment": {
            **{key: None for key in START_IMAGE_REVIEW_FIELDS},
            "off_frame_reveal_risk": None,
        },
        "notes": None,
        "reviewed_by": None,
        "reviewed_at": None,
    }


def default_generation_attempts() -> dict[str, Any]:
    return {
        "active_attempt_id": None,
        "attempts": [],
    }


def default_production_policy() -> dict[str, Any]:
    """Backwards-safe managed default; the router may select a lighter path."""
    return {
        "mode": "SERIAL_STORY",
        "approval_profile": "FULL",
        "official_workflow": None,
        "managed_state": True,
        "selected_by": None,
        "selected_at": None,
        "reason": "default for migrated and explicitly managed productions",
    }


def default_director_intelligence() -> dict[str, Any]:
    return {
        "performance_direction": None,
        "camera_intent": None,
        "prompt_lint": None,
        "complexity": None,
        "failure_analysis": None,
    }


def initialize(
    root: str | Path,
    name: str,
    template_dir: Path,
    production_policy: dict[str, Any] | None = None,
) -> Path:
    production = _root(root)
    if production.exists() and any(production.iterdir()):
        raise StateError(f"production directory is not empty: {production}")
    production.mkdir(parents=True, exist_ok=True)
    (production / "data").mkdir(exist_ok=True)
    for media_type in ("images", "videos", "audio"):
        (production / "media" / media_type).mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_dir, production / "dashboard", dirs_exist_ok=True)

    initial_policy = deepcopy(production_policy or default_production_policy())
    if initial_policy.get("mode") not in PRODUCTION_MODES:
        raise StateError("initial production policy has an invalid mode")
    if initial_policy.get("approval_profile") not in APPROVAL_PROFILES:
        raise StateError("initial production policy has an invalid approval profile")
    if initial_policy.get("mode") == "OFFICIAL_WORKFLOW" and initial_policy.get("official_workflow") not in {"marketing_studio", "video_explainer"}:
        raise StateError("official workflow mode requires marketing_studio or video_explainer")
    if initial_policy.get("mode") != "OFFICIAL_WORKFLOW" and initial_policy.get("official_workflow") is not None:
        raise StateError("official_workflow is only valid for OFFICIAL_WORKFLOW mode")
    for key, value in default_production_policy().items():
        initial_policy.setdefault(key, deepcopy(value))
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
        "story_contract": default_story_contract(),
        "production_policy": initial_policy,
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
        "actual": {
            "credits": 0.0,
            "transactions": [],
            "reconciliation_required": False,
            "pending": [],
            "ceiling_breach": False,
        },
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
    if only_version not in {1, 2, 3, 4, 5, 6, 7, 8}:
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
            binding.setdefault("prompt_lint", None)
        shot.setdefault("seedance_plan", cinematography.default_seedance_plan())
        for key, value in cinematography.default_seedance_plan().items():
            shot["seedance_plan"].setdefault(key, deepcopy(value))
        image_policy = shot["seedance_plan"].setdefault(
            "image_input_policy", deepcopy(cinematography.default_seedance_plan()["image_input_policy"])
        )
        for key, value in cinematography.default_seedance_plan()["image_input_policy"].items():
            image_policy.setdefault(key, deepcopy(value))
        if from_version <= 4 and shot["seedance_plan"].get("audio_mode") == "none":
            shot["seedance_plan"]["audio_mode"] = "post_only"
        references = shot.setdefault("references", {})
        references.setdefault("manifest", [])
        shot.setdefault("boundary", default_boundary_plan())
        boundary = shot["boundary"]
        for key, value in default_boundary_plan().items():
            boundary.setdefault(key, deepcopy(value))
        boundary.setdefault("start_image_provenance", deepcopy(default_boundary_plan()["start_image_provenance"]))
        shot.setdefault("story", default_shot_story())
        shot.setdefault("boundary_analysis", default_boundary_analysis())
        shot.setdefault("start_frame_qc", default_start_frame_qc())
        shot["start_frame_qc"].setdefault("comparison", None)
        if "start_image_review" not in shot:
            review = default_start_image_review()
            if from_version == 6 and shot.get("generation", {}).get("status") in {"GENERATED", "FINAL_COMPLETE"}:
                review["status"] = "NOT_APPLICABLE"
                review["notes"] = "Migrated after generation; no v7 preflight review evidence exists."
            shot["start_image_review"] = review
        if (shot.get("references") or {}).get("end"):
            image_policy.update(
                {
                    "mode": "start_end_transition",
                    "rationale": (shot.get("boundary") or {}).get("reason") or "migrated motivated transition",
                }
            )
        audio = shot.setdefault("audio", {})
        if audio.get("route") == "VISIBLE_DIALOGUE_ELEVENLABS_V3":
            audio["route"] = "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO"
        if not audio.get("dialogue_reference_path") and "dialogue_master_path" in audio:
            audio["dialogue_reference_path"] = audio.get("dialogue_master_path")
        if not audio.get("dialogue_reference_sha256") and "dialogue_master_sha256" in audio:
            audio["dialogue_reference_sha256"] = audio.get("dialogue_master_sha256")
        audio.pop("dialogue_master_path", None)
        audio.pop("dialogue_master_sha256", None)
        audio.pop("discard_generated_track", None)
        for key, value in default_audio_plan().items():
            audio.setdefault(key, deepcopy(value))
        route = audio.get("route")
        if route == "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO":
            audio["generated_track_policy"] = "PRESERVE"
            audio["final_mix_required"] = False
        elif route in {"NO_DIALOGUE_POST", "OFFSCREEN_NARRATION", "INTENTIONAL_SILENCE"}:
            audio["generated_track_policy"] = "NOT_GENERATED"
            audio["final_mix_required"] = route in {"NO_DIALOGUE_POST", "OFFSCREEN_NARRATION"}
        story = shot.setdefault("story", default_shot_story())
        if not story.get("dialogue_reference_sha256") and "dialogue_master_sha256" in story:
            story["dialogue_reference_sha256"] = story.get("dialogue_master_sha256")
        story.pop("dialogue_master_sha256", None)
        generation = shot.setdefault("generation", {})
        generation.pop("cost_argv", None)
        generation.pop("cost_options", None)
        execution = generation.setdefault("execution", {"mode": None, "argv": []})
        execution.setdefault("fingerprint", None)
        generation.setdefault("active_attempt_id", None)
        shot.setdefault("director_intelligence", default_director_intelligence())
        for key, value in default_director_intelligence().items():
            shot["director_intelligence"].setdefault(key, deepcopy(value))
        attempts = generation.setdefault("attempts", [])
        legacy_status = generation.get("status")
        legacy_job_id = generation.get("job_id")
        if not attempts and (legacy_job_id or legacy_status in {"QUEUED", "GENERATING"}):
            attempt_id = "ATTEMPT_MIGRATED_001"
            remote_status = "COMPLETED" if legacy_status in {"GENERATED", "QC_FAILED", "FINAL_COMPLETE"} else "UNKNOWN"
            resolution = "RECORDED" if remote_status == "COMPLETED" else "PENDING"
            attempts.append(
                {
                    "attempt_id": attempt_id,
                    "generation_version": generation.get("version", 1),
                    "execution_fingerprint": execution.get("fingerprint"),
                    "provider": generation.get("model"),
                    "mode": execution.get("mode"),
                    "match_signature": None,
                    "started_at": shot.get("updated_at") or utc_now(),
                    "submitted_at": shot.get("updated_at") if legacy_job_id else None,
                    "last_checked_at": None,
                    "resolved_at": shot.get("updated_at") if resolution == "RECORDED" else None,
                    "job_id": legacy_job_id,
                    "remote_status": remote_status,
                    "raw_remote_status": None,
                    "resolution": resolution,
                    "ambiguity_reason": "migrated legacy in-flight state" if resolution == "PENDING" else None,
                    "account_credits_before": None,
                    "account_credits_after": None,
                    "cost_uncertainty_acknowledged": False,
                    "result_available": legacy_status in {"GENERATED", "QC_FAILED", "FINAL_COMPLETE"},
                }
            )
            if resolution == "PENDING":
                generation["active_attempt_id"] = attempt_id
        for attempt in attempts:
            if isinstance(attempt, dict):
                attempt.setdefault("cost_uncertainty_acknowledged", False)
                attempt.setdefault("review", None)
        if legacy_status == "GENERATING":
            generation["status"] = "SUBMITTED" if legacy_job_id else "SUBMISSION_AMBIGUOUS"
        elif legacy_status == "QUEUED" and not legacy_job_id:
            generation["status"] = "SUBMISSION_AMBIGUOUS"
        elif legacy_job_id and generation.get("active_attempt_id"):
            generation["status"] = "SUBMITTED"
        shot.setdefault("qc", {})["cinematography"] = "PENDING"
    approval = state["project"].setdefault("cost_approval", {})
    approval.pop("scenario", None)
    approval.pop("task_contracts", None)
    approval.setdefault("mode", "PROJECT_CEILING")
    approval.setdefault("unpriced_job_risk_acknowledged", approval.get("status") == "APPROVED")
    state["project"].setdefault("story_contract", default_story_contract())
    state["project"].setdefault("production_policy", default_production_policy())
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
    ceiling = approval.get("max_credits")
    actual.setdefault(
        "ceiling_breach",
        ceiling is not None and float(actual.get("credits", 0) or 0) > float(ceiling),
    )
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


def set_production_policy(
    root: str | Path,
    mode: str,
    approval_profile: str,
    actor: str,
    reason: str,
    official_workflow: str | None = None,
) -> None:
    """Persist a routing decision without changing or cancelling provider jobs."""
    if mode not in PRODUCTION_MODES:
        raise StateError(f"invalid production mode: {mode}")
    if approval_profile not in APPROVAL_PROFILES:
        raise StateError(f"invalid approval profile: {approval_profile}")
    if not reason.strip():
        raise StateError("production policy reason is required")
    if mode == "OFFICIAL_WORKFLOW" and official_workflow not in {"marketing_studio", "video_explainer"}:
        raise StateError("official workflow mode requires marketing_studio or video_explainer")
    if mode != "OFFICIAL_WORKFLOW" and official_workflow is not None:
        raise StateError("official_workflow is only valid for OFFICIAL_WORKFLOW mode")
    path = data_dir(root) / "project.json"
    project = read_json(path)
    project["production_policy"] = {
        "mode": mode,
        "approval_profile": approval_profile,
        "official_workflow": official_workflow,
        "managed_state": mode not in {"QUICK_CLIP", "OFFICIAL_WORKFLOW"},
        "selected_by": actor,
        "selected_at": utc_now(),
        "reason": reason.strip(),
    }
    project["updated_at"] = utc_now()
    atomic_write_json(path, project)
    append_history(root, "production_policy_selected", actor, "project", "PROJECT_001", project["production_policy"])
    sync_dashboard(root)


def record_director_analysis(
    root: str | Path,
    shot_id: str,
    category: str,
    analysis: dict[str, Any],
    actor: str,
) -> None:
    allowed = set(default_director_intelligence())
    if category not in allowed:
        raise StateError("invalid director-intelligence category: " + category)
    if not isinstance(analysis, dict):
        raise StateError("director analysis must be a JSON object")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    shot.setdefault("director_intelligence", default_director_intelligence())[category] = deepcopy(analysis)
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "director_analysis_recorded", actor, "shot", shot_id, {"category": category})
    sync_dashboard(root)


def record_attempt_review(
    root: str | Path,
    shot_id: str,
    attempt_id: str,
    result: str,
    reject_reasons: list[str],
    severity: str,
    actor: str,
    *,
    human_confirmed: bool = False,
    notes: str = "",
) -> dict[str, Any]:
    if result not in {"ACCEPTED", "REJECTED"}:
        raise StateError("attempt review result must be ACCEPTED or REJECTED")
    if severity not in {"MINOR", "MAJOR", "CRITICAL", "NONE"}:
        raise StateError("invalid attempt review severity")
    valid_reasons = set(director_intelligence._load("reject-reasons.json")["reasons"])
    unknown = sorted(set(reject_reasons) - valid_reasons)
    if unknown:
        raise StateError("unknown reject reasons: " + ", ".join(unknown))
    if result == "ACCEPTED" and reject_reasons:
        raise StateError("accepted attempt must not carry reject reasons")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    attempt = next((item for item in shot.get("generation", {}).get("attempts", []) if item.get("attempt_id") == attempt_id), None)
    if attempt is None:
        raise StateError(f"unknown generation attempt: {attempt_id}")
    if not attempt.get("result_available"):
        raise StateError("generation attempt cannot be reviewed before a provider result is available")
    review = {
        "result": result,
        "reject_reasons": list(dict.fromkeys(reject_reasons)),
        "severity": severity,
        "human_confirmed": bool(human_confirmed),
        "notes": notes or None,
        "reviewed_by": actor,
        "reviewed_at": utc_now(),
    }
    attempt["review"] = review
    comparable = [item["review"] for item in shot["generation"]["attempts"] if isinstance(item.get("review"), dict)]
    analysis = director_intelligence.diagnose_failures(comparable)
    shot.setdefault("director_intelligence", default_director_intelligence())["failure_analysis"] = analysis
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "generation_attempt_reviewed", actor, "shot", shot_id, {"attempt_id": attempt_id, "result": result, "reject_reasons": review["reject_reasons"]})
    sync_dashboard(root)
    return analysis


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
    profile = ((project.get("production_policy") or {}).get("approval_profile") or "FULL")
    if profile == "FULL" and project.get("requirements_lock", {}).get("status") != "LOCKED":
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
    costs_actual = costs.setdefault("actual", {})
    costs_actual["ceiling_breach"] = actual > max_credits
    costs["updated_at"] = utc_now()
    atomic_write_json(data_dir(root) / "costs.json", costs)
    append_history(
        root,
        "project_credit_ceiling_approved",
        actor,
        "project",
        project["project"]["id"],
        {"max_credits": max_credits, "live_quote_removed": True, "approval_profile": profile},
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
        "story": default_shot_story(),
        "boundary_analysis": default_boundary_analysis(),
        "start_image_review": default_start_image_review(),
        "start_frame_qc": default_start_frame_qc(),
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
        "director_intelligence": default_director_intelligence(),
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
            **default_generation_attempts(),
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
        "story",
        "start_image_review",
    }
    unknown = sorted(set(patch) - allowed)
    if unknown:
        raise StateError("unsupported shot fields: " + ", ".join(unknown))
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    submission_sensitive = set(patch) - {"title", "purpose"}
    if submission_sensitive and unresolved_submission(shot):
        raise StateError(
            "cannot change submitted generation inputs while a provider attempt is unresolved; reconcile or resolve it first"
        )
    if not submission_sensitive and unresolved_submission(shot):
        shot.update(deepcopy(patch))
        shot["updated_at"] = utc_now()
        shots["updated_at"] = utc_now()
        atomic_write_json(path, shots)
        append_history(root, "shot_metadata_updated", actor, "shot", shot_id, {"fields": sorted(patch)})
        sync_dashboard(root)
        return
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
    image_review_invalidated = "references" in normalized or "boundary" in normalized or (
        isinstance(normalized.get("seedance_plan"), dict)
        and "image_input_policy" in normalized["seedance_plan"]
    )
    for nested in ("continuity", "boundary", "references", "audio", "seedance_plan", "story", "start_image_review"):
        if nested in normalized:
            value = normalized.pop(nested)
            if not isinstance(value, dict):
                raise StateError(f"{nested} must be a JSON object")
            shot[nested].update(value)
    if image_review_invalidated and "start_image_review" not in patch:
        shot["start_image_review"] = default_start_image_review()
    if "required_asset_ids" in normalized:
        value = normalized["required_asset_ids"]
        if not isinstance(value, list) or not all(isinstance(part, str) for part in value):
            raise StateError("required_asset_ids must be a JSON array of strings")
    shot.update(normalized)
    if shot.get("approval_status") not in {"DRAFT", "REVISION_REQUESTED"}:
        shot["approval_status"] = "DRAFT"
        shot.update({"approved_by": None, "approved_at": None})
        shot["generation"]["version"] = int(shot["generation"].get("version", 1)) + 1
    shot["generation"].update(
        {"status": "PLANNED", "active_attempt_id": None, "job_id": None, "result_path": None}
    )
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
    end_keyframe: str | None = None,
    cut_type: str | None = None,
) -> None:
    if strategy not in BOUNDARY_STRATEGIES:
        raise StateError(f"invalid boundary strategy: {strategy}")
    if not reason.strip():
        raise StateError("boundary reason is required")
    all_state = load_all(root)
    shots = all_state["shots"]
    shot = _find(shots.get("items", []), shot_id, "shot")
    ordered = ordered_shots(all_state)
    shot_index = next(index for index, item in enumerate(ordered) if item.get("id") == shot_id)
    chronological_previous = ordered[shot_index - 1] if shot_index else None
    chronological_previous_id = chronological_previous.get("id") if chronological_previous else None
    previous_analysis: dict[str, Any] = {}
    if chronological_previous is not None:
        if chronological_previous.get("generation", {}).get("status") not in {"GENERATED", "FINAL_COMPLETE"}:
            raise StateError("next boundary cannot be set before the previous sequential shot is generated")
        if chronological_previous.get("qc", {}).get("user_review") != "PASSED":
            raise StateError("next boundary cannot be set before previous user acceptance")
        previous_analysis = chronological_previous.get("boundary_analysis") or {}
    references = deepcopy(shot.get("references") or {})
    # Reset every boundary to the minimum-sufficient baseline. A later explicit
    # recovery patch may add one evidenced essential image reference.
    references["images"] = []
    references["end"] = None
    wants_inheritance = strategy == "continuous_match" or (
        strategy == "motivated_transition" and bool(previous_shot_id or previous_frame)
    )
    if bool(previous_shot_id) != bool(previous_frame):
        raise StateError("previous_shot_id and previous_frame must be supplied together")
    if wants_inheritance:
        if not previous_shot_id or not previous_frame:
            raise StateError("continuous boundary requires previous_shot_id and previous_frame")
        if chronological_previous is None or chronological_previous_id is None or previous_shot_id != chronological_previous_id:
            raise StateError("chained boundary must use the immediate previous sequential shot")
        if (chronological_previous.get("start_frame_qc") or {}).get("status") != "PASSED":
            raise StateError("inherited boundary requires previous start-frame QC to pass")
        if previous_analysis.get("status") != "COMPLETE":
            raise StateError("inherited boundary requires previous boundary analysis")
        if previous_frame != previous_analysis.get("frame_path"):
            raise StateError("chained boundary must use the selected previous boundary-analysis frame")
        references["start"] = previous_frame
        inherit = True
        provenance = {"mode": "previous_boundary", "created_after_shot_id": previous_shot_id, "created_at": utc_now()}
    else:
        if not planned_keyframe:
            raise StateError("non-inherited boundary requires a composed planned_keyframe start image")
        previous_shot_id = chronological_previous_id
        previous_frame = None
        references["start"] = planned_keyframe
        inherit = False
        provenance = {
            "mode": "initial_composition" if chronological_previous_id is None else "jit_composition",
            "created_after_shot_id": chronological_previous_id,
            "created_at": utc_now(),
        }
    if wants_inheritance:
        # A pre-designed keyframe may inform story re-alignment and the prompt,
        # but it is never transported in the video call.
        role = "analysis_only" if planned_keyframe else "none"
    else:
        role = "start_image"
    end_role = "none"
    if end_keyframe:
        if strategy != "motivated_transition":
            raise StateError("end_keyframe is allowed only for a motivated transition")
        references["end"] = end_keyframe
        end_role = "end_image"
    image_input_policy = deepcopy(cinematography.default_seedance_plan()["image_input_policy"])
    if end_keyframe:
        image_input_policy.update({"mode": "start_end_transition", "rationale": reason.strip()})
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
                "end_keyframe": end_keyframe,
                "end_keyframe_role": end_role,
                "cut_type": cut_type,
                "reason": reason,
                "start_image_provenance": provenance,
            },
            "references": references,
            "seedance_plan": {"image_input_policy": image_input_policy},
        },
        actor,
    )


def lock_story_contract(root: str | Path, anchor_beats: list[dict[str, Any]], actor: str) -> None:
    if actor != "user":
        raise StateError("only the user may lock story anchor beats")
    if not isinstance(anchor_beats, list) or not anchor_beats:
        raise StateError("story contract requires at least one anchor beat")
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for offset, beat in enumerate(anchor_beats):
        if not isinstance(beat, dict):
            raise StateError(f"anchor beat {offset + 1} must be an object")
        beat_id = beat.get("id")
        description = beat.get("description")
        if not isinstance(beat_id, str) or not beat_id.strip():
            raise StateError(f"anchor beat {offset + 1} requires id")
        if not isinstance(description, str) or not description.strip():
            raise StateError(f"anchor beat {offset + 1} requires description")
        if beat_id in seen:
            raise StateError(f"duplicate anchor beat id: {beat_id}")
        seen.add(beat_id)
        normalized.append({"id": beat_id, "description": description.strip()})
    path = data_dir(root) / "project.json"
    project = read_json(path)
    current = project.get("story_contract") or default_story_contract()
    version = int(current.get("version", 0)) + 1
    project["story_contract"] = {
        "status": "LOCKED",
        "version": version,
        "anchor_beats": normalized,
        "locked_by": actor,
        "locked_at": utc_now(),
    }
    project["updated_at"] = utc_now()
    atomic_write_json(path, project)
    append_history(root, "story_contract_locked", actor, "project", "PROJECT_001", {"version": version, "anchor_ids": sorted(seen)})
    sync_dashboard(root)


def record_boundary_analysis(
    root: str | Path,
    shot_id: str,
    frame_path: str,
    observations: dict[str, Any],
    technical: dict[str, Any],
    next_story_adjustment: str,
    actor: str,
) -> None:
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    if shot.get("generation", {}).get("status") not in {"GENERATED", "FINAL_COMPLETE"}:
        raise StateError("boundary analysis requires an accepted generated shot")
    if shot.get("qc", {}).get("user_review") != "PASSED":
        raise StateError("boundary analysis requires explicit user acceptance")
    if not frame_path:
        raise StateError("boundary analysis requires the selected frame path")
    resolved_frame = Path(frame_path).expanduser()
    if not resolved_frame.is_absolute():
        resolved_frame = _root(root) / resolved_frame
    if not resolved_frame.is_file():
        raise StateError(f"boundary analysis frame does not exist: {resolved_frame}")
    missing = [key for key in BOUNDARY_OBSERVATION_FIELDS if not isinstance(observations.get(key), str) or not observations[key].strip()]
    if missing:
        raise StateError("boundary analysis observations missing: " + ", ".join(missing))
    selection_method = technical.get("selection_method")
    if selection_method not in {"lowest_ffmpeg_blurdetect_mean", "director_selected_candidate"}:
        raise StateError("boundary analysis has an unsupported selection method")
    try:
        window_seconds = float(technical.get("window_seconds", 0) or 0)
        selected_timestamp = float(technical["selected_timestamp"])
        selected_blur_score = float(technical["selected_blur_score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise StateError("boundary analysis has invalid timestamp or blur-score evidence") from exc
    if window_seconds != 0.5:
        raise StateError("boundary analysis must cover the final 0.5 seconds")
    candidates = technical.get("candidates")
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise StateError("boundary analysis requires the scored candidate ledger")
    scored_candidates: list[tuple[float, float, str | None]] = []
    try:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise TypeError
            candidate_path = candidate.get("path")
            if candidate_path is not None and not isinstance(candidate_path, str):
                raise TypeError
            scored_candidates.append((float(candidate["timestamp"]), float(candidate["blur_score"]), candidate_path))
    except (KeyError, TypeError, ValueError) as exc:
        raise StateError("boundary analysis candidate ledger is invalid") from exc
    selected_matches = [
        item for item in scored_candidates
        if item[0] == selected_timestamp and item[1] == selected_blur_score
    ]
    if len(selected_matches) != 1:
        raise StateError("boundary analysis selection is absent from the candidate ledger")
    selection_reason = technical.get("selection_reason")
    if selection_method == "lowest_ffmpeg_blurdetect_mean":
        expected_timestamp, expected_score, _ = min(scored_candidates, key=lambda item: (item[1], -item[0]))
        if selected_timestamp != expected_timestamp or selected_blur_score != expected_score:
            raise StateError("boundary analysis selection does not match the lowest-blur candidate")
    elif not isinstance(selection_reason, str) or not selection_reason.strip():
        raise StateError("director-selected boundary requires selection_reason")
    selected_candidate_path = technical.get("selected_candidate_path") or selected_matches[0][2]
    if selection_method == "director_selected_candidate":
        if not isinstance(selected_candidate_path, str) or not selected_candidate_path:
            raise StateError("director-selected boundary requires a persisted selected_candidate_path")
        selected_candidate = Path(selected_candidate_path).expanduser()
        selected_frame = Path(frame_path).expanduser()
        if not selected_candidate.is_absolute():
            selected_candidate = _root(root) / selected_candidate
        if not selected_frame.is_absolute():
            selected_frame = _root(root) / selected_frame
        if selected_candidate.resolve() != selected_frame.resolve():
            raise StateError("director-selected frame_path must match selected_candidate_path")
    if not isinstance(next_story_adjustment, str) or not next_story_adjustment.strip():
        raise StateError("boundary analysis requires a next-story adjustment")
    analysis_id = f"BA_{shot_id}_V{shot.get('generation', {}).get('version', 1)}"
    shot["boundary_analysis"] = {
        "status": "COMPLETE",
        "analysis_id": analysis_id,
        "frame_path": frame_path,
        "observations": {key: observations[key].strip() for key in BOUNDARY_OBSERVATION_FIELDS},
        "technical": {
            "selection_method": technical["selection_method"],
            "window_seconds": 0.5,
            "selected_timestamp": selected_timestamp,
            "selected_blur_score": selected_blur_score,
            "selected_candidate_path": selected_candidate_path,
            "selection_reason": selection_reason.strip() if isinstance(selection_reason, str) else None,
            "candidates": deepcopy(candidates),
        },
        "next_story_adjustment": next_story_adjustment.strip(),
        "analyzed_by": actor,
        "analyzed_at": utc_now(),
    }
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "boundary_analysis_recorded", actor, "shot", shot_id, {"analysis_id": analysis_id, "frame_path": frame_path})
    sync_dashboard(root)


def record_start_frame_qc(
    root: str | Path,
    shot_id: str,
    rendered_first_frame_path: str,
    status: str,
    actor: str,
    notes: str = "",
    comparison: dict[str, Any] | None = None,
) -> None:
    if status not in {"PASSED", "FAILED"}:
        raise StateError("start-frame QC status must be PASSED or FAILED")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    if shot.get("generation", {}).get("status") not in {"GENERATED", "FINAL_COMPLETE"}:
        raise StateError("start-frame QC requires a generated shot")
    submitted = (shot.get("references") or {}).get("start")
    if not submitted or not rendered_first_frame_path:
        raise StateError("start-frame QC requires submitted and rendered first-frame paths")
    resolved_rendered = Path(rendered_first_frame_path).expanduser()
    if not resolved_rendered.is_absolute():
        resolved_rendered = _root(root) / resolved_rendered
    if not resolved_rendered.is_file():
        raise StateError(f"rendered first frame does not exist: {resolved_rendered}")
    if comparison is not None and not isinstance(comparison, dict):
        raise StateError("start-frame comparison must be a JSON object")
    shot["start_frame_qc"] = {
        "status": status,
        "submitted_start_path": submitted,
        "rendered_first_frame_path": rendered_first_frame_path,
        "reviewed_by": actor,
        "reviewed_at": utc_now(),
        "notes": notes,
        "comparison": deepcopy(comparison),
    }
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "start_frame_qc_recorded", actor, "shot", shot_id, {"status": status})
    sync_dashboard(root)


def record_start_image_review(
    root: str | Path,
    shot_id: str,
    assessment: dict[str, Any],
    status: str,
    actor: str,
    notes: str = "",
) -> None:
    if status not in {"PASSED", "FAILED"}:
        raise StateError("start-image review status must be PASSED or FAILED")
    if not isinstance(assessment, dict):
        raise StateError("start-image assessment must be a JSON object")
    missing = [key for key in START_IMAGE_REVIEW_FIELDS if not isinstance(assessment.get(key), bool)]
    if missing:
        raise StateError("start-image assessment missing boolean fields: " + ", ".join(missing))
    risk = assessment.get("off_frame_reveal_risk")
    if risk not in OFF_FRAME_REVEAL_RISKS:
        raise StateError("start-image assessment has invalid off_frame_reveal_risk")
    if status == "PASSED" and not all(assessment[key] for key in START_IMAGE_REVIEW_FIELDS):
        raise StateError("start-image review cannot pass while a required preparation check is false")
    if status == "PASSED" and risk == "HIGH" and not notes.strip():
        raise StateError("high off-frame reveal risk requires review notes")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    if not (shot.get("references") or {}).get("start"):
        raise StateError("start-image review requires references.start")
    shot["start_image_review"] = {
        "status": status,
        "start_image_path": (shot.get("references") or {}).get("start"),
        "assessment": {**{key: assessment[key] for key in START_IMAGE_REVIEW_FIELDS}, "off_frame_reveal_risk": risk},
        "notes": notes,
        "reviewed_by": actor,
        "reviewed_at": utc_now(),
    }
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(root, "start_image_review_recorded", actor, "shot", shot_id, {"status": status, "risk": risk})
    sync_dashboard(root)


def set_adaptive_story(
    root: str | Path,
    shot_id: str,
    anchor_beat_ids: list[str],
    adjustment_reason: str,
    dialogue_impact: str,
    actor: str,
    previous_shot_id: str | None = None,
) -> None:
    state = load_all(root)
    contract = state["project"].get("story_contract") or {}
    if contract.get("status") != "LOCKED":
        raise StateError("story anchor beats must be user-locked before adaptive planning")
    valid_ids = {item.get("id") for item in contract.get("anchor_beats", [])}
    if not isinstance(anchor_beat_ids, list) or not all(isinstance(item, str) for item in anchor_beat_ids):
        raise StateError("anchor_beat_ids must be a JSON array of strings")
    unknown = sorted(set(anchor_beat_ids) - valid_ids)
    if unknown:
        raise StateError("unknown story anchor beats: " + ", ".join(unknown))
    if dialogue_impact not in DIALOGUE_IMPACTS:
        raise StateError("invalid dialogue impact")
    if not adjustment_reason.strip():
        raise StateError("adaptive story requires an adjustment reason")
    shot = _find(state["shots"].get("items", []), shot_id, "shot")
    analysis_id = None
    if previous_shot_id:
        previous = _find(state["shots"].get("items", []), previous_shot_id, "previous shot")
        if previous.get("generation", {}).get("status") not in {"GENERATED", "FINAL_COMPLETE"}:
            raise StateError("adaptive story requires the previous generated shot")
        if previous.get("qc", {}).get("user_review") != "PASSED":
            raise StateError("adaptive story requires previous user acceptance")
        if (shot.get("boundary") or {}).get("inherit_previous_last_frame") is True:
            if (previous.get("start_frame_qc") or {}).get("status") != "PASSED":
                raise StateError("inherited adaptation requires previous start-frame QC")
            analysis = previous.get("boundary_analysis") or {}
            if analysis.get("status") != "COMPLETE":
                raise StateError("inherited adaptation requires the previous boundary analysis")
            analysis_id = analysis.get("analysis_id")
    audio = shot.get("audio") or {}
    master_hash = (
        audio.get("dialogue_reference_sha256")
        if audio.get("route") == "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO"
        else audio.get("narration_master_sha256") if audio.get("route") == "OFFSCREEN_NARRATION" else None
    )
    if audio.get("route") in {"VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO", "OFFSCREEN_NARRATION"}:
        if dialogue_impact not in {"UNCHANGED", "RERECORDED"}:
            raise StateError("recorded-speech adaptation must declare UNCHANGED or RERECORDED")
        if not isinstance(master_hash, str) or not SHA256_RE.fullmatch(master_hash):
            raise StateError("recorded-speech adaptation requires a locked master SHA-256")
    elif dialogue_impact != "NOT_APPLICABLE":
        raise StateError("shots without visible dialogue must use dialogue_impact=NOT_APPLICABLE")
    current_revision = int((shot.get("story") or {}).get("adaptive_revision", 0))
    update_shot(
        root,
        shot_id,
        {
            "story": {
                "anchor_beat_ids": list(dict.fromkeys(anchor_beat_ids)),
                "story_contract_version": contract.get("version"),
                "adaptive_revision": current_revision + 1,
                "based_on_previous_shot_id": previous_shot_id,
                "based_on_boundary_analysis_id": analysis_id,
                "adjustment_reason": adjustment_reason.strip(),
                "dialogue_impact": dialogue_impact,
                "dialogue_reference_sha256": master_hash,
                "recorded_audio_sha256": master_hash,
            }
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


def _active_attempt(shot: dict[str, Any]) -> dict[str, Any] | None:
    attempt_id = (shot.get("generation") or {}).get("active_attempt_id")
    if not attempt_id:
        return None
    return next(
        (
            item
            for item in (shot.get("generation") or {}).get("attempts", [])
            if item.get("attempt_id") == attempt_id
        ),
        None,
    )


def unresolved_submission(shot: dict[str, Any]) -> bool:
    attempt = _active_attempt(shot)
    return bool(attempt and attempt.get("resolution") == "PENDING")


def active_submission_attempt(root: str | Path, shot_id: str) -> dict[str, Any] | None:
    shots = read_json(data_dir(root) / "shots.json")
    shot = _find(shots.get("items", []), shot_id, "shot")
    attempt = _active_attempt(shot)
    return deepcopy(attempt) if attempt is not None else None


def start_submission_attempt(
    root: str | Path,
    shot_id: str,
    actor: str,
    *,
    provider: str,
    mode: str,
    execution_fingerprint: str,
    match_signature: dict[str, Any],
    account_credits_before: float | None,
    cost_uncertainty_acknowledged: bool = False,
) -> str:
    state = load_all(root)
    shot = _find(state["shots"].get("items", []), shot_id, "shot")
    if shot.get("generation", {}).get("status") != "READY":
        raise StateError("shot generation status must be READY")
    gates = shot_gate_errors(state, shot)
    if gates:
        raise StateError("generation gate failed: " + "; ".join(gates))
    if unresolved_submission(shot):
        raise StateError("an unresolved provider submission must be reconciled before a new attempt")
    generation = shot["generation"]
    attempts = generation.setdefault("attempts", [])
    attempt_id = f"ATTEMPT_{len(attempts) + 1:03d}"
    attempt = {
        "attempt_id": attempt_id,
        "generation_version": generation.get("version", 1),
        "execution_fingerprint": execution_fingerprint,
        "provider": provider,
        "mode": mode,
        "match_signature": deepcopy(match_signature),
        "started_at": utc_now(),
        "submitted_at": None,
        "last_checked_at": None,
        "resolved_at": None,
        "job_id": None,
        "remote_status": "UNKNOWN",
        "raw_remote_status": None,
        "resolution": "PENDING",
        "ambiguity_reason": None,
        "account_credits_before": account_credits_before,
        "account_credits_after": None,
        "cost_uncertainty_acknowledged": bool(cost_uncertainty_acknowledged),
        "result_available": False,
        "review": None,
    }
    attempts.append(attempt)
    generation.update(
        {
            "status": "SUBMITTING",
            "active_attempt_id": attempt_id,
            "job_id": None,
            "result_path": None,
        }
    )
    shot["updated_at"] = utc_now()
    state["shots"]["updated_at"] = utc_now()
    atomic_write_json(data_dir(root) / "shots.json", state["shots"])
    append_history(
        root,
        "submission_attempt_started",
        actor,
        "shot",
        shot_id,
        {
            "attempt_id": attempt_id,
            "provider": provider,
            "execution_fingerprint": execution_fingerprint,
            "cost_uncertainty_acknowledged": bool(cost_uncertainty_acknowledged),
        },
    )
    sync_dashboard(root)
    return attempt_id


def mark_submission_ambiguous(
    root: str | Path,
    shot_id: str,
    actor: str,
    reason: str,
) -> None:
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    attempt = _active_attempt(shot)
    if attempt is None:
        raise StateError("shot has no active submission attempt")
    attempt.update(
        {
            "remote_status": "UNKNOWN",
            "last_checked_at": utc_now(),
            "ambiguity_reason": reason,
            "resolution": "PENDING",
        }
    )
    shot["generation"]["status"] = "SUBMISSION_AMBIGUOUS"
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(
        root,
        "submission_became_ambiguous",
        actor,
        "shot",
        shot_id,
        {"attempt_id": attempt.get("attempt_id"), "reason": reason},
    )
    sync_dashboard(root)


def record_job(
    root: str | Path,
    shot_id: str,
    job_id: str,
    result_path: str | None,
    actor: str,
) -> None:
    if not isinstance(job_id, str) or not job_id.strip():
        raise StateError("job_id must be a non-empty string")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    for other in shots.get("items", []):
        if other.get("id") == shot_id:
            continue
        other_generation = other.get("generation") or {}
        other_job_ids = {other_generation.get("job_id")} | {
            item.get("job_id")
            for item in other_generation.get("attempts", [])
            if isinstance(item, dict)
        }
        if job_id in other_job_ids:
            raise StateError(f"provider job id is already bound to shot {other.get('id')}")
    generation = shot["generation"]
    existing = generation.get("job_id")
    if existing and existing != job_id:
        raise StateError(f"shot is already bound to a different provider job id: {existing}")
    attempt = _active_attempt(shot)
    if attempt is None:
        attempts = generation.setdefault("attempts", [])
        attempt_id = f"ATTEMPT_{len(attempts) + 1:03d}"
        attempt = {
            "attempt_id": attempt_id,
            "generation_version": generation.get("version", 1),
            "execution_fingerprint": (generation.get("execution") or {}).get("fingerprint"),
            "provider": generation.get("model"),
            "mode": (generation.get("execution") or {}).get("mode"),
            "match_signature": None,
            "started_at": utc_now(),
            "submitted_at": utc_now(),
            "last_checked_at": None,
            "resolved_at": None,
            "job_id": job_id,
            "remote_status": "SUBMITTED",
            "raw_remote_status": None,
            "resolution": "PENDING",
            "ambiguity_reason": None,
            "account_credits_before": None,
            "account_credits_after": None,
            "cost_uncertainty_acknowledged": False,
            "result_available": False,
        }
        attempts.append(attempt)
        generation["active_attempt_id"] = attempt_id
    elif attempt.get("job_id") not in {None, job_id}:
        raise StateError("active attempt is already bound to a different provider job id")
    attempt.update(
        {
            "job_id": job_id,
            "submitted_at": attempt.get("submitted_at") or utc_now(),
            "remote_status": "SUBMITTED" if attempt.get("remote_status") == "UNKNOWN" else attempt.get("remote_status"),
            "ambiguity_reason": None,
        }
    )
    generation.update({"job_id": job_id, "result_path": result_path})
    if generation.get("status") in {"SUBMITTING", "SUBMISSION_AMBIGUOUS", "FAILED", "READY"}:
        generation["status"] = "SUBMITTED"
    shot["updated_at"] = utc_now()
    shots["updated_at"] = utc_now()
    atomic_write_json(path, shots)
    append_history(
        root,
        "job_recorded",
        actor,
        "shot",
        shot_id,
        {"job_id": job_id, "attempt_id": attempt.get("attempt_id")},
    )
    sync_dashboard(root)


def record_provider_observation(
    root: str | Path,
    shot_id: str,
    normalized_status: str,
    actor: str,
    *,
    raw_status: str | None,
    result_available: bool,
    account_credits_after: float | None = None,
) -> None:
    allowed = {"SUBMITTED", "QUEUED", "RUNNING", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED", "FAILED"}
    if normalized_status not in allowed:
        raise StateError(f"invalid provider observation status: {normalized_status}")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    attempt = _active_attempt(shot)
    if attempt is None or not attempt.get("job_id"):
        raise StateError("provider observation requires an active attempt with a job id")
    now = utc_now()
    attempt.update(
        {
            "remote_status": normalized_status.removeprefix("PROVIDER_"),
            "raw_remote_status": raw_status,
            "last_checked_at": now,
            "account_credits_after": account_credits_after,
            "result_available": bool(result_available),
        }
    )
    generation = shot["generation"]
    if normalized_status == "FAILED":
        attempt.update({"resolution": "REMOTE_FAILED", "resolved_at": now})
        generation["active_attempt_id"] = None
        generation["status"] = "FAILED"
        generation["retry_count"] = int(generation.get("retry_count", 0)) + 1
    elif generation.get("status") not in {"GENERATED", "FINAL_COMPLETE"}:
        generation["status"] = normalized_status
    shot["updated_at"] = now
    shots["updated_at"] = now
    atomic_write_json(path, shots)
    append_history(
        root,
        "provider_observation_recorded",
        actor,
        "shot",
        shot_id,
        {
            "attempt_id": attempt.get("attempt_id"),
            "job_id": attempt.get("job_id"),
            "status": normalized_status,
            "raw_status": raw_status,
            "result_available": bool(result_available),
        },
    )
    sync_dashboard(root)


def finalize_provider_completion(root: str | Path, shot_id: str, actor: str) -> None:
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    attempt = _active_attempt(shot)
    if attempt is None or attempt.get("remote_status") != "COMPLETED" or not attempt.get("job_id"):
        raise StateError("provider completion evidence is required before local generation completion")
    now = utc_now()
    attempt.update({"resolution": "RECORDED", "resolved_at": now})
    shot["generation"].update(
        {
            "status": "GENERATED",
            "active_attempt_id": None,
            "job_id": attempt.get("job_id"),
        }
    )
    shot["updated_at"] = now
    shots["updated_at"] = now
    atomic_write_json(path, shots)
    append_history(
        root,
        "provider_completion_finalized",
        actor,
        "shot",
        shot_id,
        {"attempt_id": attempt.get("attempt_id"), "job_id": attempt.get("job_id")},
    )
    sync_dashboard(root)


def resolve_submission_ambiguity(
    root: str | Path,
    shot_id: str,
    resolution: str,
    actor: str,
    reason: str,
) -> None:
    if resolution not in {"NOT_SUBMITTED", "ABANDONED_RISK_ACCEPTED"}:
        raise StateError("ambiguity resolution must be NOT_SUBMITTED or ABANDONED_RISK_ACCEPTED")
    if resolution == "ABANDONED_RISK_ACCEPTED" and actor != "user":
        raise StateError("only the user may accept the duplicate-submission risk")
    if not reason.strip():
        raise StateError("ambiguity resolution requires a reason")
    path = data_dir(root) / "shots.json"
    shots = read_json(path)
    shot = _find(shots.get("items", []), shot_id, "shot")
    attempt = _active_attempt(shot)
    if attempt is None or attempt.get("resolution") != "PENDING":
        raise StateError("shot has no unresolved submission attempt")
    if attempt.get("job_id"):
        raise StateError("a known provider job must be reconciled, not abandoned as unknown")
    now = utc_now()
    attempt.update(
        {
            "resolution": resolution,
            "resolved_at": now,
            "ambiguity_reason": reason,
        }
    )
    generation = shot["generation"]
    generation["active_attempt_id"] = None
    generation["status"] = "FAILED"
    generation["retry_count"] = int(generation.get("retry_count", 0)) + 1
    shot["updated_at"] = now
    shots["updated_at"] = now
    atomic_write_json(path, shots)
    append_history(
        root,
        "submission_ambiguity_resolved",
        actor,
        "shot",
        shot_id,
        {"attempt_id": attempt.get("attempt_id"), "resolution": resolution, "reason": reason},
    )
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
    existing = next(
        (item for item in transactions if job_id and item.get("job_id") == job_id),
        None,
    )
    if existing is not None and (
        existing.get("entity_id") != entity_id or float(existing.get("credits", 0)) != float(credits)
    ):
        raise StateError("provider job already has a conflicting actual-cost transaction")
    projected = round(
        sum(float(item.get("credits", 0)) for item in transactions)
        + (0.0 if existing is not None else float(credits)),
        6,
    )
    project = read_json(data_dir(root) / "project.json")
    ceiling = project.get("cost_approval", {}).get("max_credits")
    if existing is None:
        transactions.append(transaction)
    actual["credits"] = projected
    actual["ceiling_breach"] = ceiling is not None and projected > float(ceiling)
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
    if existing is None:
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
    if plan.get("end_keyframe_role", "none") not in {"end_image", "none"}:
        return ["end keyframe role is invalid"]
    errors: list[str] = []
    if not plan.get("reason"):
        errors.append("boundary director reason is missing")
    if role == "image_reference":
        errors.append("planned keyframe must not ride the video call as an undocumented image_reference")
    references = shot.get("references") or {}
    inherit = plan.get("inherit_previous_last_frame")
    if strategy == "continuous_match" or (strategy == "motivated_transition" and inherit is True):
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
        errors.append("non-continuous boundary must explicitly avoid previous-frame inheritance")
    if strategy == "motivated_transition":
        end_keyframe = plan.get("end_keyframe")
        end_role = plan.get("end_keyframe_role")
        if end_keyframe:
            if end_role != "end_image" or references.get("end") != end_keyframe:
                errors.append("motivated transition end keyframe is not transported as end_image")
        elif end_role != "none" or references.get("end"):
            errors.append("prompt-only motivated transition must not carry an end keyframe")
        if inherit is False and (
            not plan.get("planned_keyframe") or references.get("start") != plan.get("planned_keyframe")
        ):
            errors.append("non-inherited motivated transition requires its composed keyframe as start_image")
    if strategy in {"editorial_cut", "scene_reset"}:
        if not plan.get("planned_keyframe") or references.get("start") != plan.get("planned_keyframe"):
            errors.append("cut/reset requires its composed planned keyframe as the start_image")
    return errors


def start_image_policy_errors(shot: dict[str, Any]) -> list[str]:
    """Enforce the adaptive, minimum-sufficient Seedance image transport."""
    references = shot.get("references") or {}
    strategy = (shot.get("boundary") or {}).get("strategy")
    errors: list[str] = []
    if not references.get("start"):
        errors.append("video execution requires exactly one start image")
    plan = shot.get("seedance_plan") or {}
    policy = plan.get("image_input_policy")
    errors.extend(cinematography.validate_image_input_policy(policy))
    policy_fields = policy if isinstance(policy, dict) else {}
    mode = policy_fields.get("mode")
    images = references.get("images") or []
    end = references.get("end")
    if mode == "start_only":
        if images:
            errors.append("start_only must not carry image_references")
        if end:
            errors.append("start_only must not carry end_image")
    elif mode == "start_plus_essential_reference":
        if len(images) != 1:
            errors.append("start_plus_essential_reference requires exactly one image_reference")
        if end:
            errors.append("essential-reference escalation must not also carry end_image")
        manifest = references.get("manifest") or []
        matching = [
            item for item in manifest
            if isinstance(item, dict)
            and item.get("transport_field") == "image_references"
            and item.get("source") in images
        ]
        if len(matching) != 1:
            errors.append("essential image_reference requires one matching manifest entry")
        elif matching[0].get("semantic_role") != policy_fields.get("essential_reference_role"):
            errors.append("essential image_reference role does not match image_input_policy")
    elif mode == "start_end_transition":
        if images:
            errors.append("start_end_transition must not also carry image_references")
        if not end:
            errors.append("start_end_transition requires end_image")
        if strategy != "motivated_transition":
            errors.append("start_end_transition requires a motivated transition")
    if end and strategy != "motivated_transition":
        errors.append("end image is allowed only for a motivated transition")
    execution = shot.get("generation", {}).get("execution") or {}
    argv = execution.get("argv") or []
    if isinstance(argv, list) and argv:
        _, flags = execution_contract.parse_flags(argv)
        if flags.get("image_references") != images and (flags.get("image_references") or images):
            errors.append("execution image_references must match the approved adaptive input policy")
        if references.get("start") and flags.get("start_image") != references.get("start"):
            errors.append("execution start_image must match references.start")
        if flags.get("end_image") != end and (flags.get("end_image") or end):
            errors.append("execution end_image must match the approved adaptive input policy")
    return errors


def start_image_review_errors(shot: dict[str, Any]) -> list[str]:
    review = shot.get("start_image_review") or {}
    status = review.get("status")
    generation_status = (shot.get("generation") or {}).get("status")
    if status == "NOT_APPLICABLE" and generation_status in {"GENERATED", "FINAL_COMPLETE"}:
        return []
    if status != "PASSED":
        return ["start image has not passed the required preparation review"]
    if review.get("start_image_path") != (shot.get("references") or {}).get("start"):
        return ["start image preparation review does not match the current references.start"]
    assessment = review.get("assessment") or {}
    missing = [key for key in START_IMAGE_REVIEW_FIELDS if assessment.get(key) is not True]
    errors = ["start image preparation check failed: " + ", ".join(missing)] if missing else []
    if assessment.get("off_frame_reveal_risk") not in OFF_FRAME_REVEAL_RISKS:
        errors.append("start image review lacks off-frame reveal risk")
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
    if route in {"NO_DIALOGUE_POST", "OFFSCREEN_NARRATION", "INTENTIONAL_SILENCE"}:
        if audio.get("generated_track_policy") != "NOT_GENERATED":
            errors.append("routes without native audio must use generated_track_policy=NOT_GENERATED")
    if route == "INTENTIONAL_SILENCE" and audio_mode != "none":
        errors.append("intentional silence must use audio_mode=none")
    if route == "OFFSCREEN_NARRATION" and audio.get("has_visible_dialogue") is not False:
        errors.append("off-screen narration must declare has_visible_dialogue=false")
    if route == "OFFSCREEN_NARRATION":
        if not audio.get("narration_master_path"):
            errors.append("off-screen narration is missing its locked narration master")
        narration_hash = audio.get("narration_master_sha256")
        if not isinstance(narration_hash, str) or not SHA256_RE.fullmatch(narration_hash):
            errors.append("off-screen narration master must be locked with a SHA-256 fingerprint")
        if audio.get("final_mix_required") is not True:
            errors.append("off-screen narration must require a final external mix")
    if route == "NO_DIALOGUE_POST" and audio.get("final_mix_required") is not True:
        errors.append("no-dialogue post route must require a final external mix")
    if route == "NO_DIALOGUE_NATIVE_SOUND":
        if audio.get("has_visible_dialogue") is not False:
            errors.append("no-dialogue native-sound route must declare has_visible_dialogue=false")
        if audio_mode != "native_sfx":
            errors.append("no-dialogue native-sound route must use audio_mode=native_sfx")
        if (shot.get("references") or {}).get("audios"):
            errors.append("no-dialogue native-sound route must not carry audio_references")
        if audio.get("generated_track_policy") != "PRESERVE":
            errors.append("no-dialogue native-sound route must preserve the Seedance native track")
        if audio.get("final_mix_required") is not False:
            errors.append("no-dialogue native-sound route must not require a creative external mix")
        errors.extend(
            "no-dialogue native sound " + message
            for message in cinematography.validate_sound_design(
                (shot.get("seedance_plan") or {}).get("sound_design"), require_complete=True
            )
        )
        if not cinematography.is_no_dialogue_brief(
            ((shot.get("seedance_plan") or {}).get("sound_design") or {}).get("dialogue")
        ):
            errors.append(
                "no-dialogue native sound requires sound_design.dialogue to explicitly say none or no dialogue"
            )
    if route == "INTENTIONAL_SILENCE" and audio.get("final_mix_required") is not False:
        errors.append("intentional silence must not require a final external mix")
    if route == "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO":
        if audio_mode != "audio_reference":
            errors.append("visible dialogue must use the locked ElevenLabs reference as audio_reference")
        if audio.get("voice_provider") != "elevenlabs" or audio.get("voice_model") != "eleven_v3":
            errors.append("visible dialogue must lock voice_provider=elevenlabs and voice_model=eleven_v3")
        reference = audio.get("dialogue_reference_path")
        if not reference:
            errors.append("visible dialogue is missing the locked dialogue reference")
        elif reference not in (shot.get("references") or {}).get("audios", []):
            errors.append("dialogue reference must be present in audio_references")
        reference_hash = audio.get("dialogue_reference_sha256")
        if not isinstance(reference_hash, str) or not SHA256_RE.fullmatch(reference_hash):
            errors.append("visible dialogue reference must be locked with a SHA-256 fingerprint")
        if audio.get("generated_track_policy") != "PRESERVE":
            errors.append("visible dialogue must preserve the Seedance-rendered native audio track")
        if audio.get("final_mix_required") is not False:
            errors.append("visible dialogue must not require a creative external audio mix")
        errors.extend(
            "visible dialogue " + message
            for message in cinematography.validate_sound_design(
                (shot.get("seedance_plan") or {}).get("sound_design"), require_complete=True
            )
        )
    return errors


def ordered_shots(state: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    scene_order = {
        item.get("id"): (item.get("order", 0), item.get("id", ""))
        for item in state["scenes"].get("items", [])
    }
    return sorted(
        state["shots"].get("items", []),
        key=lambda item: (*scene_order.get(item.get("scene_id"), (0, item.get("scene_id", ""))), item.get("order", 0), item.get("id", "")),
    )


def story_contract_errors(state: dict[str, dict[str, Any]], shot: dict[str, Any]) -> list[str]:
    contract = state["project"].get("story_contract") or {}
    if contract.get("status") != "LOCKED":
        return ["story anchor beats are not user-locked"]
    errors: list[str] = []
    story = shot.get("story") or {}
    valid_ids = {item.get("id") for item in contract.get("anchor_beats", [])}
    unknown = sorted(set(story.get("anchor_beat_ids") or []) - valid_ids)
    if unknown:
        errors.append("shot references unknown anchor beats: " + ", ".join(unknown))
    if story.get("story_contract_version") != contract.get("version"):
        errors.append("shot adaptive plan does not use the current locked story contract")
    if not story.get("adjustment_reason"):
        errors.append("shot adaptive plan has no adjustment reason")
    audio = shot.get("audio") or {}
    if audio.get("route") in {"VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO", "OFFSCREEN_NARRATION"}:
        expected_hash = (
            audio.get("dialogue_reference_sha256")
            if audio.get("route") == "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO"
            else audio.get("narration_master_sha256")
        )
        if story.get("recorded_audio_sha256") != expected_hash:
            errors.append("adaptive plan does not preserve the locked recorded-audio fingerprint")
        if story.get("dialogue_impact") not in {"UNCHANGED", "RERECORDED"}:
            errors.append("adaptive plan must declare recorded-speech impact")
    return errors


def sequential_adaptation_errors(state: dict[str, dict[str, Any]], shot: dict[str, Any]) -> list[str]:
    sequence = ordered_shots(state)
    index = next((offset for offset, item in enumerate(sequence) if item.get("id") == shot.get("id")), None)
    if index is None:
        return ["shot is absent from the ordered production sequence"]
    story = shot.get("story") or {}
    provenance = (shot.get("boundary") or {}).get("start_image_provenance") or {}
    if index == 0:
        errors: list[str] = []
        if story.get("based_on_previous_shot_id") is not None:
            errors.append("first shot adaptive plan must not depend on a previous shot")
        if provenance.get("mode") != "initial_composition":
            errors.append("first shot must use the sole initial composed start image")
        if not provenance.get("created_at"):
            errors.append("first shot start image has no composition timestamp")
        return errors
    previous = sequence[index - 1]
    previous_id = previous.get("id")
    errors = []
    if previous.get("generation", {}).get("status") not in {"GENERATED", "FINAL_COMPLETE"}:
        errors.append("previous sequential shot has not been generated and accepted")
    if previous.get("qc", {}).get("user_review") != "PASSED":
        errors.append("previous sequential shot lacks user acceptance")
    previous_analysis = previous.get("boundary_analysis") or {}
    if story.get("based_on_previous_shot_id") != previous_id:
        errors.append("adaptive plan is not based on the immediate previous shot")
    if provenance.get("created_after_shot_id") != previous_id:
        errors.append("next start image was not created or inherited just in time after the previous shot")
    if not provenance.get("created_at"):
        errors.append("next start image has no JIT provenance timestamp")
    boundary = shot.get("boundary") or {}
    strategy = boundary.get("strategy")
    if boundary.get("inherit_previous_last_frame") is True:
        if previous_analysis.get("status") != "COMPLETE":
            errors.append("inherited boundary lacks previous boundary analysis")
        if (previous.get("start_frame_qc") or {}).get("status") != "PASSED":
            errors.append("inherited boundary lacks passed previous start-frame QC")
        if story.get("based_on_boundary_analysis_id") != previous_analysis.get("analysis_id"):
            errors.append("inherited adaptive plan is not bound to the previous boundary analysis")
        if (shot.get("references") or {}).get("start") != previous_analysis.get("frame_path"):
            errors.append("chained start image must equal the accepted previous boundary analysis frame")
    elif strategy in {"motivated_transition", "editorial_cut", "scene_reset"} and provenance.get("mode") != "jit_composition":
        errors.append("cut/reset after the first shot must use a just-in-time composed start image")
    return errors


def shot_gate_errors(state: dict[str, dict[str, Any]], shot: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = state["project"]
    policy = project.get("production_policy") or default_production_policy()
    profile = policy.get("approval_profile", "FULL")
    if profile not in APPROVAL_PROFILES:
        errors.append("production approval profile is invalid")
        profile = "FULL"
    if project.get("cost_approval", {}).get("status") != "APPROVED":
        errors.append("cost ceiling is not approved")
    if profile == "FULL" and project.get("requirements_lock", {}).get("status") != "LOCKED":
        errors.append("requirements are not locked")
    if profile in {"TARGETED", "FULL"}:
        if shot.get("approval_status") != "LOCKED_FOR_VIDEO":
            errors.append("shot board is not locked for video")
        assets = {item.get("id"): item for item in state["assets"].get("items", [])}
        for asset_id in shot.get("required_asset_ids", []):
            if assets.get(asset_id, {}).get("status") != "LOCKED_FOR_VIDEO":
                errors.append(f"required asset is not locked: {asset_id}")
        errors.extend(boundary_plan_errors(shot))
    if profile == "FULL":
        continuity = shot.get("continuity", {})
        missing_context = [key for key, value in continuity.items() if not value]
        if missing_context:
            errors.append("continuity context missing: " + ", ".join(missing_context))
    errors.extend(start_image_policy_errors(shot))
    errors.extend(start_image_review_errors(shot))
    errors.extend(audio_plan_errors(shot))
    if profile == "FULL":
        errors.extend(story_contract_errors(state, shot))
        errors.extend(sequential_adaptation_errors(state, shot))
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
    if target == "READY" and unresolved_submission(shot):
        raise StateError("unresolved provider submission must be reconciled before retry")
    if target not in GENERATION_TRANSITIONS[current]:
        raise StateError(f"invalid generation transition: {current} -> {target}")
    if target == "SUBMITTING":
        gates = shot_gate_errors(state, shot)
        if gates:
            raise StateError("generation gate failed: " + "; ".join(gates))
        raise StateError("SUBMITTING may only be entered by the guarded paid runner")
    if target == "FAILED" and unresolved_submission(shot):
        raise StateError("an unresolved provider attempt must be reconciled or explicitly resolved, not marked failed")
    if target in {"SUBMITTED", "QUEUED", "RUNNING", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED"}:
        raise StateError(f"{target} may only be recorded through provider reconciliation")
    if target == "GENERATED":
        attempt = _active_attempt(shot)
        if attempt is None or attempt.get("remote_status") != "COMPLETED":
            raise StateError("GENERATED requires recorded provider completion evidence")
        attempt.update({"resolution": "RECORDED", "resolved_at": utc_now()})
        shot["generation"]["active_attempt_id"] = None
    if target == "FINAL_COMPLETE":
        if (shot.get("start_frame_qc") or {}).get("status") != "PASSED":
            raise StateError("final gate failed; start-frame QC is not passed")
        approval_profile = ((state["project"].get("production_policy") or {}).get("approval_profile") or "FULL")
        if approval_profile == "FULL" and (shot.get("boundary_analysis") or {}).get("status") != "COMPLETE":
            raise StateError("final gate failed; boundary analysis is incomplete")
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
    policy = state["project"].get("production_policy") or {}
    if policy.get("mode") not in PRODUCTION_MODES:
        errors.append("project: invalid production mode")
    if policy.get("approval_profile") not in APPROVAL_PROFILES:
        errors.append("project: invalid approval profile")
    if policy.get("mode") == "OFFICIAL_WORKFLOW" and policy.get("official_workflow") not in {"marketing_studio", "video_explainer"}:
        errors.append("project: official workflow route is incomplete")
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
        if shot.get("generation", {}).get("status") == "READY":
            errors.extend(f"shot {shot.get('id')}: {message}" for message in shot_gate_errors(state, shot))
        active_id = shot.get("generation", {}).get("active_attempt_id")
        attempts = shot.get("generation", {}).get("attempts")
        generation_status = shot.get("generation", {}).get("status")
        if not isinstance(attempts, list):
            errors.append(f"shot {shot.get('id')}: generation attempts must be an array")
        elif active_id and not any(item.get("attempt_id") == active_id for item in attempts if isinstance(item, dict)):
            errors.append(f"shot {shot.get('id')}: active generation attempt does not exist")
        if generation_status in {"SUBMITTING", "SUBMISSION_AMBIGUOUS"} and not active_id:
            errors.append(f"shot {shot.get('id')}: {generation_status} requires an active submission attempt")
        active_statuses = {
            "SUBMITTING", "SUBMISSION_AMBIGUOUS", "SUBMITTED", "QUEUED",
            "RUNNING", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED",
        }
        if active_id and generation_status not in active_statuses:
            errors.append(f"shot {shot.get('id')}: active submission attempt is inconsistent with {generation_status}")
        if generation_status in {"SUBMITTED", "QUEUED", "RUNNING", "REMOTE_UNKNOWN", "PROVIDER_COMPLETED"}:
            if not active_id:
                errors.append(f"shot {shot.get('id')}: {generation_status} requires an active submission attempt")
            if not shot.get("generation", {}).get("job_id"):
                errors.append(f"shot {shot.get('id')}: {generation_status} requires a provider job id")
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
    ceiling = approved.get("max_credits")
    expected_breach = ceiling is not None and actual > float(ceiling)
    if state["costs"].get("actual", {}).get("ceiling_breach") is not expected_breach:
        errors.append("actual credit ceiling-breach flag is inconsistent")
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
    policy = state["project"].get("production_policy") or default_production_policy()
    if policy.get("approval_profile") == "FULL" and state["project"].get("requirements_lock", {}).get("status") != "LOCKED":
        blockers.append("요구사항 승인 필요")
    if state["project"].get("cost_approval", {}).get("status") != "APPROVED":
        blockers.append("비용 상한 승인 필요")
    if state["costs"].get("actual", {}).get("reconciliation_required"):
        blockers.append("실제 크레딧 사용량 대사 필요 (새 제출은 명시적 위험 승인으로 계속 가능)")
    if state["costs"].get("actual", {}).get("ceiling_breach"):
        blockers.append("실제 사용량이 승인 상한을 초과함 (기록은 보존, 새 제출은 중지)")
    for shot in shots:
        generation = shot.get("generation", {})
        status = generation.get("status")
        if status == "SUBMISSION_AMBIGUOUS":
            blockers.append(f"{shot.get('id')}: 제출 결과 불명확 — provider history 대사 또는 사용자 위험 승인 필요")
        elif status == "SUBMITTING":
            blockers.append(f"{shot.get('id')}: 제출 도중 중단 가능성 — provider history 대사 필요")
        elif status == "REMOTE_UNKNOWN":
            blockers.append(f"{shot.get('id')}: 원격 잡 상태 관측 실패 — 같은 job ID로 재조회 필요")
    blockers.extend(
        f"{shot.get('id')}: {message}"
        for shot in shots
        if shot.get("generation", {}).get("status") == "READY"
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
