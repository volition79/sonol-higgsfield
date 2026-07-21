from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


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
        compiled = cinematography.compile_prompt(
            grammar, provider="seedance_2_0", subject="the hero", setting="a quiet room",
            action="notices the hidden clue", exit_state="the hero holds still in realization",
            invariants=["same face and wardrobe"],
            live_schema=self.live_schema,
            seedance_plan={"aspect_ratio": "16:9", "resolution": "720p"},
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
                    "route": "NO_DIALOGUE_POST",
                    "has_visible_dialogue": False,
                    "generated_track_policy": "NOT_GENERATED",
                    "final_mix_required": True,
                },
                "model": "seedance_2_0",
                "seedance_plan": {"aspect_ratio": "16:9", "resolution": "720p", "audio_mode": "post_only"},
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
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        state.transition_generation(self.production, "SHOT_001", "QUEUED", "agent")
        state.transition_generation(self.production, "SHOT_001", "GENERATING", "agent")
        state.transition_generation(self.production, "SHOT_001", "GENERATED", "agent")
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
        with self.assertRaisesRegex(state.StateError, "v7 preparation review"):
            state.transition_generation(self.production, "SHOT_001", "QUEUED", "agent")
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
            state.transition_generation(self.production, "SHOT_001", "QUEUED", "agent")

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

    def test_next_shot_requires_accepted_analysis_and_jit_adaptation(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        for target in ("READY", "QUEUED", "GENERATING", "GENERATED"):
            state.transition_generation(self.production, "SHOT_001", target, "agent")
        state.set_qc(self.production, "SHOT_001", "user_review", "PASSED", "user")
        state.add_shot(self.production, "SHOT_002", "SCENE_001", "Reaction", 2)
        with self.assertRaisesRegex(state.StateError, "previous start-frame QC"):
            state.set_boundary(
                self.production,
                "SHOT_002",
                "editorial_cut",
                "agent",
                reason="reverse angle after the discovery",
                planned_keyframe="media/images/SHOT_002_start.png",
            )
        rendered_first = self.create_media_file("media/images/SHOT_001_rendered_first.png")
        boundary_frame = self.create_media_file("media/images/SHOT_001_boundary.png")
        state.record_start_frame_qc(self.production, "SHOT_001", rendered_first, "PASSED", "agent")
        with self.assertRaisesRegex(state.StateError, "previous boundary analysis"):
            state.set_adaptive_story(
                self.production,
                "SHOT_002",
                ["BEAT_001"],
                "react to the accepted hand position",
                "NOT_APPLICABLE",
                "agent",
                "SHOT_001",
            )
        state.record_boundary_analysis(
            self.production,
            "SHOT_001",
            boundary_frame,
            {key: f"observed {key}" for key in state.BOUNDARY_OBSERVATION_FIELDS},
            {
                "selection_method": "lowest_ffmpeg_blurdetect_mean",
                "window_seconds": 0.5,
                "selected_timestamp": 4.75,
                "selected_blur_score": 1.5,
                "candidates": [
                    {"timestamp": 4.6, "blur_score": 2.0},
                    {"timestamp": 4.75, "blur_score": 1.5},
                ],
            },
            "stage the reaction from the held-clue pose",
            "agent",
        )
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
        shot["boundary"]["start_image_provenance"]["created_after_shot_id"] = "SHOT_000"
        self.assertTrue(any("just in time" in item for item in state.sequential_adaptation_errors(state.load_all(self.production), shot)))

    def test_director_may_select_a_persisted_nonsharpest_boundary_with_reason(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        for target in ("READY", "QUEUED", "GENERATING", "GENERATED"):
            state.transition_generation(self.production, "SHOT_001", target, "agent")
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
            "elif 'get' in sys.argv: print(contract)\n"
            "else: print(json.dumps({'job_id':'job-001','credits':2.5}))\n",
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
        self.assertTrue(result["actual_credits_recorded"])
        aggregate = state.aggregate(self.production)
        self.assertEqual(aggregate["shots"][0]["generation"]["status"], "GENERATED")
        self.assertEqual(aggregate["costs"]["actual"]["credits"], 2.5)

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
        # identifier key is a plain "id"; non-dict payloads are rejected.
        self.assertEqual(run_shot.provider_job_id({"id": "job-001"}), "job-001")
        self.assertEqual(run_shot.provider_job_id([{"id": "job-001"}]), "job-001")
        self.assertEqual(run_shot.provider_job_id({"data": {"job_id": "job-001"}}), "job-001")
        self.assertIsNone(run_shot.provider_job_id("job-001"))
        self.assertIsNone(run_shot.provider_job_id(["job-001"]))
        self.assertIsNone(run_shot.provider_job_id({"credits": 5}))

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

    def test_actual_cost_cannot_exceed_ceiling(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.record_actual_cost(self.production, "SHOT_001", 2.0, "agent", "job-1")
        with self.assertRaisesRegex(state.StateError, "exceed"):
            state.record_actual_cost(self.production, "SHOT_002", 2.0, "agent", "job-2")
        costs = state.read_json(state.data_dir(self.production) / "costs.json")
        self.assertEqual(costs["actual"]["credits"], 2.0)

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
        self.assertEqual(state.read_json(state.data_dir(self.production) / "project.json")["schema_version"], 7)
        self.assertFalse(state.validate(self.production))

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
        self.assertEqual(result["schema_version"], 7)
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
        self.assertEqual(result["schema_version"], 7)
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
