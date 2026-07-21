#!/usr/bin/env python3
"""Deterministic cinematography recommendation, validation, and provider compilation."""

from __future__ import annotations

import json
import hashlib
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parent.parent
REFERENCES = SKILL_ROOT / "references"
CATALOG_PATH = REFERENCES / "film-technique-catalog.json"
GENRE_PATH = REFERENCES / "genre-directing-presets.json"
SUPPORT_PATH = REFERENCES / "higgsfield-technique-support.json"

SUPPORT_LEVELS = {
    "native_structured",
    "native_reference",
    "prompt_soft",
    "web_only",
    "post_only",
    "unreliable",
    "unsupported",
}
REFERENCE_ROLES = {"character", "style", "motion", "audio", "start", "end", "product", "location", "prop"}
REQUIRED_GRAMMAR_FIELDS = (
    "dramatic_beat",
    "viewer_should_feel",
    "shot_size",
    "angle",
    "lens_family",
    "movement",
    "composition",
    "lighting",
    "blocking",
    "screen_direction",
    "duration_seconds",
    "transition_out",
    "why",
)
DEFAULTS = {
    "shot_size": "shot.ms",
    "angle": "angle.eye_level",
    "lens": "lens.normal",
    "focus": "focus.selective",
    "movement": "movement.static",
    "composition": "composition.rule_of_thirds",
    "lighting": "lighting.motivated",
    "temporal": "temporal.realtime",
    "editing": "editing.straight_cut",
    "blocking": "blocking.one_action",
    "continuity": "continuity.axis_180",
    "color": "color.naturalistic",
    "audio": "audio.perspective",
}
CATEGORY_FIELDS = {
    "shot_size": "shot_size",
    "angle": "angle",
    "lens": "lens_family",
    "focus": "focus_plan",
    "movement": "movement",
    "composition": "composition",
    "lighting": "lighting",
    "temporal": "temporal_plan",
    "editing": "transition_out",
}


