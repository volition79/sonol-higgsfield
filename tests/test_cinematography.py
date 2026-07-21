from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import cinematography as cine  # noqa: E402


def seedance_snapshot(provider: str = "seedance_2_0") -> dict:
    resolutions = ["480p", "720p"] if provider == "seedance_2_0_mini" else ["480p", "720p", "1080p", "4k"]
    contract = {
        "job_type": provider,
        "params": [
            {"name": "aspect_ratio", "type": "string", "enum": ["auto", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]},
            {"name": "audio_references", "type": "array"},
            {"name": "bitrate_mode", "type": "string", "enum": ["standard", "high"]},
            {"name": "duration", "type": "integer"},
            {"name": "end_image", "type": "object|null"},
            {"name": "generate_audio", "type": "boolean"},
            {"name": "image_references", "type": "array"},
            *([{"name": "mode", "type": "string", "enum": ["std", "fast"]}] if provider == "seedance_2_0" else []),
            {"name": "prompt", "type": "string", "required": True},
            {"name": "resolution", "type": "string", "enum": resolutions},
            {"name": "start_image", "type": "object|null"},
            {"name": "video_references", "type": "array"},
        ],
    }
    return {
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "model_contracts": {provider: contract},
        "contract_fingerprints": {"models": {provider: cine.stable_hash(contract)}, "workflows": {}},
    }


class CinematographyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog, self.genres, self.support = cine.load_knowledge()

    def grammar(self) -> dict:
        return cine.recommend(
            "배신을 알아차리고 고립되는 감정", genre="drama", platform="cinema",
            subject_priority="emotion", provider="seedance_2_0", duration_seconds=5, top_n=1,
        )["recommendations"][0]["grammar"]

    def test_knowledge_is_comprehensive_and_cross_referenced(self) -> None:
        self.assertGreaterEqual(len(self.catalog["techniques"]), 140)
        self.assertEqual(len(self.catalog["categories"]), 15)
        self.assertFalse(cine.validate_knowledge(self.catalog, self.genres, self.support))
        controls = self.support["providers"]["higgsfield_web_camera_controls"]
        self.assertEqual(len(controls["official_controls"]), 65)
        self.assertEqual(len(set(controls["official_controls"])), 65)
        self.assertEqual(controls["named_motion_count_excluding_general"], 64)

    def test_korean_recommendation_is_deterministic_and_explained(self) -> None:
        first = cine.recommend("제품을 고급스럽게 공개", genre="product_ad", platform="reels", provider="seedance_2_0")
        second = cine.recommend("제품을 고급스럽게 공개", genre="product_ad", platform="reels", provider="seedance_2_0")
        self.assertEqual(first, second)
        self.assertEqual(len(first["recommendations"]), 3)
        self.assertTrue(all(item["plain_summary"] and item["grammar"]["why"] for item in first["recommendations"]))
        grammar = first["recommendations"][0]["grammar"]
        categories = {cine.technique_index(self.catalog)[item]["category"] for item in grammar["technique_ids"]}
        self.assertTrue({"blocking", "continuity", "color", "audio", "social"}.issubset(categories))

    def test_conflicting_focus_and_multiple_primary_moves_are_rejected(self) -> None:
        grammar = self.grammar()
        grammar["technique_ids"].extend(["focus.shallow", "focus.deep", "movement.pan"])
        grammar["focus_plan"] = "focus.shallow"
        errors, _ = cine.validate_grammar(grammar, require_complete=False)
        self.assertTrue(any("conflicts" in item for item in errors))
        self.assertTrue(any("one primary camera movement" in item for item in errors))

    def test_seedance_compiles_ordered_soft_prompt(self) -> None:
        grammar = self.grammar()
        compiled = cine.compile_prompt(
            grammar, provider="seedance_2_0", subject="the protagonist", setting="an empty office",
            action="recognizes the betrayal", exit_state="eyes locked on the evidence",
            invariants=["same identity", "same screen direction", "same wardrobe", "ignore this fourth invariant"],
            live_schema=seedance_snapshot(),
            references={"start": "start.png"}, boundary_strategy="scene_reset",
        )
        self.assertIn("End state:", compiled["prompt"])
        self.assertTrue(compiled["prompt"].startswith("1 shot / 5s / auto / single continuous shot"))
        self.assertFalse(compiled["native_params"]["generate_audio"])
        self.assertEqual(compiled["native_params"]["resolution"], "720p")
        self.assertIn("Begin exactly on the provided start image framing", compiled["prompt"])
        self.assertIn("Critical invariants: same identity; same screen direction; same wardrobe", compiled["prompt"])
        self.assertNotIn("ignore this fourth invariant", compiled["prompt"])
        applied = cine.apply_compilation(grammar, compiled)
        self.assertEqual(applied["status"], "VALIDATED")
        self.assertFalse(cine.validate_grammar(applied, require_complete=True, shot_duration=5)[0])

    def test_cinema35_native_fields_are_checked_against_live_schema(self) -> None:
        grammar = self.grammar()
        grammar["technique_ids"] = [item for item in grammar["technique_ids"] if not item.startswith("movement.")]
        grammar["technique_ids"].append("movement.static")
        grammar["movement"] = "movement.static"
        snapshot = {
            "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "workflow_contracts": {"cinematic_studio_video_3_5": {"params": [
                {"name": "camera_style", "enum": ["classic_static", "intimate_observer"]},
                {"name": "light_scheme", "enum": ["soft_cross", "contre_jour", "overhead_fall", "window", "practicals", "silhouette"]},
                {"name": "color_grading", "enum": ["naturalistic_clean", "teal_orange_epic", "cold_steel", "hyper_neon", "bleach_bypass", "classic_bw"]}
            ]}}
        }
        compiled = cine.compile_prompt(
            grammar, provider="cinematic_studio_video_3_5", subject="a woman", setting="a room",
            action="looks up", exit_state="still close-up", live_schema=snapshot,
        )
        self.assertEqual(compiled["native_params"]["camera_style"], "classic_static")
        bad = deepcopy(snapshot)
        bad["workflow_contracts"]["cinematic_studio_video_3_5"]["params"][0]["enum"] = ["intimate_observer"]
        with self.assertRaisesRegex(cine.CinematographyError, "not allowed"):
            cine.compile_prompt(grammar, provider="cinematic_studio_video_3_5", subject="a woman", setting="a room", action="looks up", exit_state="still close-up", live_schema=bad)

    def test_web_and_unverified_mcp_are_not_automation_ready(self) -> None:
        for provider in ("higgsfield_web_camera_controls", "mcp_higgsfield"):
            with self.subTest(provider=provider), self.assertRaisesRegex(cine.CinematographyError, "not automation-ready"):
                cine.compile_prompt(self.grammar(), provider=provider, subject="x", setting="y", action="z", exit_state="q")


if __name__ == "__main__":
    unittest.main()
