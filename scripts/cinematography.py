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

import director_intelligence


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


def technique_prompt(index: dict[str, dict[str, Any]], identifier: Any) -> str | None:
    if not isinstance(identifier, str):
        return None
    value = index.get(identifier, {}).get("prompt")
    return value if isinstance(value, str) and value.strip() else None


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
            "prompt_lint": None,
        },
        "qc_plan": [],
        "evidence": [],
    }


def default_seedance_plan() -> dict[str, Any]:
    """Minimum-sufficient baseline; routing may select native multi-shot."""
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
        "prompt_kind": "simple",
        "load_bearing_element": None,
        "camera_invariants": [],
        "start_frame_behavior": "match_then_release",
        "image_input_policy": {
            "mode": "start_only",
            "rationale": None,
            "baseline_job_id": None,
            "baseline_failure": None,
            "essential_reference_role": None,
            "changed_variable": None,
        },
        "sound_design": {
            "dialogue": None,
            "ambience": None,
            "synchronized_effects": [],
            "music": None,
            "exclusions": [],
        },
        # Retained only so v8 plans deserialize. Native multi-shot is now a
        # routed production choice, not a blanket experimental exception.
        "experimental_approved": False,
    }


def default_cinema35_plan() -> dict[str, Any]:
    """Live Cinema Studio 3.5 workflow settings plus conservative internal policy."""
    return {
        "visual_priority": "balanced",
        "camera_style": None,
        "light_scheme": None,
        "color_grading": None,
        "genre": "auto",
        "aspect_ratio": "auto",
        "resolution": "720p",
        "prompt_language": "en",
        "enhance_prompt": False,
        "audio_mode": "none",
        "sound_design": deepcopy(default_seedance_plan()["sound_design"]),
        "multi_shots": False,
        "multi_shot_mode": "custom",
        "multi_prompt": [],
        "style_prompt": None,
        "start_frame_behavior": "match_then_release",
        "prompt_kind": "simple",
        "load_bearing_element": None,
        "camera_invariants": [],
    }


START_FRAME_BEHAVIORS = {
    "preserve_composition",
    "match_then_release",
    "identity_anchor_only",
}


def start_frame_prompt(behavior: str) -> str:
    if behavior == "preserve_composition":
        return "Match the supplied first frame and preserve its initial composition as motion begins"
    if behavior == "identity_anchor_only":
        return "Use the supplied first frame as the identity and spatial anchor; deliberate reframing may begin immediately"
    return "Match the supplied first frame, then let the planned camera move reframe naturally"


def validate_image_input_policy(value: Any) -> list[str]:
    """Validate the evidence-led Seedance image transport policy."""
    if not isinstance(value, dict):
        return ["seedance_plan.image_input_policy must be an object"]
    allowed = {
        "mode",
        "rationale",
        "baseline_job_id",
        "baseline_failure",
        "essential_reference_role",
        "changed_variable",
    }
    unknown = sorted(set(value) - allowed)
    errors = ["unknown image_input_policy fields: " + ", ".join(unknown)] if unknown else []
    mode = value.get("mode")
    if mode not in {"start_only", "start_plus_essential_reference", "start_end_transition"}:
        errors.append(f"invalid image_input_policy.mode: {mode}")
        return errors
    for key in allowed - {"mode"}:
        item = value.get(key)
        if item is not None and (not isinstance(item, str) or not item.strip()):
            errors.append(f"image_input_policy.{key} must be a non-empty string or null")
    if mode == "start_plus_essential_reference":
        for key in (
            "rationale",
            "baseline_job_id",
            "baseline_failure",
            "essential_reference_role",
            "changed_variable",
        ):
            if not isinstance(value.get(key), str) or not value[key].strip():
                errors.append(f"start_plus_essential_reference requires image_input_policy.{key}")
        if value.get("essential_reference_role") not in REFERENCE_ROLES:
            errors.append("image_input_policy.essential_reference_role is invalid")
    if mode == "start_end_transition" and (
        not isinstance(value.get("rationale"), str) or not value["rationale"].strip()
    ):
        errors.append("start_end_transition requires image_input_policy.rationale")
    return errors