class CinematographyError(RuntimeError):
    """Raised when the cinematography knowledge contract is invalid."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CinematographyError(f"cannot read cinematography data {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CinematographyError(f"cinematography data must be an object: {path}")
    return value


def load_knowledge() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    catalog = read_json(CATALOG_PATH)
    genres = read_json(GENRE_PATH)
    support = read_json(SUPPORT_PATH)
    errors = validate_knowledge(catalog, genres, support)
    if errors:
        raise CinematographyError("invalid cinematography knowledge:\n- " + "\n- ".join(errors))
    return catalog, genres, support


def technique_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in catalog.get("techniques", []) if isinstance(item, dict)}


def validate_knowledge(
    catalog: dict[str, Any], genres: dict[str, Any], support: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    techniques = catalog.get("techniques")
    if not isinstance(techniques, list) or not techniques:
        return ["catalog.techniques must be a non-empty array"]
    ids: list[str] = []
    categories = set(catalog.get("categories", {}))
    sources = set(catalog.get("sources", {}))
    for offset, item in enumerate(techniques):
        if not isinstance(item, dict):
            errors.append(f"technique[{offset}] must be an object")
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            errors.append(f"technique[{offset}] missing id")
            continue
        ids.append(identifier)
        if item.get("category") not in categories:
            errors.append(f"{identifier}: unknown category {item.get('category')}")
        for field in ("name_ko", "prompt", "plain_language"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{identifier}: missing {field}")
        for field in ("aliases", "intents", "effects", "avoid", "failures", "qc", "sources"):
            if not isinstance(item.get(field), list):
                errors.append(f"{identifier}: {field} must be an array")
        for source in item.get("sources", []):
            if source not in sources:
                errors.append(f"{identifier}: unknown source {source}")
    if len(ids) != len(set(ids)):
        errors.append("technique ids must be unique")
    known = set(ids)
    for item in techniques:
        if not isinstance(item, dict):
            continue
        for other in item.get("incompatible_with", []):
            if other not in known:
                errors.append(f"{item.get('id')}: unknown incompatible technique {other}")
    profiles = genres.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append("genre profiles must be a non-empty object")
    else:
        for name, profile in profiles.items():
            for field in ("prefer", "avoid"):
                for identifier in profile.get(field, []):
                    if identifier not in known:
                        errors.append(f"genre {name}: unknown {field} technique {identifier}")
    providers = support.get("providers")
    if not isinstance(providers, dict) or not providers:
        errors.append("support.providers must be a non-empty object")
    else:
        for provider, profile in providers.items():
            level = profile.get("default_support")
            if level not in SUPPORT_LEVELS:
                errors.append(f"provider {provider}: invalid default support {level}")
            for identifier, override in profile.get("technique_support", {}).items():
                if identifier not in known:
                    errors.append(f"provider {provider}: unknown technique {identifier}")
                if override not in SUPPORT_LEVELS:
                    errors.append(f"provider {provider}: invalid support {override}")
    return errors


def empty_grammar() -> dict[str, Any]:
    return {
        "status": "DRAFT",
        "recommendation_id": None,
        "dramatic_beat": None,
        "viewer_should_feel": [],
        "technique_ids": [],
        "shot_size": None,
        "angle": None,
        "camera_height": None,
        "roll": "level",
        "lens_family": None,
        "focal_length_hint_35mm": None,
        "camera_distance": None,
        "depth_of_field": None,
        "focus_plan": None,
        "movement": None,
        "movement_speed": None,
        "composition": [],
        "lighting": [],
        "color_grade": None,
        "social_plan": None,
        "audio_perspective": None,
        "vfx_plan": None,
        "temporal_plan": None,
        "blocking": None,
        "screen_direction": None,
        "axis_side": None,
        "duration_seconds": None,
        "transition_in": None,
        "transition_out": None,
        "intentional_break": False,
        "why": None,
        "provider_binding": {
            "provider": None,
            "support_level": None,
            "native_params": {},
            "compiled_prompt": None,
            "schema_verified_at": None,
            "schema_contract_hash": None,
        },
        "qc_plan": [],
        "evidence": [],
    }


def default_seedance_plan() -> dict[str, Any]:
    """Safe official-guide baseline: one short 720p shot with native audio off."""
    return {
        "mode": "controlled_single_shot",
        "shot_count": 1,
        "aspect_ratio": "auto",
        "resolution": "720p",
        "generation_mode": "std",
        "bitrate_mode": "standard",
        "audio_mode": "post_only",
        "prototype": True,
        "timed_beats": [],
        "camera_invariants": [],
        "experimental_approved": False,
    }


def merge_grammar(current: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise CinematographyError("shot_grammar must be an object")
    result = empty_grammar()
    if isinstance(current, dict):
        _deep_update(result, current)
    _deep_update(result, patch)
    errors, _ = validate_grammar(result, require_complete=False)
    if errors:
        raise CinematographyError("invalid shot_grammar:\n- " + "\n- ".join(errors))
    complete_errors, _ = validate_grammar(result, require_complete=True)
    result["status"] = "VALIDATED" if not complete_errors else "DRAFT"
    return result


def _deep_update(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_update(target[key], value)
        else:
            target[key] = deepcopy(value)


def _tokens(value: str) -> set[str]:
    return {part for part in re.findall(r"[0-9a-zA-Z가-힣]+", value.lower()) if len(part) > 1}


def _text_score(query: str, item: dict[str, Any]) -> float:
    haystacks = [
        item.get("name_ko", ""),
        item.get("plain_language", ""),
        *item.get("aliases", []),
        *item.get("intents", []),
        *item.get("effects", []),
    ]
    query_lower = query.lower()
    query_tokens = _tokens(query)
    score = 0.0
    for text in haystacks:
        lowered = str(text).lower()
        if lowered and lowered in query_lower:
            score += 4.0
        score += len(query_tokens & _tokens(lowered)) * 1.5
    return score


def support_level(provider: str | None, technique_id: str, support: dict[str, Any]) -> str:
    if not provider:
        return "prompt_soft"
    profile = support.get("providers", {}).get(provider)
    if not isinstance(profile, dict):
        return "unsupported"
    return profile.get("technique_support", {}).get(technique_id, profile.get("default_support", "unsupported"))


def _ranked_by_category(
    intent: str,
    genre: str,
    platform: str,
    subject_priority: str,
    stability: str,
    provider: str | None,
    catalog: dict[str, Any],
    genres: dict[str, Any],
    support: dict[str, Any],
) -> dict[str, list[tuple[float, dict[str, Any]]]]:
    query = " ".join((intent, genre, platform, subject_priority, stability))
    profile = genres.get("profiles", {}).get(genre, genres.get("profiles", {}).get("general", {}))
    preferred = set(profile.get("prefer", []))
    avoided = set(profile.get("avoid", []))
    platform_profile = genres.get("platform_profiles", {}).get(platform, {})
    preferred.update(platform_profile.get("prefer", []))
    avoided.update(platform_profile.get("avoid", []))
    ranked: dict[str, list[tuple[float, dict[str, Any]]]] = {}
    for item in catalog.get("techniques", []):
        score = _text_score(query, item)
        identifier = item["id"]
        if identifier in preferred:
            score += 4.0
        if identifier in avoided:
            score -= 5.0
        if subject_priority == "emotion" and identifier in {"shot.cu", "shot.mcu", "lens.short_telephoto", "movement.dolly_in"}:
            score += 4.0
        if subject_priority == "space" and identifier in {"shot.ews", "shot.ws", "lens.wide", "movement.crane"}:
            score += 4.0
        if subject_priority == "product" and identifier in {"shot.insert", "lens.macro", "movement.arc", "movement.slider"}:
            score += 4.0
        if subject_priority == "action" and identifier in {"shot.full", "movement.tracking", "movement.leading"}:
            score += 4.0
        if stability == "stable" and identifier in {"movement.static", "movement.gimbal", "movement.slider"}:
            score += 4.0
        if stability == "unstable" and identifier in {"movement.handheld", "angle.dutch", "movement.snorricam"}:
            score += 4.0
        level = support_level(provider, identifier, support)
        score += {
            "native_structured": 2.0,
            "native_reference": 1.5,
            "prompt_soft": 0.5,
            "web_only": -1.0,
            "post_only": -0.5,
            "unreliable": -2.0,
            "unsupported": -6.0,
        }[level]
        ranked.setdefault(item["category"], []).append((score, item))
    for items in ranked.values():
        items.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return ranked


def _pick(ranked: dict[str, list[tuple[float, dict[str, Any]]]], category: str, offset: int = 0) -> dict[str, Any]:
    candidates = ranked.get(category, [])
    if not candidates:
        raise CinematographyError(f"no techniques for category {category}")
    positive = [item for score, item in candidates if score > 0]
    if positive:
        return positive[min(offset, len(positive) - 1)]
    default_id = DEFAULTS.get(category)
    for _, item in candidates:
        if item["id"] == default_id:
            return item
    return candidates[0][1]


def recommend(
    intent: str,
    *,
    genre: str = "general",
    platform: str = "general",
    subject_priority: str = "balanced",
    stability: str = "balanced",
    provider: str | None = None,
    duration_seconds: float = 5.0,
    top_n: int = 3,
) -> dict[str, Any]:
    if not intent.strip():
        raise CinematographyError("intent must not be empty")
    catalog, genres, support = load_knowledge()
    ranked = _ranked_by_category(
        intent, genre, platform, subject_priority, stability, provider, catalog, genres, support
    )
    results: list[dict[str, Any]] = []
    for variant in range(max(1, min(top_n, 3))):
        selected = {
            category: _pick(ranked, category, variant if category in {"movement", "shot_size", "angle"} else 0)
            for category in DEFAULTS
        }
        if platform in {"tiktok", "reels", "shorts"}:
            selected["social"] = _pick(ranked, "social", 0)
        vfx_candidate = ranked.get("vfx", [(0.0, {})])[0]
        if vfx_candidate[0] >= 6.0:
            selected["vfx"] = vfx_candidate[1]
        technique_ids = list(dict.fromkeys(item["id"] for item in selected.values()))
        grammar = empty_grammar()
        grammar.update(
            {
                "recommendation_id": f"REC_{variant + 1:02d}",
                "dramatic_beat": intent,
                "viewer_should_feel": sorted(_tokens(intent)) or [intent],
                "technique_ids": technique_ids,
                "shot_size": selected["shot_size"]["id"],
                "angle": selected["angle"]["id"],
                "camera_height": selected["angle"].get("camera_height", "eye"),
                "roll": selected["angle"].get("roll", "level"),
                "lens_family": selected["lens"]["id"],
                "focal_length_hint_35mm": selected["lens"].get("focal_hint"),
                "camera_distance": selected["lens"].get("camera_distance", "contextual"),
                "depth_of_field": selected["focus"].get("depth_of_field", "selective"),
                "focus_plan": selected["focus"]["id"],
                "movement": selected["movement"]["id"],
                "movement_speed": selected["movement"].get("speed", "controlled"),
                "composition": [selected["composition"]["id"]],
                "lighting": [selected["lighting"]["id"]],
                "color_grade": selected["color"]["id"],
                "temporal_plan": selected["temporal"]["id"],
                "blocking": selected["blocking"]["id"],
                "screen_direction": "preserve the established screen direction and 180-degree axis",
                "axis_side": selected["continuity"]["id"],
                "social_plan": selected.get("social", {}).get("id"),
                "audio_perspective": selected["audio"]["id"],
                "vfx_plan": selected.get("vfx", {}).get("id"),
                "duration_seconds": duration_seconds,
                "transition_in": "editing.straight_cut",
                "transition_out": selected["editing"]["id"],
                "why": "; ".join(item["plain_language"] for item in selected.values()),
                "qc_plan": sorted({check for item in selected.values() for check in item.get("qc", [])}),
                "evidence": sorted({source for item in selected.values() for source in item.get("sources", [])}),
            }
        )
        if provider:
            levels = [support_level(provider, identifier, support) for identifier in technique_ids]
            grammar["provider_binding"].update(
                {"provider": provider, "support_level": _lowest_support(levels)}
            )
        complete_errors, warnings = validate_grammar(grammar, require_complete=False, catalog=catalog)
        grammar["status"] = "RECOMMENDED" if not complete_errors else "DRAFT"
        results.append(
            {
                "id": grammar["recommendation_id"],
                "plain_summary": _summary(grammar, technique_index(catalog)),
                "grammar": grammar,
                "errors": complete_errors,
                "warnings": warnings,
            }
        )
    return {
        "intent": intent,
        "genre": genre,
        "platform": platform,
        "provider": provider,
        "recommendations": results,
    }


def _lowest_support(levels: Iterable[str]) -> str:
    order = [
        "native_structured",
        "native_reference",
        "prompt_soft",
        "post_only",
        "web_only",
        "unreliable",
        "unsupported",
    ]
    material = list(levels)
    return max(material, key=order.index) if material else "unsupported"


def _summary(grammar: dict[str, Any], index: dict[str, dict[str, Any]]) -> str:
    ids = [
        grammar.get("shot_size"),
        grammar.get("angle"),
        grammar.get("lens_family"),
        grammar.get("movement"),
    ]
    return " + ".join(index[item]["name_ko"] for item in ids if item in index)


def validate_grammar(
    grammar: dict[str, Any],
    *,
    require_complete: bool,
    catalog: dict[str, Any] | None = None,
    shot_duration: float | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(grammar, dict):
        return ["shot_grammar must be an object"], []
    unknown_fields = sorted(set(grammar) - set(empty_grammar()))
    if unknown_fields:
        errors.append("unknown shot_grammar fields: " + ", ".join(unknown_fields))
    if catalog is None:
        catalog = read_json(CATALOG_PATH)
    index = technique_index(catalog)
    unknown = sorted(set(grammar.get("technique_ids", [])) - set(index))
    if unknown:
        errors.append("unknown technique ids: " + ", ".join(unknown))
    for field in ("viewer_should_feel", "technique_ids", "composition", "lighting", "qc_plan", "evidence"):
        if field in grammar and not isinstance(grammar[field], list):
            errors.append(f"{field} must be an array")
    if grammar.get("duration_seconds") is not None:
        try:
            if float(grammar["duration_seconds"]) <= 0:
                errors.append("duration_seconds must be positive")
        except (TypeError, ValueError):
            errors.append("duration_seconds must be numeric")
    if shot_duration is not None and grammar.get("duration_seconds") is not None:
        if abs(float(grammar["duration_seconds"]) - float(shot_duration)) > 0.001:
            errors.append("shot_grammar duration_seconds must match shot duration_seconds")
    selected = set(grammar.get("technique_ids", []))
    fields_to_ids = [grammar.get("shot_size"), grammar.get("angle"), grammar.get("lens_family"), grammar.get("focus_plan"), grammar.get("movement"), grammar.get("temporal_plan"), grammar.get("transition_out")]
    for field, prefix in (("blocking", "blocking."), ("axis_side", "continuity."), ("color_grade", "color."), ("social_plan", "social."), ("audio_perspective", "audio."), ("vfx_plan", "vfx.")):
        value = grammar.get(field)
        if isinstance(value, str) and (value in index or value.startswith(prefix)):
            fields_to_ids.append(value)
    fields_to_ids.extend(grammar.get("composition", []) if isinstance(grammar.get("composition"), list) else [])
    fields_to_ids.extend(grammar.get("lighting", []) if isinstance(grammar.get("lighting"), list) else [])
    for identifier in fields_to_ids:
        if identifier and identifier not in index:
            errors.append(f"unknown selected technique: {identifier}")
        elif identifier and identifier not in selected:
            warnings.append(f"selected field {identifier} is not listed in technique_ids")
    for identifier in selected:
        item = index.get(identifier, {})
        conflicts = selected & set(item.get("incompatible_with", []))
        if conflicts:
            errors.append(f"{identifier} conflicts with {', '.join(sorted(conflicts))}")
    movement_ids = [identifier for identifier in selected if index.get(identifier, {}).get("category") == "movement"]
    if len(movement_ids) > 1:
        errors.append("one shot may contain only one primary camera movement")
    if grammar.get("intentional_break"):
        warnings.append("intentional continuity break requires explicit user explanation and approval")
    if grammar.get("movement") in {"movement.orbit", "movement.crane", "movement.fpv", "movement.dolly_zoom"}:
        duration = grammar.get("duration_seconds")
        if duration is not None and float(duration) < 4:
            warnings.append("complex camera movement under four seconds is unreliable")
    if "lighting.silhouette" in selected and grammar.get("shot_size") in {"shot.cu", "shot.ecu"}:
        warnings.append("silhouette lighting conflicts with readable close-up facial emotion")
    binding = grammar.get("provider_binding")
    if binding is not None and not isinstance(binding, dict):
        errors.append("provider_binding must be an object")
    elif isinstance(binding, dict):
        unknown_binding = sorted(
            set(binding) - set(empty_grammar()["provider_binding"])
        )
        if unknown_binding:
            errors.append("unknown provider_binding fields: " + ", ".join(unknown_binding))
        level = binding.get("support_level")
        if level is not None and level not in SUPPORT_LEVELS:
            errors.append(f"invalid provider support level: {level}")
    if require_complete:
        for field in REQUIRED_GRAMMAR_FIELDS:
            value = grammar.get(field)
            if value is None or value == "" or value == []:
                errors.append(f"required shot_grammar field is missing: {field}")
        if not selected:
            errors.append("technique_ids must not be empty")
        if not isinstance(binding, dict) or not binding.get("provider"):
            errors.append("provider_binding.provider is required")
        if not isinstance(binding, dict) or not binding.get("compiled_prompt"):
            errors.append("provider_binding.compiled_prompt is required")
        if not isinstance(binding, dict) or not binding.get("schema_verified_at"):
            errors.append("provider_binding.schema_verified_at is required")
        if not isinstance(binding, dict) or not binding.get("schema_contract_hash"):
            errors.append("provider_binding.schema_contract_hash is required")
    return sorted(set(errors)), sorted(set(warnings))


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_live_schema(
    provider: str,
    live_schema: dict[str, Any] | None,
    *,
    max_age_hours: float = 24.0,
) -> tuple[dict[str, Any], str, str]:
    if not isinstance(live_schema, dict):
        raise CinematographyError(f"fresh live schema is required for provider: {provider}")
    contract = _contract_from_snapshot(provider, live_schema)
    if not isinstance(contract, dict):
        raise CinematographyError(f"provider contract absent from live schema: {provider}")
    captured_at = live_schema.get("captured_at")
    try:
        captured = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError) as exc:
        raise CinematographyError("live schema captured_at is missing or invalid") from exc
    age_hours = (datetime.now(timezone.utc) - captured.astimezone(timezone.utc)).total_seconds() / 3600
    if age_hours < -0.25 or age_hours > max_age_hours:
        raise CinematographyError(
            f"live schema is stale or future-dated: age={age_hours:.2f}h, max={max_age_hours:.2f}h"
        )
    kind = "workflows" if provider in live_schema.get("workflow_contracts", {}) else "models"
    recorded = live_schema.get("contract_fingerprints", {}).get(kind, {}).get(provider)
    calculated = stable_hash(contract)
    if recorded is not None and recorded != calculated:
        raise CinematographyError(f"live schema contract fingerprint mismatch: {provider}")
    return contract, str(captured_at), calculated


def _reference_transport(references: dict[str, Any] | None) -> dict[str, Any]:
    source = references if isinstance(references, dict) else {}
    for key in ("images", "videos", "audios"):
        if key in source and not isinstance(source[key], list):
            raise CinematographyError(f"references.{key} must be an array")
    result: dict[str, Any] = {
        "start_image": source.get("start"),
        "end_image": source.get("end"),
        "image_references": list(source.get("images") or []),
        "video_references": list(source.get("videos") or []),
        "audio_references": list(source.get("audios") or []),
    }
    manifest = source.get("manifest") or []
    if not isinstance(manifest, list):
        raise CinematographyError("references.manifest must be an array")
    for offset, item in enumerate(manifest):
        if not isinstance(item, dict):
            raise CinematographyError(f"references.manifest[{offset}] must be an object")
        field = item.get("transport_field")
        value = item.get("source")
        if item.get("semantic_role") not in REFERENCE_ROLES:
            raise CinematographyError(f"references.manifest[{offset}] has invalid semantic_role")
        if not isinstance(item.get("controls", []), list):
            raise CinematographyError(f"references.manifest[{offset}].controls must be an array")
        if field not in result:
            raise CinematographyError(f"references.manifest[{offset}] has invalid transport_field")
        if item.get("prompt_alias"):
            raise CinematographyError("CLI reference aliases are not exposed by the live Seedance contract")
        if field in {"start_image", "end_image"}:
            if result[field] and result[field] != value:
                raise CinematographyError(f"multiple values assigned to {field}")
            result[field] = value
        elif value is not None and value not in result[field]:
            result[field].append(value)
    return result


def _seedance_native_params(
    provider: str,
    grammar: dict[str, Any],
    plan: dict[str, Any] | None,
    references: dict[str, Any] | None,
    boundary_strategy: str | None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    merged = default_seedance_plan()
    if plan is not None:
        if not isinstance(plan, dict):
            raise CinematographyError("seedance_plan must be an object")
        unknown = sorted(set(plan) - set(merged))
        if unknown:
            raise CinematographyError("unknown seedance_plan fields: " + ", ".join(unknown))
        merged.update(deepcopy(plan))
    if merged["mode"] not in {"controlled_single_shot", "seedance_multishot_experimental"}:
        raise CinematographyError(f"invalid Seedance production mode: {merged['mode']}")
    shot_count = merged.get("shot_count")
    if not isinstance(shot_count, int) or isinstance(shot_count, bool) or shot_count < 1:
        raise CinematographyError("seedance_plan.shot_count must be a positive integer")
    beats = merged.get("timed_beats")
    if not isinstance(beats, list):
        raise CinematographyError("seedance_plan.timed_beats must be an array")
    if merged["mode"] == "controlled_single_shot":
        if shot_count != 1 or beats:
            raise CinematographyError("controlled_single_shot requires shot_count=1 and no timed beats")
    elif not merged.get("experimental_approved"):
        raise CinematographyError("experimental Seedance multi-shot requires explicit user approval")
    elif shot_count < 2 or len(beats) != shot_count:
        raise CinematographyError("experimental Seedance multi-shot requires one timed beat per shot")
    audio_mode = merged.get("audio_mode")
    if audio_mode not in {"none", "native_sfx", "native_dialogue", "audio_reference", "post_only"}:
        raise CinematographyError(f"invalid Seedance audio mode: {audio_mode}")
    transport = _reference_transport(references)
    duration_value = float(grammar["duration_seconds"])
    if not duration_value.is_integer():
        raise CinematographyError("Seedance duration must be a whole number of seconds")
    params: dict[str, Any] = {
        "duration": int(duration_value),
        "aspect_ratio": merged["aspect_ratio"],
        "resolution": merged["resolution"],
        "bitrate_mode": merged["bitrate_mode"],
        "generate_audio": audio_mode in {"native_sfx", "native_dialogue", "audio_reference"},
    }
    if provider == "seedance_2_0":
        params["mode"] = merged["generation_mode"]
    elif merged["generation_mode"] != "std":
        raise CinematographyError("Seedance Mini live contract does not expose generation mode")
    for key, value in transport.items():
        if value not in (None, [], ""):
            params[key] = value
    image_count = len(transport["image_references"]) + int(bool(transport["start_image"])) + int(bool(transport["end_image"]))
    video_count = len(transport["video_references"])
    audio_count = len(transport["audio_references"])
    errors: list[str] = []
    if not transport["start_image"]:
        errors.append("Seedance single-start-image contract requires start_image")
    if transport["image_references"]:
        errors.append("Seedance video calls must not carry image references; compose them into start_image")
    if transport["end_image"] and boundary_strategy != "motivated_transition":
        errors.append("Seedance end_image is allowed only for boundary_strategy=motivated_transition")
    if not 4 <= duration_value <= 15:
        errors.append("Seedance duration must be between 4 and 15 seconds")
    if merged.get("prototype") and duration_value > 8:
        errors.append("Seedance prototype shots must be 8 seconds or shorter")
    if image_count > 9:
        errors.append("Seedance image references including start/end exceed 9")
    if video_count > 3:
        errors.append("Seedance video references exceed 3")
    if audio_count > 3:
        errors.append("Seedance audio references exceed 3")
    if image_count + video_count + audio_count > 12:
        errors.append("Seedance total references exceed 12")
    if audio_count and image_count + video_count == 0:
        errors.append("Seedance audio references require at least one visual reference")
    if audio_count and audio_mode != "audio_reference":
        errors.append("Seedance audio references require audio_mode=audio_reference")
    if merged["generation_mode"] == "fast" and str(merged["resolution"]).lower() in {"1080p", "4k"}:
        errors.append("Seedance fast mode supports at most 720p")
    return params, merged, errors


def compile_prompt(
    grammar: dict[str, Any],
    *,
    provider: str,
    subject: str,
    setting: str,
    action: str,
    exit_state: str,
    invariants: list[str] | None = None,
    live_schema: dict[str, Any] | None = None,
    seedance_plan: dict[str, Any] | None = None,
    references: dict[str, Any] | None = None,
    boundary_strategy: str | None = None,
    schema_max_age_hours: float = 24.0,
) -> dict[str, Any]:
    catalog, _, support = load_knowledge()
    index = technique_index(catalog)
    structural_errors, warnings = validate_grammar(grammar, require_complete=False, catalog=catalog)
    if structural_errors:
        raise CinematographyError("cannot compile invalid grammar:\n- " + "\n- ".join(structural_errors))
    if provider not in support.get("providers", {}):
        raise CinematographyError(f"unknown provider: {provider}")
    profile = support["providers"][provider]
    if profile.get("kind") in {"web_ui", "mcp"}:
        blocker = profile.get("automation_blocker") or profile.get("verification_blocker")
        raise CinematographyError(f"provider is not automation-ready: {provider}; {blocker or 'no executable contract'}")
    selected = [index[item] for item in grammar.get("technique_ids", []) if item in index]
    camera_terms = [
        index[item]["prompt"]
        for item in (grammar.get("shot_size"), grammar.get("angle"), grammar.get("lens_family"), grammar.get("focus_plan"), grammar.get("movement"))
        if item in index
    ]
    look_terms = [index[item]["prompt"] for item in grammar.get("composition", []) + grammar.get("lighting", []) if item in index]
    for item in (grammar.get("color_grade"), grammar.get("blocking"), grammar.get("axis_side"), grammar.get("social_plan"), grammar.get("audio_perspective"), grammar.get("vfx_plan")):
        if item in index:
            look_terms.append(index[item]["prompt"])
    temporal = grammar.get("temporal_plan")
    if temporal in index:
        look_terms.append(index[temporal]["prompt"])
    constraints = sorted({text for item in selected for text in item.get("constraints", [])})
    plan: dict[str, Any] | None = None
    native_params = _native_params(grammar, provider, profile)
    seedance_errors: list[str] = []
    if provider in {"seedance_2_0", "seedance_2_0_mini"}:
        native_params, plan, seedance_errors = _seedance_native_params(
            provider, grammar, seedance_plan, references, boundary_strategy
        )
    if seedance_errors:
        raise CinematographyError("Seedance plan rejected:\n- " + "\n- ".join(seedance_errors))
    duration = grammar.get("duration_seconds")
    if plan and plan["mode"] == "seedance_multishot_experimental":
        header = f"{plan['shot_count']} shots / {duration}s / {plan['aspect_ratio']} / timecoded experimental sequence"
        beat_text = []
        for offset, beat in enumerate(plan["timed_beats"], 1):
            if not isinstance(beat, dict) or not beat.get("time") or not beat.get("action"):
                raise CinematographyError(f"timed beat {offset} requires time and action")
            beat_text.append(f"Shot {offset} [{beat['time']}]: {beat['action']}")
    elif plan:
        aspect = plan["aspect_ratio"]
        header = f"1 shot / {duration}s / {aspect} / single continuous shot"
        beat_text = []
        forbidden = re.compile(r"\b(cut to|hard cut|jump cut|montage|multi[- ]?shot)\b", re.IGNORECASE)
        if forbidden.search(" ".join((subject, setting, action, exit_state))):
            raise CinematographyError("single continuous Seedance shot conflicts with cuts or montage language")
    else:
        header = ""
        beat_text = []
    if plan:
        compact_camera = list(dict.fromkeys(camera_terms))[:4]
        compact_look = list(dict.fromkeys(look_terms))[:2]
        prompt_parts = [
            header,
            "Begin exactly on the provided start image framing",
            f"Subject and action: {subject.strip()}; {action.strip()}",
            f"Camera: {', '.join(compact_camera)}",
            f"Setting, light, and mood: {setting.strip()}; {', '.join(compact_look)}; {grammar.get('dramatic_beat') or ''}",
            *beat_text,
            f"End state: {exit_state.strip()}",
        ]
    else:
        prompt_parts = [
            f"{subject} in {setting}".strip(),
            action.strip(),
            ", ".join(camera_terms),
            ", ".join(look_terms),
            f"End state: {exit_state.strip()}",
        ]
    all_invariants = list(invariants or [])
    if plan:
        all_invariants.extend(plan.get("camera_invariants") or [])
    all_invariants.extend(constraints)
    if all_invariants:
        unique_invariants = list(dict.fromkeys(item.strip() for item in all_invariants if item.strip()))
        if plan:
            unique_invariants = unique_invariants[:3]
        prompt_parts.append("Critical invariants: " + "; ".join(unique_invariants))
    if plan:
        prompt_parts.append(f"Audio: {plan['audio_mode']}")
    prompt = ". ".join(part for part in prompt_parts if part and part != " in")
    schema_verified_at = None
    schema_contract_hash = None
    if profile.get("schema_required"):
        _, schema_verified_at, schema_contract_hash = validate_live_schema(
            provider, live_schema, max_age_hours=schema_max_age_hours
        )
    if live_schema is not None:
        schema_errors = validate_native_params_against_schema(provider, native_params, live_schema)
        if schema_errors:
            raise CinematographyError("live schema rejected compiled params:\n- " + "\n- ".join(schema_errors))
    levels = {item["id"]: support_level(provider, item["id"], support) for item in selected}
    unsupported = [identifier for identifier, level in levels.items() if level in {"unsupported", "web_only"}]
    if unsupported:
        warnings.append("provider cannot directly execute: " + ", ".join(unsupported))
    result = {
        "provider": provider,
        "prompt": prompt,
        "native_params": native_params,
        "technique_support": levels,
        "support_level": _lowest_support(levels.values()),
        "warnings": sorted(set(warnings)),
        "qc_checks": sorted({check for item in selected for check in item.get("qc", [])}),
        "schema_verified_at": schema_verified_at,
        "schema_contract_hash": schema_contract_hash,
        "seedance_plan": plan,
    }
    return result


def _native_params(grammar: dict[str, Any], provider: str, profile: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    mappings = profile.get("native_mappings", {})
    selected = set(grammar.get("technique_ids", []))
    selected.update(
        item
        for item in (grammar.get("movement"), grammar.get("color_grade"), grammar.get("temporal_plan"))
        if item
    )
    selected.update(grammar.get("lighting", []))
    for field, choices in mappings.items():
        for technique_id, value in choices.items():
            if technique_id in selected:
                params[field] = value
                break
    return params


def _contract_from_snapshot(provider: str, live_schema: dict[str, Any]) -> dict[str, Any] | None:
    return live_schema.get("workflow_contracts", {}).get(provider) or live_schema.get("model_contracts", {}).get(provider)


def validate_native_params_against_schema(
    provider: str, native_params: dict[str, Any], live_schema: dict[str, Any]
) -> list[str]:
    contract = _contract_from_snapshot(provider, live_schema)
    if not isinstance(contract, dict):
        return [f"provider contract absent from live schema: {provider}"]
    declared = {item.get("name"): item for item in contract.get("params", []) if isinstance(item, dict)}
    errors: list[str] = []
    for key, value in native_params.items():
        if key not in declared:
            errors.append(f"native param is not declared: {key}")
            continue
        allowed = declared[key].get("enum")
        if isinstance(allowed, list) and value not in allowed:
            errors.append(f"native param {key} value is not allowed: {value}")
        minimum = declared[key].get("minimum", declared[key].get("min"))
        maximum = declared[key].get("maximum", declared[key].get("max"))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if isinstance(minimum, (int, float)) and value < minimum:
                errors.append(f"native param {key} is below minimum {minimum}: {value}")
            if isinstance(maximum, (int, float)) and value > maximum:
                errors.append(f"native param {key} exceeds maximum {maximum}: {value}")
        declared_type = declared[key].get("type")
        if declared_type == "boolean" and not isinstance(value, bool):
            errors.append(f"native param {key} must be boolean")
        if declared_type in {"integer", "number"} and (
            not isinstance(value, (int, float)) or isinstance(value, bool)
        ):
            errors.append(f"native param {key} must be numeric")
    for item in contract.get("params", []):
        if (
            isinstance(item, dict)
            and item.get("required")
            and item.get("name") not in {"prompt"}
            and item.get("name") not in native_params
        ):
            errors.append(f"required native param is missing: {item.get('name')}")
    return errors


def apply_compilation(grammar: dict[str, Any], compiled: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(grammar)
    result.setdefault("provider_binding", {}).update(
        {
            "provider": compiled["provider"],
            "support_level": compiled["support_level"],
            "native_params": compiled["native_params"],
            "compiled_prompt": compiled["prompt"],
            "schema_verified_at": compiled.get("schema_verified_at"),
            "schema_contract_hash": compiled.get("schema_contract_hash"),
        }
    )
    result["qc_plan"] = sorted(set(result.get("qc_plan", [])) | set(compiled.get("qc_checks", [])))
    errors, _ = validate_grammar(result, require_complete=True)
    result["status"] = "VALIDATED" if not errors else "DRAFT"
    return result
