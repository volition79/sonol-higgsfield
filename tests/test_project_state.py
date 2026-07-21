from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_state as state  # noqa: E402
import run_shot  # noqa: E402
import cinematography  # noqa: E402
from test_cinematography import seedance_snapshot  # noqa: E402


class ProductionStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.production = Path(self.temp.name) / "production"
        state.initialize(self.production, "테스트 제작", SKILL / "assets" / "dashboard-template")
        self.live_schema = seedance_snapshot()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_media_file(self, relative: str) -> str:
        path = self.production / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"test-media")
        return relative

    def confirm_requirements(self) -> None:
        values = {
            "purpose": "brand film",
            "core_message": "hello",
            "target_audience": "buyers",
            "target_platform": "web",
            "duration_seconds": 5,
            "aspect_ratio": "16:9",
            "resolution": "720p",
            "frame_rate": 24,
            "language": "ko",
            "story_direction": "cinematic",
            "characters_products_brands": "CHAR_001",
            "copyright_constraints": "owned inputs",
            "approval_method": "dashboard",
            "quality_cost_priority": "balanced",
        }
        for key, value in values.items():
            state.set_requirement(self.production, key, value, "CONFIRMED", "user", "test")

    def lock_and_budget(self) -> None:
        self.confirm_requirements()
        state.lock_requirements(self.production, "user")
        state.lock_story_contract(
            self.production,
            [{"id": "BEAT_001", "description": "The hero discovers the decisive clue"}],
            "user",
        )

    def approve_current_shot_cost(self, credits: float = 2.5, ceiling: float = 3.0) -> None:
        del credits
        state.approve_budget(self.production, ceiling, "user")

    def complete_shot(self, shot_id: str = "SHOT_001", job_id: str = "job-test-001") -> None:
        shots = state.read_json(state.data_dir(self.production) / "shots.json")["items"]
        shot = next(item for item in shots if item["id"] == shot_id)
        if shot["generation"]["status"] == "PLANNED":
            state.transition_generation(self.production, shot_id, "READY", "agent")
        execution = shot["generation"]["execution"]
        state.start_submission_attempt(
            self.production,
            shot_id,
            "agent",
            provider=shot["generation"]["model"],
            mode=execution["mode"],
            execution_fingerprint=execution["fingerprint"],
            match_signature=run_shot.submission_match_signature(execution["mode"], execution["argv"]),
            account_credits_before=100.0,
        )
        state.record_job(self.production, shot_id, job_id, None, "agent")
        state.record_provider_observation(
            self.production,
            shot_id,
            "PROVIDER_COMPLETED",
            "agent",
            raw_status="completed",
            result_available=True,
        )
        state.finalize_provider_completion(self.production, shot_id, "agent")

    def add_locked_asset(self) -> None:
        state.add_asset(self.production, "CHAR_001", "character", "Hero")
        state.update_asset(
            self.production,
            "CHAR_001",
            {"contains_korean_text": True, "ocr_status": "PASSED"},
            "agent",
        )
        state.transition_asset(self.production, "CHAR_001", "INTERNAL_QC_PASSED", "agent")
        state.transition_asset(self.production, "CHAR_001", "USER_REVIEW", "agent")
        state.transition_asset(self.production, "CHAR_001", "USER_APPROVED", "user")
        state.transition_asset(self.production, "CHAR_001", "LOCKED_FOR_VIDEO", "user")

    def add_locked_shot(self) -> None:
        state.add_scene(self.production, "SCENE_001", "Opening", 1)
        state.add_shot(self.production, "SHOT_001", "SCENE_001", "Reveal", 1)
        continuity = {
            key: f"value for {key}"
            for key in state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]["continuity"]
        }
        grammar = cinematography.recommend(
            "주인공이 중요한 단서를 발견한다", genre="drama", provider="seedance_2_0",
            duration_seconds=5, top_n=1,
        )["recommendations"][0]["grammar"]
        seedance_plan = {
            "aspect_ratio": "16:9",
            "resolution": "720p",
            "audio_mode": "native_sfx",
            "sound_design": {
                "dialogue": "none",
                "ambience": "quiet indoor room tone matching the visible office",
                "synchronized_effects": ["soft paper movement when the note is lifted"],
                "music": "none",
                "exclusions": ["no voices", "no unrelated impacts"],
            },
        }
        compiled = cinematography.compile_prompt(
            grammar, provider="seedance_2_0", subject="the hero", setting="a quiet room",
            action="notices the hidden clue", exit_state="the hero holds still in realization",
            invariants=["same face and wardrobe"],
            live_schema=self.live_schema,
            seedance_plan=seedance_plan,
            references={"start": "media/images/SHOT_001_start.png"},
            boundary_strategy="scene_reset",
        )
        contract = state.read_json(state.data_dir(self.production) / "project.json")["story_contract"]
        argv = ["seedance_2_0", "--prompt", compiled["prompt"]]
        for key, value in compiled["native_params"].items():
            argv.extend(("--" + key.replace("_", "-"), json.dumps(value) if not isinstance(value, str) else value))
        state.update_shot(
            self.production, "SHOT_001",
            {
                "duration_seconds": 5,
                "continuity": continuity,
                "boundary": {
                    "strategy": "scene_reset",
                    "inherit_previous_last_frame": False,
                    "planned_keyframe": "media/images/SHOT_001_start.png",
                    "planned_keyframe_role": "start_image",
                    "cut_type": "opening",
                    "reason": "first shot establishes a new scene",
                    "start_image_provenance": {
                        "mode": "initial_composition",
                        "created_after_shot_id": None,
                        "created_at": "2026-07-21T00:00:00+00:00",
                    },
                },
                "references": {"start": "media/images/SHOT_001_start.png"},
                "required_asset_ids": ["CHAR_001"],
                "audio": {
                    "route": "NO_DIALOGUE_NATIVE_SOUND",
                    "has_visible_dialogue": False,
                    "generated_track_policy": "PRESERVE",
                    "final_mix_required": False,
                },
                "model": "seedance_2_0",
                "seedance_plan": seedance_plan,
                "execution": {"mode": "model", "argv": argv},
                "shot_grammar": cinematography.apply_compilation(grammar, compiled),
                "story": {
                    "anchor_beat_ids": ["BEAT_001"] if contract["status"] == "LOCKED" else [],
                    "story_contract_version": contract["version"] if contract["status"] == "LOCKED" else None,
                    "adaptive_revision": 1,
                    "based_on_previous_shot_id": None,
                    "based_on_boundary_analysis_id": None,
                    "adjustment_reason": "initial shot plan",
                    "dialogue_impact": "NOT_APPLICABLE",
                },
            },
            "agent",
        )
        state.record_start_image_review(
            self.production,
            "SHOT_001",
            {
                "final_first_frame": True,
                "aspect_ratio_match": True,
                "no_collage_or_labels": True,
                "key_subject_readable": True,
                "action_compatible": True,
                "off_frame_reveal_risk": "LOW",
            },
            "PASSED",
            "agent",
            "start image is ready for the intended first motion",
        )
        state.transition_shot_approval(self.production, "SHOT_001", "INTERNAL_QC_PASSED", "agent")
        state.transition_shot_approval(self.production, "SHOT_001", "USER_REVIEW", "agent")
        state.transition_shot_approval(self.production, "SHOT_001", "USER_APPROVED", "user")
        state.transition_shot_approval(self.production, "SHOT_001", "LOCKED_FOR_VIDEO", "user")

    def test_initialization_creates_split_state_and_dashboard(self) -> None:
        self.assertFalse(state.validate(self.production))
        for name in state.DATA_FILES:
            self.assertTrue((self.production / "data" / name).is_file())
        self.assertTrue((self.production / "dashboard" / "project-data.js").is_file())
        state.add_scene(self.production, "SCENE_C35", "Cinema route", 1)
        state.add_shot(self.production, "SHOT_C35", "SCENE_C35", "Expressive move", 1)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["cinema35_plan"]["start_frame_behavior"], "match_then_release")
        self.assertEqual(shot["cinema35_plan"]["audio_mode"], "none")

    def test_requirements_require_user_and_all_confirmed(self) -> None:
        with self.assertRaisesRegex(state.StateError, "only the user"):
            state.lock_requirements(self.production, "agent")
        with self.assertRaisesRegex(state.StateError, "not confirmed"):
            state.lock_requirements(self.production, "user")
        self.confirm_requirements()
        state.lock_requirements(self.production, "user")
        project = state.read_json(state.data_dir(self.production) / "project.json")
        self.assertEqual(project["requirements_lock"]["status"], "LOCKED")
        self.assertEqual(project["project"]["aspect_ratio"], "16:9")

    def test_budget_approval_requires_locked_requirements_and_user(self) -> None:
        with self.assertRaisesRegex(state.StateError, "requirements must be locked"):
            state.approve_budget(self.production, 2, "user")
        self.confirm_requirements()
        state.lock_requirements(self.production, "user")
        with self.assertRaisesRegex(state.StateError, "only the user"):
            state.approve_budget(self.production, 2, "agent")
        state.approve_budget(self.production, 2, "user")
        approval = state.read_json(state.data_dir(self.production) / "project.json")["cost_approval"]
        self.assertEqual(approval["mode"], "PROJECT_CEILING")
        self.assertTrue(approval["unpriced_job_risk_acknowledged"])

    def test_light_policy_can_approve_spend_without_full_requirement_lock(self) -> None:
        state.set_production_policy(
            self.production,
            "NATIVE_MULTISHOT",
            "LIGHT",
            "agent",
            "one small native clip",
        )
        state.approve_budget(self.production, 2, "user")
        project = state.read_json(state.data_dir(self.production) / "project.json")
        self.assertEqual(project["requirements_lock"]["status"], "UNLOCKED")
        self.assertEqual(project["cost_approval"]["status"], "APPROVED")

    def test_story_anchor_contract_requires_user_and_persists_version(self) -> None:
        beats = [{"id": "BEAT_001", "description": "The irreversible discovery"}]
        with self.assertRaisesRegex(state.StateError, "only the user"):
            state.lock_story_contract(self.production, beats, "agent")
        state.lock_story_contract(self.production, beats, "user")
        contract = state.read_json(state.data_dir(self.production) / "project.json")["story_contract"]
        self.assertEqual(contract["status"], "LOCKED")
        self.assertEqual(contract["version"], 1)
        self.assertEqual(contract["anchor_beats"], beats)

    def test_korean_asset_ocr_and_version_specific_approval(self) -> None:
        state.add_asset(self.production, "TEXT_001", "graphic", "Title")
        state.update_asset(self.production, "TEXT_001", {"contains_korean_text": True}, "agent")
        state.transition_asset(self.production, "TEXT_001", "INTERNAL_QC_PASSED", "agent")
        state.transition_asset(self.production, "TEXT_001", "USER_REVIEW", "agent")
        with self.assertRaisesRegex(state.StateError, "only the user"):
            state.transition_asset(self.production, "TEXT_001", "USER_APPROVED", "agent")
        state.transition_asset(self.production, "TEXT_001", "USER_APPROVED", "user")
        with self.assertRaisesRegex(state.StateError, "pass OCR"):
            state.transition_asset(self.production, "TEXT_001", "LOCKED_FOR_VIDEO", "user")
        state.update_asset(self.production, "TEXT_001", {"ocr_status": "PASSED", "label": "Changed"}, "agent")
        asset = state.read_json(state.data_dir(self.production) / "assets.json")["items"][0]
        self.assertEqual(asset["status"], "DRAFT")
        self.assertEqual(asset["version"], 2)
        self.assertIsNone(asset["approved_by"])

    def test_generation_and_final_qc_gates(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        self.complete_shot()
        with self.assertRaisesRegex(state.StateError, "start-frame QC"):
            state.transition_generation(self.production, "SHOT_001", "FINAL_COMPLETE", "agent")
        for check in ("technical", "transcript", "lip_sync", "visual", "continuity", "cinematography"):
            state.set_qc(self.production, "SHOT_001", check, "PASSED", "agent")
        state.set_qc(self.production, "SHOT_001", "korean_pronunciation", "NOT_APPLICABLE", "agent")
        with self.assertRaisesRegex(state.StateError, "only the user"):
            state.set_qc(self.production, "SHOT_001", "user_review", "PASSED", "agent")
        state.set_qc(self.production, "SHOT_001", "user_review", "PASSED", "user")
        rendered_first = self.create_media_file("media/images/SHOT_001_rendered_first.png")
        boundary_frame = self.create_media_file("media/images/SHOT_001_boundary.png")
        state.record_start_frame_qc(self.production, "SHOT_001", rendered_first, "PASSED", "agent")
        state.record_boundary_analysis(
            self.production,
            "SHOT_001",
            boundary_frame,
            {key: f"observed {key}" for key in state.BOUNDARY_OBSERVATION_FIELDS},
            {
                "selection_method": "lowest_ffmpeg_blurdetect_mean",
                "window_seconds": 0.5,
                "selected_timestamp": 4.85,
                "selected_blur_score": 2.1,
                "candidates": [
                    {"timestamp": 4.7, "blur_score": 2.5},
                    {"timestamp": 4.85, "blur_score": 2.1},
                ],
            },
            "continue from the held clue",
            "agent",
        )
        state.transition_generation(self.production, "SHOT_001", "FINAL_COMPLETE", "agent")
        self.assertFalse(state.validate(self.production))
        self.assertEqual(state.aggregate(self.production)["summary"]["progress_percent"], 100.0)

    def test_start_image_review_is_a_real_preflight_gate(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        reviewed = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(reviewed["start_image_review"]["start_image_path"], "media/images/SHOT_001_start.png")
        state.update_shot(self.production, "SHOT_001", {"references": {"start": "revised.png"}}, "agent")
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["start_image_review"]["status"], "PENDING")
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        with self.assertRaisesRegex(state.StateError, "required preparation review"):
            state.transition_generation(self.production, "SHOT_001", "SUBMITTING", "agent")
        assessment = {
            "final_first_frame": True,
            "aspect_ratio_match": True,
            "no_collage_or_labels": True,
            "key_subject_readable": True,
            "action_compatible": True,
            "off_frame_reveal_risk": "HIGH",
        }
        with self.assertRaisesRegex(state.StateError, "high off-frame reveal risk"):
            state.record_start_image_review(self.production, "SHOT_001", assessment, "PASSED", "agent")

    def test_generation_is_blocked_without_locked_asset(self) -> None:
        self.lock_and_budget()
        state.add_asset(self.production, "CHAR_001", "character", "Hero")
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        with self.assertRaisesRegex(state.StateError, "required asset is not locked"):
            state.transition_generation(self.production, "SHOT_001", "SUBMITTING", "agent")

    def test_continuous_boundary_requires_previous_frame_as_start_image(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        state.add_scene(self.production, "SCENE_000", "Prelude", 0)
        state.add_shot(self.production, "SHOT_000", "SCENE_000", "Approach", 0)
        shots_path = state.data_dir(self.production) / "shots.json"
        shots = state.read_json(shots_path)
        previous = next(item for item in shots["items"] if item["id"] == "SHOT_000")
        previous["generation"]["status"] = "GENERATED"
        previous["qc"]["user_review"] = "PASSED"
        previous["start_frame_qc"]["status"] = "PASSED"
        previous["boundary_analysis"].update(
            {
                "status": "COMPLETE",
                "analysis_id": "BA_SHOT_000_V1",
                "frame_path": "media/images/SHOT_000_boundary.png",
            }
        )
        state.atomic_write_json(shots_path, shots)
        self.add_locked_shot()
        with self.assertRaisesRegex(state.StateError, "previous_shot_id"):
            state.set_boundary(
                self.production,
                "SHOT_001",
                "continuous_match",
                "agent",
                reason="same action and camera axis continue",
            )
        state.set_boundary(
            self.production,
            "SHOT_001",
            "continuous_match",
            "agent",
            reason="same action and camera axis continue",
            previous_shot_id="SHOT_000",
            previous_frame="media/images/SHOT_000_boundary.png",
            planned_keyframe="media/images/SHOT_001_keyframe.png",
        )
        shot = next(
            item
            for item in state.read_json(state.data_dir(self.production) / "shots.json")["items"]
            if item["id"] == "SHOT_001"
        )
        self.assertEqual(state.boundary_plan_errors(shot), [])
        self.assertEqual(shot["references"]["start"], "media/images/SHOT_000_boundary.png")
        self.assertNotIn("media/images/SHOT_001_keyframe.png", shot["references"].get("images", []))
        self.assertEqual(shot["boundary"]["planned_keyframe_role"], "analysis_only")

    def test_motivated_transition_defaults_to_prompt_only_without_end_image(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        state.add_scene(self.production, "SCENE_000", "Prelude", 0)
        state.add_shot(self.production, "SHOT_000", "SCENE_000", "Approach", 0)
        shots_path = state.data_dir(self.production) / "shots.json"
        shots = state.read_json(shots_path)
        previous = next(item for item in shots["items"] if item["id"] == "SHOT_000")
        previous["generation"]["status"] = "GENERATED"
        previous["qc"]["user_review"] = "PASSED"
        previous["start_frame_qc"]["status"] = "PASSED"
        previous["boundary_analysis"].update(
            {"status": "COMPLETE", "frame_path": "media/images/SHOT_000_boundary.png"}
        )
        state.atomic_write_json(shots_path, shots)
        self.add_locked_shot()
        state.set_boundary(
            self.production,
            "SHOT_001",
            "motivated_transition",
            "agent",
            reason="a slow push changes the composition without requiring an exact landing frame",
            previous_shot_id="SHOT_000",
            previous_frame="media/images/SHOT_000_boundary.png",
        )
        shot = next(
            item for item in state.read_json(shots_path)["items"] if item["id"] == "SHOT_001"
        )
        self.assertEqual(shot["seedance_plan"]["image_input_policy"]["mode"], "start_only")
        self.assertIsNone(shot["references"].get("end"))
        self.assertEqual(shot["boundary"]["planned_keyframe_role"], "none")
        self.assertEqual(state.boundary_plan_errors(shot), [])

    def test_motivated_transition_can_use_new_start_and_optional_exact_end(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        state.add_scene(self.production, "SCENE_000", "Prelude", 0)
        state.add_shot(self.production, "SHOT_000", "SCENE_000", "Approach", 0)
        shots_path = state.data_dir(self.production) / "shots.json"
        shots = state.read_json(shots_path)
        previous = next(item for item in shots["items"] if item["id"] == "SHOT_000")
        previous["generation"]["status"] = "GENERATED"
        previous["qc"]["user_review"] = "PASSED"
        state.atomic_write_json(shots_path, shots)
        self.add_locked_shot()
        state.set_boundary(
            self.production,
            "SHOT_001",
            "motivated_transition",
            "agent",
            reason="new angle must land on the approved doorway composition",
            planned_keyframe="media/images/SHOT_001_start.png",
            end_keyframe="media/images/SHOT_001_end.png",
        )
        shot = next(item for item in state.read_json(shots_path)["items"] if item["id"] == "SHOT_001")
        self.assertFalse(shot["boundary"]["inherit_previous_last_frame"])
        self.assertEqual(shot["references"]["start"], "media/images/SHOT_001_start.png")
        self.assertEqual(shot["references"]["end"], "media/images/SHOT_001_end.png")
        self.assertEqual(shot["seedance_plan"]["image_input_policy"]["mode"], "start_end_transition")
        self.assertEqual(state.boundary_plan_errors(shot), [])

    def test_light_policy_skips_full_requirements_board_assets_and_continuity_gates(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.set_production_policy(
            self.production,
            "NATIVE_MULTISHOT",
            "LIGHT",
            "agent",
            "one low-cost native clip with simple beats",
        )
        project_path = state.data_dir(self.production) / "project.json"
        project = state.read_json(project_path)
        project["requirements_lock"]["status"] = "UNLOCKED"
        state.atomic_write_json(project_path, project)
        assets_path = state.data_dir(self.production) / "assets.json"
        assets = state.read_json(assets_path)
        assets["items"][0]["status"] = "DRAFT"
        state.atomic_write_json(assets_path, assets)
        shots_path = state.data_dir(self.production) / "shots.json"
        shots = state.read_json(shots_path)
        shots["items"][0]["approval_status"] = "DRAFT"
        shots["items"][0]["continuity"] = {key: None for key in shots["items"][0]["continuity"]}
        state.atomic_write_json(shots_path, shots)
        shot = state.read_json(shots_path)["items"][0]
        errors = state.shot_gate_errors(state.load_all(self.production), shot)
        self.assertFalse(any("requirements" in item for item in errors))
        self.assertFalse(any("shot board" in item for item in errors))
        self.assertFalse(any("required asset" in item for item in errors))
        self.assertFalse(any("continuity context" in item for item in errors))

    def test_editorial_cut_requires_acceptance_and_jit_start_not_boundary_analysis(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        self.complete_shot()
        state.set_qc(self.production, "SHOT_001", "user_review", "PASSED", "user")
        state.add_shot(self.production, "SHOT_002", "SCENE_001", "Reaction", 2)
        state.set_boundary(
            self.production,
            "SHOT_002",
            "editorial_cut",
            "agent",
            reason="reverse angle after the discovery",
            planned_keyframe="media/images/SHOT_002_start.png",
        )
        state.set_adaptive_story(
            self.production,
            "SHOT_002",
            ["BEAT_001"],
            "stage the reaction from the accepted hand position",
            "NOT_APPLICABLE",
            "agent",
            "SHOT_001",
        )
        shot = next(
            item
            for item in state.read_json(state.data_dir(self.production) / "shots.json")["items"]
            if item["id"] == "SHOT_002"
        )
        self.assertEqual(state.sequential_adaptation_errors(state.load_all(self.production), shot), [])
        self.assertIsNone(shot["story"]["based_on_boundary_analysis_id"])
        shot["boundary"]["start_image_provenance"]["created_after_shot_id"] = "SHOT_000"
        self.assertTrue(any("just in time" in item for item in state.sequential_adaptation_errors(state.load_all(self.production), shot)))

    def test_director_may_select_a_persisted_nonsharpest_boundary_with_reason(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        self.complete_shot()
        state.set_qc(self.production, "SHOT_001", "user_review", "PASSED", "user")
        sharper = self.create_media_file("media/images/candidate_00.png")
        better_pose = self.create_media_file("media/images/candidate_01.png")
        state.record_boundary_analysis(
            self.production,
            "SHOT_001",
            better_pose,
            {key: f"observed {key}" for key in state.BOUNDARY_OBSERVATION_FIELDS},
            {
                "selection_method": "director_selected_candidate",
                "window_seconds": 0.5,
                "selected_timestamp": 4.8,
                "selected_blur_score": 2.2,
                "selected_candidate_path": better_pose,
                "selection_reason": "cleaner hand pose and stronger eyeline despite slightly more blur",
                "candidates": [
                    {"timestamp": 4.7, "blur_score": 1.9, "path": sharper},
                    {"timestamp": 4.8, "blur_score": 2.2, "path": better_pose},
                ],
            },
            "continue from the readable hand pose",
            "agent",
        )
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        technical = shot["boundary_analysis"]["technical"]
        self.assertEqual(technical["selection_method"], "director_selected_candidate")
        self.assertEqual(technical["selected_candidate_path"], better_pose)
        self.assertIn("hand pose", technical["selection_reason"])

    def test_visible_dialogue_requires_v3_reference_and_preserved_native_audio(self) -> None:
        self.add_locked_asset()
        self.add_locked_shot()
        state.update_shot(
            self.production,
            "SHOT_001",
            {
                "audio": {
                    "route": "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO",
                    "has_visible_dialogue": True,
                    "voice_provider": "elevenlabs",
                    "voice_model": "eleven_v3",
                    "dialogue_reference_path": "media/audio/dialogue.wav",
                    "dialogue_reference_sha256": "sha256:" + "a" * 64,
                    "generated_track_policy": "PRESERVE",
                    "final_mix_required": False,
                },
                "references": {"audios": ["media/audio/dialogue.wav"], "start": "hero.png"},
                "seedance_plan": {
                    "audio_mode": "audio_reference",
                    "sound_design": {
                        "dialogue": "one Korean speaker follows the supplied reference exactly",
                        "ambience": "light rooftop wind and distant city traffic",
                        "synchronized_effects": ["soft glass contact at the visible touch"],
                        "music": "none",
                        "exclusions": ["no narration", "no extra voices"],
                    },
                },
            },
            "agent",
        )
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(state.audio_plan_errors(shot), [])
        shot["audio"]["dialogue_reference_sha256"] = None
        self.assertTrue(any("SHA-256" in item for item in state.audio_plan_errors(shot)))
        shot["audio"]["dialogue_reference_sha256"] = "sha256:" + "a" * 64
        shot["audio"]["generated_track_policy"] = "DISCARD"
        self.assertTrue(any("preserve" in item for item in state.audio_plan_errors(shot)))

    def test_no_dialogue_native_sound_requires_complete_brief_and_preservation(self) -> None:
        self.add_locked_asset()
        self.add_locked_shot()
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(state.audio_plan_errors(shot), [])
        shot["seedance_plan"]["sound_design"]["ambience"] = None
        self.assertTrue(any("sound_design.ambience" in item for item in state.audio_plan_errors(shot)))
        shot["seedance_plan"]["sound_design"]["ambience"] = "quiet room tone"
        shot["seedance_plan"]["sound_design"]["dialogue"] = "a man says hello"
        self.assertTrue(any("explicitly say none" in item for item in state.audio_plan_errors(shot)))
        shot["seedance_plan"]["sound_design"]["dialogue"] = "none"
        shot["audio"]["generated_track_policy"] = "DISCARD"
        self.assertTrue(any("preserve" in item for item in state.audio_plan_errors(shot)))

    def test_offscreen_narration_requires_a_fingerprinted_master(self) -> None:
        self.add_locked_asset()
        self.add_locked_shot()
        state.update_shot(
            self.production,
            "SHOT_001",
            {
                "audio": {
                    "route": "OFFSCREEN_NARRATION",
                    "has_visible_dialogue": False,
                    "narration_master_path": "media/audio/narration.wav",
                    "narration_master_sha256": "sha256:" + "b" * 64,
                    "generated_track_policy": "NOT_GENERATED",
                    "final_mix_required": True,
                },
                "seedance_plan": {"audio_mode": "post_only"},
            },
            "agent",
        )
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(state.audio_plan_errors(shot), [])
        shot["audio"]["narration_master_sha256"] = "invalid"
        self.assertTrue(any("SHA-256" in item for item in state.audio_plan_errors(shot)))

    def test_guarded_paid_runner_uses_budget_without_live_quote(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        script = Path(self.temp.name) / "fake_higgsfield.py"
        contract = self.live_schema["model_contracts"]["seedance_2_0"]
        script.write_text(
            "#!/usr/bin/env python3\nimport json,sys\n"
            f"contract={json.dumps(contract)!r}\n"
            "assert 'cost' not in sys.argv, 'live cost endpoint must not be called'\n"
            "if 'account' in sys.argv: print(json.dumps({'credits': 100}))\n"
            "elif 'model' in sys.argv and 'get' in sys.argv: print(contract)\n"
            "elif 'create' in sys.argv: print(json.dumps([{'id':'job-001','status':'queued'}]))\n"
            "elif 'generate' in sys.argv and 'get' in sys.argv: "
            "print(json.dumps({'id':'job-001','status':'completed','credits':2.5,'result_url':'https://private.invalid/result'}))\n"
            "else: raise SystemExit(3)\n",
            encoding="utf-8",
        )
        if os.name == "nt":
            fake = Path(self.temp.name) / "fake-higgsfield.cmd"
            fake.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
        else:
            fake = script
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        result = run_shot.run_paid(self.production, "SHOT_001", str(fake), False, 30)
        self.assertEqual(result["job_id"], "job-001")
        self.assertFalse(result["actual_credits_recorded"])
        self.assertEqual(result["status"], "QUEUED")
        reconciled = run_shot.reconcile(
            self.production,
            "SHOT_001",
            str(fake),
            job_id=None,
            wait=False,
            timeout=30,
            credits=None,
        )
        self.assertEqual(reconciled["status"], "GENERATED")
        self.assertTrue(reconciled["actual_credits_recorded"])
        aggregate = state.aggregate(self.production)
        self.assertEqual(aggregate["shots"][0]["generation"]["status"], "GENERATED")
        self.assertEqual(aggregate["costs"]["actual"]["credits"], 2.5)

    def test_web_ui_job_reconcile_records_surface_provider_result_and_cost(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost(ceiling=100)
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        job = {
            "id": "web-cinema-job",
            "job_type": "seedance_2_0",
            "status": "completed",
            "credits": 80,
            "result_url": "https://private.invalid/web-cinema-result",
        }

        def provider(command: list[str], timeout: int):
            del timeout
            if "account" in command:
                return {"credits": 1200}
            return job

        result_path = "media/videos/SHOT_001_web.mp4"
        with patch.object(run_shot, "cli_json", provider):
            reconciled = run_shot.reconcile(
                self.production,
                "SHOT_001",
                "/fake/higgsfield",
                job_id="web-cinema-job",
                wait=False,
                timeout=30,
                credits=80,
                submission_surface="web_ui",
                result_path=result_path,
            )
        self.assertEqual(reconciled["status"], "GENERATED")
        self.assertEqual(reconciled["submission_surface"], "web_ui")
        self.assertEqual(reconciled["result_path"], result_path)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        attempt = shot["generation"]["attempts"][-1]
        self.assertEqual(attempt["provider"], "seedance_2_0")
        self.assertEqual(attempt["submission_surface"], "web_ui")
        self.assertEqual(attempt["result_path"], result_path)
        self.assertEqual(state.aggregate(self.production)["costs"]["actual"]["credits"], 80)

        annotated = run_shot.reconcile(
            self.production,
            "SHOT_001",
            "/fake/higgsfield",
            job_id="web-cinema-job",
            wait=False,
            timeout=30,
            credits=None,
            submission_surface="web_ui",
            result_path=result_path,
        )
        self.assertTrue(annotated["already_reconciled"])
        self.assertEqual(len(shot["generation"]["attempts"]), 1)

    def test_guarded_paid_runner_rejects_exhausted_project_ceiling(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost(ceiling=2)
        state.record_actual_cost(self.production, "PRIOR", 2, "agent", "job-prior")
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        with self.assertRaisesRegex(state.StateError, "ceiling is exhausted"):
            run_shot.run_paid(self.production, "SHOT_001", "/provider/must/not/run", False, 30)

    def test_provider_job_id_accepts_only_known_envelopes(self) -> None:
        # The live hf CLI returns job objects (or a list of them) whose
        # identifier key is a plain "id". Some releases instead return a
        # one-item UUID array, which is accepted without opening parsing to
        # arbitrary string payloads.
        job_uuid = "1f5cc4f1-98bd-42de-92dd-27a9f704cc53"
        self.assertEqual(run_shot.provider_job_id({"id": "job-001"}), "job-001")
        self.assertEqual(run_shot.provider_job_id([{"id": "job-001"}]), "job-001")
        self.assertEqual(run_shot.provider_job_id({"data": {"job_id": "job-001"}}), "job-001")
        self.assertEqual(run_shot.provider_job_id([job_uuid]), job_uuid)
        self.assertIsNone(run_shot.provider_job_id("job-001"))
        self.assertIsNone(run_shot.provider_job_id(["job-001"]))
        self.assertIsNone(run_shot.provider_job_id([job_uuid, {"id": "job-002"}]))
        self.assertIsNone(run_shot.provider_job_id({"credits": 5}))

    def test_provider_status_incident_fixture_is_fail_open_for_unknown_states(self) -> None:
        fixture = json.loads(
            (SKILL / "tests" / "fixtures" / "provider_lifecycle_incidents.json").read_text(encoding="utf-8")
        )
        for item in fixture["provider_status_cases"]:
            with self.subTest(raw=item["raw"]):
                self.assertEqual(run_shot.normalize_provider_status(item["raw"]), item["expected"])

    def test_interrupted_submission_becomes_reconcilable_not_failed_or_generating(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        contract = self.live_schema["model_contracts"]["seedance_2_0"]

        def interrupted(command: list[str], timeout: int):
            del timeout
            if "model" in command and "get" in command:
                return contract
            if "account" in command:
                return {"credits": 100}
            raise KeyboardInterrupt()

        with patch.object(run_shot, "cli_json", interrupted), self.assertRaises(KeyboardInterrupt):
            run_shot.run_paid(self.production, "SHOT_001", "/fake/higgsfield", False, 30)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["generation"]["status"], "SUBMISSION_AMBIGUOUS")
        self.assertIsNone(shot["generation"]["job_id"])
        self.assertTrue(state.unresolved_submission(shot))
        with self.assertRaisesRegex(state.StateError, "reconciled"):
            state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        state.resolve_submission_ambiguity(
            self.production,
            "SHOT_001",
            "NOT_SUBMITTED",
            "agent",
            "provider history and account activity confirm no remote job",
        )
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")

    def test_ambiguous_submission_can_recover_one_matching_history_job(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        execution = shot["generation"]["execution"]
        signature = run_shot.submission_match_signature(execution["mode"], execution["argv"])
        state.start_submission_attempt(
            self.production,
            "SHOT_001",
            "agent",
            provider="seedance_2_0",
            mode=execution["mode"],
            execution_fingerprint=execution["fingerprint"],
            match_signature=signature,
            account_credits_before=100,
        )
        state.mark_submission_ambiguous(self.production, "SHOT_001", "agent", "test interruption")
        _, flags = run_shot.execution_contract.parse_flags(execution["argv"])
        candidate_params = {"prompt": flags["prompt"], **signature["params"]}
        candidate = {
            "id": "recovered-job",
            "job_type": "seedance_2_0",
            "created_at": state.utc_now(),
            "status": "completed",
            "params": candidate_params,
            "result_url": "https://private.invalid/result",
        }

        def provider(command: list[str], timeout: int):
            del timeout
            if "list" in command:
                return [candidate]
            if "account" in command:
                return {"credits": 95}
            return candidate

        with patch.object(run_shot, "cli_json", provider):
            recovered = run_shot.reconcile(
                self.production,
                "SHOT_001",
                "/fake/higgsfield",
                job_id=None,
                wait=False,
                timeout=30,
                credits=None,
            )
        self.assertEqual(recovered["job_id"], "recovered-job")
        self.assertEqual(recovered["status"], "GENERATED")
        self.assertTrue(recovered["cost_reconciliation_required"])
        self.assertEqual(recovered["balance_delta_candidate"], 5)

    def test_interrupted_observation_keeps_known_job_reconcilable(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        execution = shot["generation"]["execution"]
        state.start_submission_attempt(
            self.production,
            "SHOT_001",
            "agent",
            provider="seedance_2_0",
            mode=execution["mode"],
            execution_fingerprint=execution["fingerprint"],
            match_signature=run_shot.submission_match_signature(execution["mode"], execution["argv"]),
            account_credits_before=100,
        )
        state.record_job(self.production, "SHOT_001", "known-job", None, "agent")
        with patch.object(run_shot, "cli_json", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            run_shot.reconcile(
                self.production,
                "SHOT_001",
                "/fake/higgsfield",
                job_id=None,
                wait=True,
                timeout=30,
                credits=None,
            )
        current = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(current["generation"]["status"], "REMOTE_UNKNOWN")
        self.assertEqual(current["generation"]["job_id"], "known-job")
        self.assertTrue(state.unresolved_submission(current))

    def test_ambiguous_history_never_guesses_between_multiple_candidates(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        execution = shot["generation"]["execution"]
        signature = run_shot.submission_match_signature(execution["mode"], execution["argv"])
        state.start_submission_attempt(
            self.production,
            "SHOT_001",
            "agent",
            provider="seedance_2_0",
            mode=execution["mode"],
            execution_fingerprint=execution["fingerprint"],
            match_signature=signature,
            account_credits_before=100,
        )
        state.mark_submission_ambiguous(self.production, "SHOT_001", "agent", "test interruption")
        _, flags = run_shot.execution_contract.parse_flags(execution["argv"])
        common = {
            "job_type": "seedance_2_0",
            "created_at": state.utc_now(),
            "status": "queued",
            "params": {"prompt": flags["prompt"], **signature["params"]},
        }
        listing = [common | {"id": "candidate-a"}, common | {"id": "candidate-b"}]
        with patch.object(run_shot, "cli_json", return_value=listing):
            result = run_shot.reconcile(
                self.production,
                "SHOT_001",
                "/fake/higgsfield",
                job_id=None,
                wait=False,
                timeout=30,
                credits=None,
            )
        self.assertEqual(result["status"], "SUBMISSION_AMBIGUOUS")
        self.assertEqual(result["candidate_job_ids"], ["candidate-a", "candidate-b"])
        current = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertIsNone(current["generation"]["job_id"])

    def test_pending_cost_is_an_explicit_override_not_a_permanent_deadlock(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.require_cost_reconciliation(
            self.production,
            "PRIOR",
            "agent",
            job_id="prior-job",
            reported_credits=None,
            reason="provider omitted credits",
        )
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        with self.assertRaisesRegex(state.StateError, "acknowledge-pending-costs"):
            run_shot.run_paid(self.production, "SHOT_001", "/fake/higgsfield", False, 30)
        contract = self.live_schema["model_contracts"]["seedance_2_0"]

        def provider(command: list[str], timeout: int):
            del timeout
            if "model" in command and "get" in command:
                return contract
            if "account" in command:
                return {"credits": 100}
            return [{"id": "new-job", "status": "queued"}]

        with patch.object(run_shot, "cli_json", provider):
            submitted = run_shot.run_paid(
                self.production,
                "SHOT_001",
                "/fake/higgsfield",
                False,
                30,
                acknowledge_pending_costs=True,
            )
        self.assertEqual(submitted["status"], "QUEUED")

    def test_post_submit_gate_drift_never_blocks_provider_truth_or_actual_cost(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost(ceiling=3)
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        execution = shot["generation"]["execution"]
        state.start_submission_attempt(
            self.production,
            "SHOT_001",
            "agent",
            provider="seedance_2_0",
            mode=execution["mode"],
            execution_fingerprint=execution["fingerprint"],
            match_signature=run_shot.submission_match_signature(execution["mode"], execution["argv"]),
            account_credits_before=100,
        )
        state.record_job(self.production, "SHOT_001", "already-paid-job", None, "agent")
        shots_path = state.data_dir(self.production) / "shots.json"
        shots = state.read_json(shots_path)
        shots["items"][0]["audio"]["generated_track_policy"] = "DISCARD"
        state.atomic_write_json(shots_path, shots)
        self.assertTrue(state.shot_gate_errors(state.load_all(self.production), shots["items"][0]))
        state.record_provider_observation(
            self.production,
            "SHOT_001",
            "PROVIDER_COMPLETED",
            "agent",
            raw_status="completed",
            result_available=True,
        )
        state.finalize_provider_completion(self.production, "SHOT_001", "agent")
        state.record_actual_cost(self.production, "SHOT_001", 5, "agent", "already-paid-job")
        aggregate = state.aggregate(self.production)
        self.assertEqual(aggregate["shots"][0]["generation"]["status"], "GENERATED")
        self.assertEqual(aggregate["costs"]["actual"]["credits"], 5)
        self.assertTrue(aggregate["costs"]["actual"]["ceiling_breach"])

    def test_v7_inflight_job_without_id_migrates_to_submission_ambiguous(self) -> None:
        state.add_scene(self.production, "SCENE_001", "Opening", 1)
        state.add_shot(self.production, "SHOT_001", "SCENE_001", "Interrupted", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 7
            if name == "shots.json":
                document["items"][0]["generation"]["status"] = "GENERATING"
                document["items"][0]["generation"].pop("active_attempt_id", None)
                document["items"][0]["generation"].pop("attempts", None)
            if name == "costs.json":
                document["actual"].pop("ceiling_breach", None)
            state.atomic_write_json(path, document, backup=False)
        state.migrate(self.production)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["generation"]["status"], "SUBMISSION_AMBIGUOUS")
        self.assertTrue(shot["generation"]["active_attempt_id"])
        self.assertEqual(shot["generation"]["attempts"][0]["resolution"], "PENDING")

    def test_v7_qc_failed_job_migrates_as_completed_evidence(self) -> None:
        state.add_scene(self.production, "SCENE_001", "Opening", 1)
        state.add_shot(self.production, "SHOT_001", "SCENE_001", "Rejected render", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 7
            if name == "shots.json":
                generation = document["items"][0]["generation"]
                generation["status"] = "QC_FAILED"
                generation["job_id"] = "completed-before-qc"
                generation.pop("active_attempt_id", None)
                generation.pop("attempts", None)
            if name == "costs.json":
                document["actual"].pop("ceiling_breach", None)
            state.atomic_write_json(path, document, backup=False)
        state.migrate(self.production)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["generation"]["status"], "QC_FAILED")
        self.assertIsNone(shot["generation"]["active_attempt_id"])
        self.assertEqual(shot["generation"]["attempts"][0]["remote_status"], "COMPLETED")
        self.assertEqual(shot["generation"]["attempts"][0]["resolution"], "RECORDED")

    def test_requirement_change_unlocks_requirements_but_preserves_ceiling(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.set_requirement(self.production, "duration_seconds", 6, "CONFIRMED", "user", "revision")
        project = state.read_json(state.data_dir(self.production) / "project.json")
        costs = state.read_json(state.data_dir(self.production) / "costs.json")
        self.assertEqual(project["requirements_lock"]["status"], "UNLOCKED")
        self.assertEqual(project["cost_approval"]["status"], "APPROVED")
        self.assertEqual(costs["reference_estimates"]["status"], "STALE")

    def test_execution_change_invalidates_reference_only_not_ceiling(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.update_shot(self.production, "SHOT_001", {"duration_seconds": 6}, "agent")
        project = state.read_json(state.data_dir(self.production) / "project.json")
        costs = state.read_json(state.data_dir(self.production) / "costs.json")
        self.assertEqual(project["cost_approval"]["status"], "APPROVED")
        self.assertEqual(costs["reference_estimates"]["status"], "STALE")

    def test_actual_cost_records_truth_and_flags_ceiling_breach(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.record_actual_cost(self.production, "SHOT_001", 2.0, "agent", "job-1")
        state.record_actual_cost(self.production, "SHOT_002", 2.0, "agent", "job-2")
        costs = state.read_json(state.data_dir(self.production) / "costs.json")
        self.assertEqual(costs["actual"]["credits"], 4.0)
        self.assertTrue(costs["actual"]["ceiling_breach"])
        state.record_actual_cost(self.production, "SHOT_002", 2.0, "agent", "job-2")
        self.assertEqual(
            state.read_json(state.data_dir(self.production) / "costs.json")["actual"]["credits"],
            4.0,
        )

    def test_attempt_reviews_persist_and_drive_evidence_based_retry_strategy(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        self.complete_shot(job_id="job-review-1")
        first = state.record_attempt_review(
            self.production,
            "SHOT_001",
            "ATTEMPT_001",
            "REJECTED",
            ["CAMERA_MISS"],
            "MAJOR",
            "user",
            human_confirmed=True,
        )
        self.assertEqual(first["classification"], "INSUFFICIENT_EVIDENCE")
        state.transition_generation(self.production, "SHOT_001", "READY", "agent", "controlled retry")
        self.complete_shot(job_id="job-review-2")
        second = state.record_attempt_review(
            self.production,
            "SHOT_001",
            "ATTEMPT_002",
            "REJECTED",
            ["CAMERA_MISS"],
            "MAJOR",
            "user",
            human_confirmed=True,
        )
        self.assertEqual(second["classification"], "SYSTEMATIC")
        self.assertEqual(second["next_action"], "CHANGE_ONE_VARIABLE")
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertTrue(shot["generation"]["attempts"][1]["review"]["human_confirmed"])

    def test_shot_grammar_is_required_and_edits_invalidate_approval(self) -> None:
        state.add_scene(self.production, "SCENE_EMPTY", "Unplanned", 0)
        state.add_shot(self.production, "SHOT_EMPTY", "SCENE_EMPTY", "Unplanned", 0)
        with self.assertRaisesRegex(state.StateError, "shot grammar gate failed"):
            state.transition_shot_approval(self.production, "SHOT_EMPTY", "INTERNAL_QC_PASSED", "agent")
        self.add_locked_asset()
        self.add_locked_shot()
        before = next(item for item in state.read_json(state.data_dir(self.production) / "shots.json")["items"] if item["id"] == "SHOT_001")
        self.assertEqual(before["approval_status"], "LOCKED_FOR_VIDEO")
        state.update_shot(self.production, "SHOT_001", {"shot_grammar": {"why": "revised rationale"}}, "agent")
        after = next(item for item in state.read_json(state.data_dir(self.production) / "shots.json")["items"] if item["id"] == "SHOT_001")
        self.assertEqual(after["approval_status"], "DRAFT")
        self.assertEqual(after["generation"]["version"], before["generation"]["version"] + 1)
        self.assertTrue(all(value == "PENDING" for value in after["qc"].values()))

    def test_explicit_v1_migration_adds_grammar_and_qc(self) -> None:
        state.add_scene(self.production, "SCENE_001", "Opening", 1)
        state.add_shot(self.production, "SHOT_001", "SCENE_001", "Reveal", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 1
            if name == "shots.json":
                document["items"][0].pop("shot_grammar")
                document["items"][0]["qc"].pop("cinematography")
            state.atomic_write_json(path, document, backup=False)
        result = state.migrate(self.production)
        self.assertTrue(result["migrated"])
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertIn("shot_grammar", shot)
        self.assertEqual(shot["qc"]["cinematography"], "PENDING")
        self.assertIn("boundary_analysis", shot)
        self.assertIn("start_frame_qc", shot)
        self.assertIn("story", shot)
        self.assertIn("start_image_review", shot)
        self.assertEqual(
            state.read_json(state.data_dir(self.production) / "project.json")["schema_version"],
            state.SCHEMA_VERSION,
        )
        self.assertFalse(state.validate(self.production))

    def test_explicit_v8_migration_adds_adaptive_policy_and_director_state(self) -> None:
        state.add_scene(self.production, "SCENE_OLD", "Old", 1)
        state.add_shot(self.production, "SHOT_OLD", "SCENE_OLD", "Old shot", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 8
            if name == "project.json":
                document.pop("production_policy", None)
            if name == "shots.json":
                shot = document["items"][0]
                shot.pop("director_intelligence", None)
                shot["boundary"].pop("end_keyframe", None)
                shot["boundary"].pop("end_keyframe_role", None)
                shot["shot_grammar"]["provider_binding"].pop("prompt_lint", None)
            state.atomic_write_json(path, document)
        result = state.migrate(self.production)
        self.assertTrue(result["migrated"])
        project = state.read_json(state.data_dir(self.production) / "project.json")
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(project["production_policy"]["approval_profile"], "FULL")
        self.assertIn("complexity", shot["director_intelligence"])
        self.assertIn("end_keyframe", shot["boundary"])
        self.assertIn("start_frame_qc", shot)
        self.assertIn("story", shot)
        self.assertIn("start_image_review", shot)
        self.assertEqual(
            state.read_json(state.data_dir(self.production) / "project.json")["schema_version"],
            state.SCHEMA_VERSION,
        )
        self.assertFalse(state.validate(self.production))

    def test_explicit_v9_migration_adds_cinema35_plan(self) -> None:
        state.add_scene(self.production, "SCENE_OLD", "Old", 1)
        state.add_shot(self.production, "SHOT_OLD", "SCENE_OLD", "Old shot", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 9
            if name == "shots.json":
                document["items"][0].pop("cinema35_plan", None)
            state.atomic_write_json(path, document, backup=False)
        result = state.migrate(self.production)
        self.assertEqual(result["schema_version"], state.SCHEMA_VERSION)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["cinema35_plan"]["camera_style"], None)
        self.assertEqual(shot["cinema35_plan"]["start_frame_behavior"], "match_then_release")

    def test_explicit_v10_migration_adds_submission_provenance(self) -> None:
        state.add_scene(self.production, "SCENE_OLD", "Old", 1)
        state.add_shot(self.production, "SHOT_OLD", "SCENE_OLD", "Old shot", 1)
        shots_path = state.data_dir(self.production) / "shots.json"
        shots = state.read_json(shots_path)
        shots["items"][0]["generation"]["attempts"] = [
            {
                "attempt_id": "ATTEMPT_001",
                "job_id": "legacy-job",
                "resolution": "RECORDED",
                "review": None,
            }
        ]
        state.atomic_write_json(shots_path, shots, backup=False)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 10
            state.atomic_write_json(path, document, backup=False)
        state.migrate(self.production)
        attempt = state.read_json(shots_path)["items"][0]["generation"]["attempts"][0]
        self.assertEqual(attempt["submission_surface"], "unknown")
        self.assertIsNone(attempt["result_path"])

    def test_explicit_v5_migration_converts_visible_dialogue_to_native_audio(self) -> None:
        state.add_scene(self.production, "SCENE_001", "Opening", 1)
        state.add_shot(self.production, "SHOT_001", "SCENE_001", "Dialogue", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 5
            if name == "shots.json":
                shot = document["items"][0]
                shot["seedance_plan"].pop("sound_design", None)
                shot["audio"].update(
                    {
                        "route": "VISIBLE_DIALOGUE_ELEVENLABS_V3",
                        "dialogue_master_path": "media/audio/dialogue.wav",
                        "dialogue_master_sha256": "sha256:" + "a" * 64,
                        "discard_generated_track": True,
                        "final_mix_required": True,
                    }
                )
                shot["story"]["dialogue_master_sha256"] = "sha256:" + "a" * 64
            state.atomic_write_json(path, document, backup=False)
        result = state.migrate(self.production)
        self.assertEqual(result["schema_version"], state.SCHEMA_VERSION)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["audio"]["route"], "VISIBLE_DIALOGUE_V3_REFERENCE_NATIVE_AUDIO")
        self.assertEqual(shot["audio"]["generated_track_policy"], "PRESERVE")
        self.assertFalse(shot["audio"]["final_mix_required"])
        self.assertEqual(shot["audio"]["dialogue_reference_path"], "media/audio/dialogue.wav")
        self.assertNotIn("discard_generated_track", shot["audio"])
        self.assertIn("sound_design", shot["seedance_plan"])

    def test_explicit_v6_migration_preserves_generated_shot_without_inventing_review(self) -> None:
        state.add_scene(self.production, "SCENE_001", "Opening", 1)
        state.add_shot(self.production, "SHOT_001", "SCENE_001", "Existing render", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 6
            if name == "shots.json":
                shot = document["items"][0]
                shot.pop("start_image_review", None)
                shot["generation"]["status"] = "GENERATED"
            state.atomic_write_json(path, document, backup=False)
        result = state.migrate(self.production)
        self.assertEqual(result["schema_version"], state.SCHEMA_VERSION)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["start_image_review"]["status"], "NOT_APPLICABLE")
        self.assertIn("no v7 preflight", shot["start_image_review"]["notes"])

    def test_explicit_v5_migration_preserves_intentional_silence_mode(self) -> None:
        state.add_scene(self.production, "SCENE_001", "Ending", 1)
        state.add_shot(self.production, "SHOT_001", "SCENE_001", "Silence", 1)
        for name in state.DATA_FILES:
            path = state.data_dir(self.production) / name
            document = state.read_json(path)
            document["schema_version"] = 5
            if name == "shots.json":
                shot = document["items"][0]
                shot["seedance_plan"]["audio_mode"] = "none"
                shot["seedance_plan"].pop("sound_design", None)
                shot["audio"].update({"route": "INTENTIONAL_SILENCE", "final_mix_required": False})
            state.atomic_write_json(path, document, backup=False)
        state.migrate(self.production)
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        self.assertEqual(shot["seedance_plan"]["audio_mode"], "none")
        self.assertEqual(shot["audio"]["generated_track_policy"], "NOT_GENERATED")
        self.assertFalse(shot["audio"]["final_mix_required"])

    def test_history_and_backup_are_durable(self) -> None:
        state.set_requirement(self.production, "purpose", "film", "CONFIRMED", "user", "test")
        backup = self.production / "data" / "requirements.json.bak"
        self.assertTrue(backup.is_file())
        events = state.read_json(state.data_dir(self.production) / "history.json")["events"]
        self.assertGreaterEqual(len(events), 2)
        payload = (self.production / "dashboard" / "project-data.js").read_text(encoding="utf-8")
        self.assertIn("SONOL_HIGGSFIELD_STATE", payload)
        self.assertIn("requirement_updated", payload)


if __name__ == "__main__":
    unittest.main()