def validate_sound_design(value: Any, *, require_complete: bool = False) -> list[str]:
    """Validate a compact native-generation sound brief."""
    if not isinstance(value, dict):
        return ["seedance_plan.sound_design must be an object"]
    allowed = {"dialogue", "ambience", "synchronized_effects", "music", "exclusions"}
    errors: list[str] = []
    unknown = sorted(set(value) - allowed)
    if unknown:
        errors.append("unknown sound_design fields: " + ", ".join(unknown))
    for key in ("dialogue", "ambience", "music"):
        item = value.get(key)
        if item is not None and (not isinstance(item, str) or not item.strip()):
            errors.append(f"sound_design.{key} must be a non-empty string or null")
        if require_complete and (not isinstance(item, str) or not item.strip()):
            errors.append(f"complete native sound requires sound_design.{key}")
    for key, maximum in (("synchronized_effects", 3), ("exclusions", 4)):
        items = value.get(key)
        if not isinstance(items, list) or any(not isinstance(item, str) or not item.strip() for item in items):
            errors.append(f"sound_design.{key} must be an array of non-empty strings")
        elif len(items) > maximum:
            errors.append(f"sound_design.{key} supports at most {maximum} compact entries")
    return errors


NO_DIALOGUE_BRIEFS = {"none", "no dialogue", "no spoken dialogue", "무대사", "대사 없음"}


def is_no_dialogue_brief(value: Any) -> bool:
    """Return whether a compact sound brief explicitly forbids spoken dialogue."""
    return isinstance(value, str) and value.strip().casefold() in NO_DIALOGUE_BRIEFS


def seedance_audio_prompt(plan: dict[str, Any]) -> str:
    """Render one compact audio clause without pretending references are pass-through."""
    mode = plan["audio_mode"]
    if mode not in {"audio_reference", "native_sfx"}:
        return f"Audio: {mode}"
    sound = plan["sound_design"]
    effects = "; ".join(sound["synchronized_effects"]) or "none"
    exclusions = "; ".join(sound["exclusions"]) or "none"
    if mode == "native_sfx":
        return (
            f"Audio: no visible or spoken dialogue; ambience: {sound['ambience']}; "
            f"synchronized effects: {effects}; music: {sound['music']}; exclude: {exclusions}; "
            "generate the complete production sound with the picture and keep the native rendered track"
        )
    return (
        "Audio: use the supplied ElevenLabs V3 dialogue reference as guidance for voice, "
        f"performance, pronunciation, timing, and lip movement; dialogue: {sound['dialogue']}; "
        f"ambience: {sound['ambience']}; synchronized effects: {effects}; music: {sound['music']}; "
        f"exclude: {exclusions}; generate the complete production sound with the picture and keep "
        "the native rendered track"
    )


def native_sfx_prompt(plan: dict[str, Any]) -> str:
    sound = plan["sound_design"]
    effects = "; ".join(sound["synchronized_effects"]) or "none"
    exclusions = "; ".join(sound["exclusions"]) or "none"
    return (
        f"Audio: no visible or spoken dialogue; ambience: {sound['ambience']}; "
        f"synchronized effects: {effects}; music: {sound['music']}; exclude: {exclusions}; "
        "generate the complete production sound with the picture and keep the native rendered track"
    )


