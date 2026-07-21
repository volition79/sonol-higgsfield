#!/usr/bin/env python3
"""Small, explainable director aids for adaptive Higgsfield production."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFERENCES = ROOT / "references"


class DirectorIntelligenceError(ValueError):
    pass


def _load(name: str) -> dict[str, Any]:
    return json.loads((REFERENCES / name).read_text(encoding="utf-8"))


def route_production(
    *, intent_type: str, duration_seconds: float, planned_jobs: int, simple_beats: int = 1,
    high_cost: bool = False, continuity: bool = False, exact_dialogue: bool = False,
    precise_performance: bool = False, exact_object_interaction: bool = False,
) -> dict[str, Any]:
    intent = intent_type.strip().lower().replace("-", "_")
    if intent in {"ad", "advertisement", "marketing", "ugc_ad"}:
        return {"mode": "OFFICIAL_WORKFLOW", "approval_profile": "LIGHT", "official_workflow": "marketing_studio", "managed_state": False, "reason": "official ad workflow is purpose-built"}
    if intent in {"explainer", "video_explainer", "narrated_explainer"}:
        return {"mode": "OFFICIAL_WORKFLOW", "approval_profile": "LIGHT", "official_workflow": "video_explainer", "managed_state": False, "reason": "official explainer workflow is purpose-built"}
    if duration_seconds > 15 or planned_jobs > 1 or continuity:
        profile = "FULL" if high_cost or planned_jobs > 2 or duration_seconds > 30 else "TARGETED"
        return {"mode": "SERIAL_STORY", "approval_profile": profile, "official_workflow": None, "managed_state": True, "reason": "multiple jobs or continuity require recovery and sequence state"}
    if high_cost:
        return {"mode": "CONTROLLED_SHOT", "approval_profile": "FULL", "official_workflow": None, "managed_state": True, "reason": "the high-cost generation needs a full preflight and recovery record"}
    if exact_dialogue or precise_performance or exact_object_interaction:
        return {"mode": "CONTROLLED_SHOT", "approval_profile": "TARGETED", "official_workflow": None, "managed_state": True, "reason": "a load-bearing detail benefits from one controlled shot"}
    if 2 <= simple_beats <= 4 and duration_seconds <= 15:
        return {"mode": "NATIVE_MULTISHOT", "approval_profile": "LIGHT", "official_workflow": None, "managed_state": True, "reason": "simple beats can share one native Seedance generation"}
    return {"mode": "QUICK_CLIP", "approval_profile": "LIGHT", "official_workflow": None, "managed_state": False, "reason": "a small exploratory clip does not need the full production system"}


def performance_direction(emotion: str, visible_channels: list[str], maximum: int = 3) -> dict[str, Any]:
    presets = _load("performance-presets.json")["presets"]
    key = emotion.strip().lower()
    if key not in presets:
        return {"status": "NEEDS_SELECTION", "emotion_intent": emotion, "selected_cues": [], "warning": "no preset matches; ask for observable acting direction"}
    selected: list[str] = []
    visible = list(dict.fromkeys(item.strip().lower() for item in visible_channels if item.strip()))
    for channel in visible:
        for cue in presets[key].get(channel, []):
            if cue not in selected and len(selected) < max(1, min(maximum, 3)):
                selected.append(cue)
    return {"status": "ADVISORY", "emotion_intent": key, "visible_channels": visible, "selected_cues": selected, "source": "preset_advisory"}


def camera_alternatives(story_function: str) -> dict[str, Any]:
    strategies = _load("camera-emotion-map.json")["strategies"]
    key = story_function.strip().lower()
    if key not in strategies:
        return {"status": "NEEDS_SELECTION", "story_function": story_function, "alternatives": [], "warning": "no mapping matches; retain the existing director choice"}
    return {
        "status": "ADVISORY", "story_function": key, "support_level": "prompt_soft",
        "alternatives": [dict(strategy="follow", **strategies[key]["follow"]), dict(strategy="contrast", **strategies[key]["contrast"])],
        "selected_strategy": None,
    }


def lint_prompt(prompt: str, *, kind: str = "simple", load_bearing_element: str | None = None) -> dict[str, Any]:
    rules = _load("prompt-language-rules.json")
    text = " ".join(prompt.split())
    lower = text.lower()
    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, str]] = []
    for term, dimensions in rules["abstract_terms"].items():
        if re.search(rf"\b{re.escape(term)}\b", lower):
            warnings.append({"code": "ABSTRACT_TERM", "term": term, "clarify_with": dimensions})
    disambiguators = {
        "tearing": r"\b(?:fabric|paper|cloth|material|eyes|crying|tears)\b",
        "shoot": r"\b(?:camera|film|video|photo|gun|weapon|rifle|pistol|bullet)\b",
        "wave": r"\b(?:hand|ocean|sea|water|surf)\b",
        "draw": r"\b(?:pencil|pen|sketch|paper|weapon|gun|sword|pull)\b",
    }
    for verb, meanings in rules["ambiguous_verbs"].items():
        if re.search(rf"\b{re.escape(verb)}\b", lower) and not re.search(disambiguators.get(verb, r"$^"), lower):
            warnings.append({"code": "AMBIGUOUS_VERB", "term": verb, "possible_meanings": meanings})
    conflicts = (
        (r"\bstatic\b", r"\b(?:tracking|pan|orbit|dolly|push in|pull out|crane)\b", "static camera conflicts with camera movement"),
        (r"\bpush in\b", r"\bpull out\b", "push in conflicts with pull out"),
        (r"\bno cuts?\b", r"\b(?:hard cut|jump cut|cut to|montage)\b", "no-cut direction conflicts with edit language"),
    )
    for left, right, message in conflicts:
        if re.search(left, lower) and re.search(right, lower):
            blockers.append({"code": "CONTRADICTION", "message": message})
    words = re.findall(r"\b[\w'-]+\b", text)
    target = rules["target_ranges"].get(kind, rules["target_ranges"]["simple"])
    if len(words) < target[0] or len(words) > target[1]:
        warnings.append({"code": "TARGET_RANGE", "word_count": len(words), "target_range": target, "note": "advisory only; preserve necessary meaning"})
    load_position = None
    if load_bearing_element:
        pos = lower.find(load_bearing_element.strip().lower())
        load_position = None if pos < 0 else len(re.findall(r"\b[\w'-]+\b", text[:pos])) + 1
        if pos < 0:
            blockers.append({"code": "MISSING_LOAD_BEARING_ELEMENT", "message": "the declared load-bearing element is absent"})
        elif load_position is not None and load_position > 20:
            warnings.append({"code": "LATE_LOAD_BEARING_ELEMENT", "word_position": load_position})
    return {
        "status": "BLOCKED" if blockers else ("PASS_WITH_WARNINGS" if warnings else "PASS"),
        "word_count": len(words), "target_range": target, "load_bearing_element": load_bearing_element,
        "load_bearing_element_position": load_position, "warnings": warnings, "blockers": blockers,
        "meaning_preserved": True,
    }


def refine_prompt(
    prompt: str,
    *,
    kind: str = "simple",
    load_bearing_element: str | None = None,
    static_facts: list[str] | None = None,
) -> dict[str, Any]:
    """Conservatively reorder and deduplicate exact supplied facts; never invent."""
    clauses = [item.strip() for item in re.split(r"(?<=[.!?])\s+", " ".join(prompt.split())) if item.strip()]
    static = {" ".join(item.lower().split()).rstrip(".!?") for item in (static_facts or []) if item.strip()}
    kept: list[str] = []
    removed: list[str] = []
    for clause in clauses:
        normalized = " ".join(clause.lower().split()).rstrip(".!?")
        if normalized in static:
            removed.append(clause)
        else:
            kept.append(clause)
    if load_bearing_element:
        needle = load_bearing_element.strip().lower()
        matching = [item for item in kept if needle in item.lower()]
        if matching:
            chosen = matching[0]
            kept.remove(chosen)
            kept.insert(0, chosen)
    refined = " ".join(kept)
    return {
        "prompt": refined,
        "static_redescription_removed": bool(removed),
        "removed_exact_static_clauses": removed,
        "meaning_preserved": True,
        "lint": lint_prompt(refined, kind=kind, load_bearing_element=load_bearing_element),
    }


def score_complexity(
    *, primary_actions: int = 1, camera_moves: int = 1, characters: int = 1,
    exact_object_interaction: bool = False, major_location_change: bool = False,
    emotion_changes: int = 0, offscreen_interaction: bool = False,
    reflection_or_duplicate: bool = False, fast_subject_and_camera: bool = False,
    dialogue_and_large_motion: bool = False,
) -> dict[str, Any]:
    drivers: list[dict[str, Any]] = []
    def add(condition: bool, code: str, points: int) -> None:
        if condition:
            drivers.append({"code": code, "points": points})
    add(primary_actions > 1, "MULTIPLE_PRIMARY_ACTIONS", 2)
    add(camera_moves > 1, "MULTIPLE_CAMERA_MOVES", 2)
    add(characters > 2, "MORE_THAN_TWO_CHARACTERS", 2)
    add(exact_object_interaction, "EXACT_OBJECT_INTERACTION", 2)
    add(major_location_change, "MAJOR_LOCATION_CHANGE", 2)
    add(emotion_changes >= 2, "MULTIPLE_EMOTION_CHANGES", 1)
    add(offscreen_interaction, "OFFSCREEN_INTERACTION", 2)
    add(reflection_or_duplicate, "REFLECTION_OR_DUPLICATE", 3)
    add(fast_subject_and_camera, "FAST_SUBJECT_AND_CAMERA", 3)
    add(dialogue_and_large_motion, "DIALOGUE_AND_LARGE_MOTION", 2)
    score = sum(item["points"] for item in drivers)
    level = "LOW" if score <= 3 else "MODERATE" if score <= 6 else "HIGH" if score <= 9 else "SPLIT_REQUIRED"
    return {"score": score, "level": level, "drivers": drivers, "recommendation": "PROPOSE_SPLIT" if level == "SPLIT_REQUIRED" else "KEEP_OR_SIMPLIFY", "auto_apply": False}


def diagnose_failures(
    attempts: list[dict[str, Any]], *, remaining_credits: float | None = None,
    credits_per_attempt: float | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    valid = set(_load("reject-reasons.json")["reasons"])
    for attempt in attempts:
        if attempt.get("result") != "REJECTED":
            continue
        for reason in attempt.get("reject_reasons") or []:
            if reason in valid:
                reasons.append(reason)
    sample = sum(1 for item in attempts if item.get("result") == "REJECTED")
    if sample < 2 or not reasons:
        return {"classification": "INSUFFICIENT_EVIDENCE", "confidence": 0.0, "sample_size": sample, "next_action": "REVIEW_MORE_RESULTS"}
    counts = Counter(reasons)
    dominant, count = counts.most_common(1)[0]
    ratio = count / sample
    if ratio >= 2 / 3:
        classification, action = "SYSTEMATIC", "CHANGE_ONE_VARIABLE"
    elif len(counts) >= 2 and max(counts.values()) == 1:
        classification, action = "STOCHASTIC", "BATCH_AND_SELECT"
    else:
        classification, action = "INSUFFICIENT_EVIDENCE", "REVIEW_MORE_RESULTS"
    confidence = round(min(0.9, (0.45 if sample == 2 else 0.6) + abs(ratio - 0.5) * 0.5), 2)
    result: dict[str, Any] = {"classification": classification, "confidence": confidence, "sample_size": sample, "dominant_reason": dominant, "next_action": action}
    if action == "BATCH_AND_SELECT":
        recommended = 2
        if remaining_credits is not None and credits_per_attempt and credits_per_attempt > 0:
            recommended = min(recommended, max(0, int(remaining_credits // credits_per_attempt)))
        result.update({"recommended_attempts": recommended, "lock_prompt": True})
    elif action == "CHANGE_ONE_VARIABLE":
        result.update({"variable_to_change": dominant, "lock_other_variables": True})
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("route")
    cmd.add_argument("intent_type"); cmd.add_argument("duration_seconds", type=float); cmd.add_argument("planned_jobs", type=int)
    cmd.add_argument("--simple-beats", type=int, default=1)
    for flag in ("high_cost", "continuity", "exact_dialogue", "precise_performance", "exact_object_interaction"):
        cmd.add_argument("--" + flag.replace("_", "-"), action="store_true")
    cmd = sub.add_parser("performance")
    cmd.add_argument("emotion"); cmd.add_argument("--visible-channel", action="append", default=[]); cmd.add_argument("--maximum", type=int, default=3)
    cmd = sub.add_parser("camera"); cmd.add_argument("story_function")
    cmd = sub.add_parser("lint"); cmd.add_argument("prompt"); cmd.add_argument("--kind", default="simple"); cmd.add_argument("--load-bearing-element")
    cmd = sub.add_parser("refine"); cmd.add_argument("prompt"); cmd.add_argument("--kind", default="simple"); cmd.add_argument("--load-bearing-element"); cmd.add_argument("--static-fact", action="append", default=[])
    cmd = sub.add_parser("complexity")
    cmd.add_argument("--primary-actions", type=int, default=1); cmd.add_argument("--camera-moves", type=int, default=1); cmd.add_argument("--characters", type=int, default=1); cmd.add_argument("--emotion-changes", type=int, default=0)
    for flag in ("exact_object_interaction", "major_location_change", "offscreen_interaction", "reflection_or_duplicate", "fast_subject_and_camera", "dialogue_and_large_motion"):
        cmd.add_argument("--" + flag.replace("_", "-"), action="store_true")
    cmd = sub.add_parser("diagnose"); cmd.add_argument("attempts_json", type=Path); cmd.add_argument("--remaining-credits", type=float); cmd.add_argument("--credits-per-attempt", type=float)
    return root


def main() -> int:
    args = vars(parser().parse_args()); command = args.pop("command")
    if command == "route": result = route_production(**args)
    elif command == "performance": result = performance_direction(args["emotion"], args["visible_channel"], args["maximum"])
    elif command == "camera": result = camera_alternatives(args["story_function"])
    elif command == "lint": result = lint_prompt(args["prompt"], kind=args["kind"], load_bearing_element=args["load_bearing_element"])
    elif command == "refine": result = refine_prompt(args["prompt"], kind=args["kind"], load_bearing_element=args["load_bearing_element"], static_facts=args["static_fact"])
    elif command == "complexity": result = score_complexity(**args)
    else:
        attempts = json.loads(args["attempts_json"].read_text(encoding="utf-8"))
        result = diagnose_failures(attempts, remaining_credits=args["remaining_credits"], credits_per_attempt=args["credits_per_attempt"])
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
