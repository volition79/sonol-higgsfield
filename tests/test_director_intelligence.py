from __future__ import annotations

import sys
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import director_intelligence as di  # noqa: E402


class DirectorIntelligenceTests(unittest.TestCase):
    def test_router_selects_official_and_managed_modes_by_intent(self) -> None:
        ad = di.route_production(intent_type="ad", duration_seconds=10, planned_jobs=1)
        self.assertEqual(ad["mode"], "OFFICIAL_WORKFLOW")
        self.assertEqual(ad["official_workflow"], "marketing_studio")
        explainer = di.route_production(intent_type="explainer", duration_seconds=60, planned_jobs=6)
        self.assertEqual(explainer["official_workflow"], "video_explainer")
        precise = di.route_production(
            intent_type="film", duration_seconds=8, planned_jobs=1, exact_dialogue=True
        )
        self.assertEqual(precise["mode"], "CONTROLLED_SHOT")
        self.assertEqual(
            precise["provider_strategy"]["preferred_provider"], "seedance_2_0"
        )
        multishot = di.route_production(
            intent_type="film", duration_seconds=12, planned_jobs=1, simple_beats=3
        )
        self.assertEqual(multishot["mode"], "NATIVE_MULTISHOT")
        serial = di.route_production(
            intent_type="film", duration_seconds=45, planned_jobs=5, continuity=True
        )
        self.assertEqual((serial["mode"], serial["approval_profile"]), ("SERIAL_STORY", "FULL"))
        expensive = di.route_production(
            intent_type="film", duration_seconds=8, planned_jobs=1, high_cost=True
        )
        self.assertEqual(expensive["approval_profile"], "FULL")

    def test_provider_router_uses_cinema_for_load_bearing_direction_without_forcing_it(self) -> None:
        expressive = di.route_production(
            intent_type="film", duration_seconds=8, planned_jobs=1,
            visual_priority="expressive", camera_load_bearing=True,
        )
        strategy = expressive["provider_strategy"]
        self.assertEqual(strategy["preferred_provider"], "cinematic_studio_video_3_5")
        self.assertEqual(strategy["confidence"], "HIGH")
        balanced = di.route_provider()
        self.assertIsNone(balanced["preferred_provider"])
        self.assertTrue(balanced["selection_required"])
        fragile = di.route_provider(
            visual_priority="expressive", camera_load_bearing=True, exact_dialogue=True
        )
        self.assertEqual(fragile["preferred_provider"], "seedance_2_0")

    def test_performance_uses_only_visible_channels_and_at_most_three_cues(self) -> None:
        result = di.performance_direction("shock", ["eyes", "face", "breath", "hands"], 9)
        self.assertEqual(result["status"], "ADVISORY")
        self.assertLessEqual(len(result["selected_cues"]), 3)
        self.assertFalse(any("upper body" in cue for cue in result["selected_cues"]))

    def test_camera_returns_two_unselected_soft_alternatives(self) -> None:
        result = di.camera_alternatives("revelation")
        self.assertEqual(len(result["alternatives"]), 2)
        self.assertEqual(result["support_level"], "prompt_soft")
        self.assertIsNone(result["selected_strategy"])
        cinema = di.camera_alternatives("urgency", "cinematic_studio_video_3_5")
        self.assertEqual(
            cinema["alternatives"][0]["cinema35_camera_style_hint"], "silent_machine"
        )
        self.assertEqual(cinema["alternatives"][0]["movement_support"], "prompt_soft")

    def test_prompt_lint_is_advisory_for_length_but_blocks_real_conflict(self) -> None:
        short = di.lint_prompt("The woman stops at the doorway, dramatic.", load_bearing_element="stops")
        self.assertEqual(short["status"], "PASS_WITH_WARNINGS")
        self.assertTrue(any(item["code"] == "TARGET_RANGE" for item in short["warnings"]))
        conflict = di.lint_prompt(
            "The woman stops. Static camera, then tracking camera follows her.",
            load_bearing_element="stops",
        )
        self.assertEqual(conflict["status"], "BLOCKED")

    def test_prompt_refiner_only_removes_exact_supplied_static_facts(self) -> None:
        result = di.refine_prompt(
            "A red coat fills the frame. The woman opens the door. Soft window light.",
            load_bearing_element="opens the door",
            static_facts=["A red coat fills the frame"],
        )
        self.assertTrue(result["static_redescription_removed"])
        self.assertTrue(result["prompt"].startswith("The woman opens the door"))
        self.assertIn("Soft window light", result["prompt"])

    def test_complexity_proposes_but_never_auto_applies_split(self) -> None:
        result = di.score_complexity(
            primary_actions=3,
            camera_moves=2,
            characters=3,
            reflection_or_duplicate=True,
            dialogue_and_large_motion=True,
        )
        self.assertEqual(result["level"], "SPLIT_REQUIRED")
        self.assertFalse(result["auto_apply"])

    def test_failure_diagnosis_waits_for_evidence_and_changes_one_variable(self) -> None:
        one = di.diagnose_failures(
            [{"result": "REJECTED", "reject_reasons": ["CAMERA_MISS"]}]
        )
        self.assertEqual(one["classification"], "INSUFFICIENT_EVIDENCE")
        repeated = di.diagnose_failures(
            [
                {"result": "REJECTED", "reject_reasons": ["CAMERA_MISS"]},
                {"result": "REJECTED", "reject_reasons": ["CAMERA_MISS"]},
                {"result": "REJECTED", "reject_reasons": ["HAND_DEFORMATION"]},
            ]
        )
        self.assertEqual(repeated["classification"], "SYSTEMATIC")
        self.assertEqual(repeated["next_action"], "CHANGE_ONE_VARIABLE")
        varied = di.diagnose_failures(
            [
                {"result": "REJECTED", "reject_reasons": ["FACE_DEFORMATION"]},
                {"result": "REJECTED", "reject_reasons": ["HAND_DEFORMATION"]},
            ],
            remaining_credits=1,
            credits_per_attempt=2,
        )
        self.assertEqual(varied["classification"], "STOCHASTIC")
        self.assertEqual(varied["recommended_attempts"], 0)


if __name__ == "__main__":
    unittest.main()