def merge_grammar(current: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(patch, dict):
        raise CinematographyError("shot_grammar must be an object")
    result = empty_grammar()
    if isinstance(current, dict):
        _deep_update(result, current)
    _deep_update(result, patch)
    if isinstance(patch.get("provider_binding"), dict):
        # A compiled binding is an atomic artifact: deep-merging it with a
        # previous provider's binding resurrects stale native params (for
        # example Seedance mode/bitrate_mode surviving a switch to Cinema
        # Studio) and permanently fails the execution gate. Replace wholesale.
        binding = empty_grammar()["provider_binding"]
        binding.update(deepcopy(patch["provider_binding"]))
        result["provider_binding"] = binding
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
        copied = deepcopy(plan)
        if "image_input_policy" in copied:
            policy = copied.pop("image_input_policy")
            if not isinstance(policy, dict):
                raise CinematographyError("seedance_plan.image_input_policy must be an object")
            merged["image_input_policy"].update(policy)
        merged.update(copied)
    if merged["mode"] not in {"controlled_single_shot", "native_multishot", "seedance_multishot_experimental"}:
        raise CinematographyError(f"invalid Seedance production mode: {merged['mode']}")
    if merged.get("start_frame_behavior") not in START_FRAME_BEHAVIORS:
        raise CinematographyError(
            f"invalid Seedance start_frame_behavior: {merged.get('start_frame_behavior')}"
        )
    shot_count = merged.get("shot_count")
    if not isinstance(shot_count, int) or isinstance(shot_count, bool) or shot_count < 1:
        raise CinematographyError("seedance_plan.shot_count must be a positive integer")
    beats = merged.get("timed_beats")
    if not isinstance(beats, list):
        raise CinematographyError("seedance_plan.timed_beats must be an array")
    if merged["mode"] == "controlled_single_shot":
        if shot_count != 1 or beats:
            raise CinematographyError("controlled_single_shot requires shot_count=1 and no timed beats")
    elif shot_count < 2 or len(beats) != shot_count:
        raise CinematographyError("native Seedance multi-shot requires one timed beat per shot")
    elif shot_count > 4:
        raise CinematographyError("native Seedance multi-shot is limited to four simple timed beats")
    audio_mode = merged.get("audio_mode")
    if audio_mode not in {"none", "native_sfx", "native_dialogue", "audio_reference", "post_only"}:
        raise CinematographyError(f"invalid Seedance audio mode: {audio_mode}")
    sound_errors = validate_sound_design(
        merged.get("sound_design"), require_complete=audio_mode in {"audio_reference", "native_sfx"}
    )
    if audio_mode == "native_sfx" and not is_no_dialogue_brief(
        (merged.get("sound_design") or {}).get("dialogue")
    ):
        sound_errors.append(
            "native_sfx requires sound_design.dialogue to explicitly say none or no dialogue"
        )
    if sound_errors:
        raise CinematographyError("invalid Seedance sound design:\n- " + "\n- ".join(sound_errors))
    image_policy_errors = validate_image_input_policy(merged.get("image_input_policy"))
    if image_policy_errors:
        raise CinematographyError("invalid Seedance image input policy:\n- " + "\n- ".join(image_policy_errors))
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
        errors.append("Seedance image-input contract requires exactly one start_image")
    image_policy = merged["image_input_policy"]
    image_mode = image_policy["mode"]
    if image_mode == "start_only":
        if transport["image_references"]:
            errors.append("start_only must not carry image_references")
        if transport["end_image"]:
            errors.append("start_only must not carry end_image; describe the exit state in the prompt")
    elif image_mode == "start_plus_essential_reference":
        if len(transport["image_references"]) != 1:
            errors.append("start_plus_essential_reference requires exactly one image_reference")
        if transport["end_image"]:
            errors.append("start_plus_essential_reference must not also carry end_image")
        matching_manifest = [
            item for item in (references or {}).get("manifest", [])
            if isinstance(item, dict)
            and item.get("transport_field") == "image_references"
            and item.get("source") in transport["image_references"]
        ]
        if len(matching_manifest) != 1:
            errors.append("the essential image_reference requires exactly one matching manifest entry")
        elif matching_manifest[0].get("semantic_role") != image_policy.get("essential_reference_role"):
            errors.append("essential image_reference manifest role does not match image_input_policy")
        elif not matching_manifest[0].get("controls"):
            errors.append("essential image_reference manifest must declare controlled attributes")
    elif image_mode == "start_end_transition":
        if transport["image_references"]:
            errors.append("start_end_transition must not also carry image_references")
        if not transport["end_image"]:
            errors.append("start_end_transition requires end_image")
        if boundary_strategy != "motivated_transition":
            errors.append("start_end_transition requires boundary_strategy=motivated_transition")
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
    if audio_mode == "audio_reference" and not audio_count:
        errors.append("Seedance audio_mode=audio_reference requires at least one audio reference")
    if merged["generation_mode"] == "fast" and str(merged["resolution"]).lower() in {"1080p", "4k"}:
        errors.append("Seedance fast mode supports at most 720p")
    return params, merged, errors


def _cinema35_native_params(
    grammar: dict[str, Any],
    inferred_params: dict[str, Any],
    plan: dict[str, Any] | None,
    references: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    merged = default_cinema35_plan()
    if plan is not None:
        if not isinstance(plan, dict):
            raise CinematographyError("cinema35_plan must be an object")
        unknown = sorted(set(plan) - set(merged))
        if unknown:
            raise CinematographyError("unknown cinema35_plan fields: " + ", ".join(unknown))
        copied = deepcopy(plan)
        if "sound_design" in copied:
            sound = copied.pop("sound_design")
            if not isinstance(sound, dict):
                raise CinematographyError("cinema35_plan.sound_design must be an object")
            merged["sound_design"].update(sound)
        merged.update(copied)
    if merged["visual_priority"] not in {"stability", "balanced", "expressive"}:
        raise CinematographyError("cinema35_plan.visual_priority is invalid")
    if merged["start_frame_behavior"] not in START_FRAME_BEHAVIORS:
        raise CinematographyError("cinema35_plan.start_frame_behavior is invalid")
    if merged["audio_mode"] not in {"none", "native_sfx"}:
        raise CinematographyError(
            "Cinema 3.5 audio_mode supports none or native_sfx; dialogue-reference conditioning remains an explicit A/B experiment"
        )
    sound_errors = validate_sound_design(
        merged["sound_design"], require_complete=merged["audio_mode"] == "native_sfx"
    )
    if merged["audio_mode"] == "native_sfx" and not is_no_dialogue_brief(
        merged["sound_design"].get("dialogue")
    ):
        sound_errors.append(
            "Cinema 3.5 native_sfx requires sound_design.dialogue to explicitly say none or no dialogue"
        )
    if sound_errors:
        raise CinematographyError("invalid Cinema 3.5 sound design:\n- " + "\n- ".join(sound_errors))
    if not isinstance(merged["multi_prompt"], list) or any(
        not isinstance(item, str) or not item.strip() for item in merged["multi_prompt"]
    ):
        raise CinematographyError("cinema35_plan.multi_prompt must be an array of non-empty strings")
    if merged["multi_shots"] and len(merged["multi_prompt"]) < 2:
        raise CinematographyError("Cinema 3.5 multi_shots requires at least two multi_prompt entries")
    if not merged["multi_shots"] and merged["multi_prompt"]:
        raise CinematographyError("Cinema 3.5 multi_prompt requires multi_shots=true")
    if merged["style_prompt"] and any(
        merged.get(field) for field in ("camera_style", "light_scheme", "color_grading")
    ):
        raise CinematographyError(
            "Cinema 3.5 style_prompt is mutually exclusive with camera_style, light_scheme, and color_grading"
        )
    transport = _reference_transport(references)
    total_references = (
        int(bool(transport["start_image"]))
        + int(bool(transport["end_image"]))
        + len(transport["image_references"])
        + len(transport["video_references"])
        + len(transport["audio_references"])
    )
    errors: list[str] = []
    if total_references > 15:
        errors.append("Cinema 3.5 total media references exceed 15")
    if transport["audio_references"]:
        errors.append(
            "Cinema 3.5 audio-reference conditioning is not yet a proven production route; run an explicit A/B outside the paid gate"
        )
    duration_value = float(grammar["duration_seconds"])
    if not duration_value.is_integer():
        errors.append("Cinema 3.5 duration must be a whole number of seconds")
    params = {} if merged["style_prompt"] else dict(inferred_params)
    for field in ("camera_style", "light_scheme", "color_grading"):
        if merged[field] is not None:
            params[field] = merged[field]
    params.update(
        {
            "duration": int(duration_value),
            "genre": merged["genre"],
            "aspect_ratio": merged["aspect_ratio"],
            "resolution": merged["resolution"],
            "prompt_language": merged["prompt_language"],
            "enhance_prompt": merged["enhance_prompt"],
            "generate_audio": merged["audio_mode"] == "native_sfx",
            "multi_shots": merged["multi_shots"],
            "multi_shot_mode": merged["multi_shot_mode"],
        }
    )
    if merged["multi_prompt"]:
        params["multi_prompt"] = merged["multi_prompt"]
    if merged["style_prompt"]:
        params["style_prompt"] = merged["style_prompt"]
    for key, value in transport.items():
        if value not in (None, [], ""):
            params[key] = value
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
    cinema35_plan: dict[str, Any] | None = None,
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
    cinema_plan: dict[str, Any] | None = None
    native_params = _native_params(grammar, provider, profile)
    provider_errors: list[str] = []
    if provider in {"seedance_2_0", "seedance_2_0_mini"}:
        native_params, plan, provider_errors = _seedance_native_params(
            provider, grammar, seedance_plan, references, boundary_strategy
        )
    elif provider == "cinematic_studio_video_3_5":
        native_params, cinema_plan, provider_errors = _cinema35_native_params(
            grammar, native_params, cinema35_plan, references
        )
    if provider_errors:
        label = "Seedance" if plan is not None else "Cinema 3.5"
        raise CinematographyError(f"{label} plan rejected:\n- " + "\n- ".join(provider_errors))
    active_plan = plan or cinema_plan
    duration = grammar.get("duration_seconds")
    if plan and plan["mode"] in {"native_multishot", "seedance_multishot_experimental"}:
        header = f"{plan['shot_count']} shots / {duration}s / {plan['aspect_ratio']} / timecoded sequence"
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
    elif cinema_plan:
        if cinema_plan["multi_shots"]:
            header = (
                f"{len(cinema_plan['multi_prompt'])} shots / {duration}s / "
                f"{cinema_plan['aspect_ratio']} / directed sequence"
            )
        else:
            header = f"1 shot / {duration}s / {cinema_plan['aspect_ratio']} / directed continuous shot"
        beat_text = []
    else:
        header = ""
        beat_text = []
    if plan:
        compact_camera = list(dict.fromkeys(
            item for item in (
                technique_prompt(index, grammar.get("shot_size")),
                technique_prompt(index, grammar.get("movement")),
            ) if item
        ))
        compact_look = list(dict.fromkeys(look_terms))[:1]
        has_start = bool((references or {}).get("start"))
        prompt_parts = [
            header,
            f"Action: {action.strip()}",
            None if has_start else f"Subject: {subject.strip()}",
            start_frame_prompt(plan["start_frame_behavior"]) if has_start else None,
            f"Camera: {', '.join(compact_camera)}",
            f"Scene: {setting.strip()}; {', '.join(compact_look)}",
            *beat_text,
            f"End state: {exit_state.strip()}",
        ]
        image_policy = plan["image_input_policy"]
        if image_policy["mode"] == "start_plus_essential_reference":
            prompt_parts.append(
                "Use the single essential image reference only for "
                f"{image_policy['essential_reference_role']}; keep the start-image composition authoritative"
            )
        elif image_policy["mode"] == "start_end_transition":
            prompt_parts.append(
                "Arrive naturally at the supplied end-image composition without inserting an editorial cut"
            )
    elif cinema_plan:
        has_start = bool((references or {}).get("start"))
        movement_term = technique_prompt(index, grammar.get("movement"))
        shot_term = technique_prompt(index, grammar.get("shot_size"))
        angle_term = technique_prompt(index, grammar.get("angle"))
        compact_camera = list(dict.fromkeys(
            item for item in (movement_term, shot_term, angle_term) if item
        ))[:3]
        native_look_fields = {
            key for key in ("light_scheme", "color_grading") if key in native_params
        }
        compact_look = [] if native_look_fields else list(dict.fromkeys(look_terms))[:1]
        prompt_parts = [
            header,
            f"Action: {action.strip()}",
            None if has_start else f"Subject: {subject.strip()}",
            start_frame_prompt(cinema_plan["start_frame_behavior"]) if has_start else None,
            f"Camera move: {', '.join(compact_camera)}",
            f"Scene: {setting.strip()}" + (f"; {compact_look[0]}" if compact_look else ""),
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
    if active_plan:
        all_invariants.extend(active_plan.get("camera_invariants") or [])
    all_invariants.extend(constraints)
    if all_invariants:
        unique_invariants = list(dict.fromkeys(item.strip() for item in all_invariants if item.strip()))
        if active_plan:
            unique_invariants = unique_invariants[:3]
        prompt_parts.append("Critical invariants: " + "; ".join(unique_invariants))
    if plan:
        prompt_parts.append(seedance_audio_prompt(plan))
    elif cinema_plan and cinema_plan["audio_mode"] == "native_sfx":
        prompt_parts.append(native_sfx_prompt(cinema_plan))
    prompt = ". ".join(part for part in prompt_parts if part and part != " in")
    prompt_lint = None
    prompt_refinement = None
    if active_plan:
        load_bearing = active_plan.get("load_bearing_element") or action.strip()
        prompt_refinement = director_intelligence.refine_prompt(
            prompt,
            kind=active_plan.get("prompt_kind") or (
                "multishot" if (plan and plan["mode"] != "controlled_single_shot")
                or (cinema_plan and cinema_plan["multi_shots"])
                else "simple"
            ),
            load_bearing_element=load_bearing,
        )
        prompt = prompt_refinement["prompt"]
        prompt_lint = prompt_refinement["lint"]
        if prompt_lint["status"] == "BLOCKED":
            messages = [item["message"] for item in prompt_lint["blockers"]]
            raise CinematographyError("minimum-sufficient prompt lint failed:\n- " + "\n- ".join(messages))
        warnings.extend(
            f"prompt lint {item['code']}: advisory refinement recommended"
            for item in prompt_lint["warnings"]
        )
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
        "cinema35_plan": cinema_plan,
        "prompt_lint": prompt_lint,
        "prompt_refinement": prompt_refinement,
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
            "prompt_lint": compiled.get("prompt_lint"),
        }
    )
    result["qc_plan"] = sorted(set(result.get("qc_plan", [])) | set(compiled.get("qc_checks", [])))
    errors, _ = validate_grammar(result, require_complete=True)
    result["status"] = "VALIDATED" if not errors else "DRAFT"
    return result
