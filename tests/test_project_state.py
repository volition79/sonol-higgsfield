from __future__ import annotations

import json
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
import execution_contract  # noqa: E402
from test_cinematography import seedance_snapshot  # noqa: E402


class ProductionStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.production = Path(self.temp.name) / "production"
        state.initialize(self.production, "테스트 제작", SKILL / "assets" / "dashboard-template")
        self.live_schema = seedance_snapshot()

    def tearDown(self) -> None:
        self.temp.cleanup()

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

    def approve_current_shot_cost(self, credits: float = 2.5, ceiling: float = 3.0) -> None:
        shot = state.read_json(state.data_dir(self.production) / "shots.json")["items"][0]
        execution = shot["generation"]["execution"]
        fingerprint = execution_contract.fingerprint(execution["mode"], execution["argv"])
        state.set_cost_scenario(self.production, "recommended", credits, "agent")
        state.replace_task_estimates(
            self.production,
            [{
                "shot_id": shot["id"],
                "scenario": "recommended",
                "credits": credits,
                "argv": execution["argv"],
                "execution_fingerprint": fingerprint,
            }],
            "agent",
        )
        state.approve_cost(self.production, "recommended", ceiling, "user")

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
        )
        argv = ["seedance_2_0", "--prompt", compiled["prompt"]]
        for key, value in compiled["native_params"].items():
            argv.extend(("--" + key.replace("_", "-"), json.dumps(value) if not isinstance(value, str) else value))
        state.update_shot(
            self.production, "SHOT_001",
            {
                "duration_seconds": 5,
                "continuity": continuity,
                "required_asset_ids": ["CHAR_001"],
                "model": "seedance_2_0",
                "seedance_plan": {"aspect_ratio": "16:9", "resolution": "720p"},
                "execution": {"mode": "model", "argv": argv},
                "shot_grammar": cinematography.apply_compilation(grammar, compiled),
            },
            "agent",
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

    def test_cost_approval_requires_locked_requirements_and_user(self) -> None:
        state.set_cost_scenario(self.production, "recommended", 2, "agent")
        with self.assertRaisesRegex(state.StateError, "requirements must be locked"):
            state.approve_cost(self.production, "recommended", 2, "user")
        self.confirm_requirements()
        state.lock_requirements(self.production, "user")
        with self.assertRaisesRegex(state.StateError, "only the user"):
            state.approve_cost(self.production, "recommended", 2, "agent")
        with self.assertRaisesRegex(state.StateError, "below"):
            state.approve_cost(self.production, "recommended", 1, "user")

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
        with self.assertRaisesRegex(state.StateError, "QC incomplete"):
            state.transition_generation(self.production, "SHOT_001", "FINAL_COMPLETE", "agent")
        for check in ("technical", "transcript", "lip_sync", "visual", "continuity", "cinematography"):
            state.set_qc(self.production, "SHOT_001", check, "PASSED", "agent")
        state.set_qc(self.production, "SHOT_001", "korean_pronunciation", "NOT_APPLICABLE", "agent")
        with self.assertRaisesRegex(state.StateError, "only the user"):
            state.set_qc(self.production, "SHOT_001", "user_review", "PASSED", "agent")
        state.set_qc(self.production, "SHOT_001", "user_review", "PASSED", "user")
        state.transition_generation(self.production, "SHOT_001", "FINAL_COMPLETE", "agent")
        self.assertFalse(state.validate(self.production))
        self.assertEqual(state.aggregate(self.production)["summary"]["progress_percent"], 100.0)

    def test_generation_is_blocked_without_locked_asset(self) -> None:
        self.lock_and_budget()
        state.add_asset(self.production, "CHAR_001", "character", "Hero")
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        with self.assertRaisesRegex(state.StateError, "required asset is not locked"):
            state.transition_generation(self.production, "SHOT_001", "QUEUED", "agent")

    def test_guarded_paid_runner_uses_exact_approved_estimate(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        fake = Path(self.temp.name) / "fake-higgsfield"
        contract = self.live_schema["model_contracts"]["seedance_2_0"]
        fake.write_text(
            "#!/usr/bin/env python3\nimport json,sys\n"
            f"contract={json.dumps(contract)!r}\n"
            "if 'account' in sys.argv: print(json.dumps({'credits': 100}))\n"
            "elif 'get' in sys.argv: print(contract)\n"
            "else: print(json.dumps({'job_id':'job-001','credits':2.5}))\n",
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        result = run_shot.run_paid(self.production, "SHOT_001", str(fake), False, 30)
        self.assertEqual(result["job_id"], "job-001")
        self.assertTrue(result["actual_credits_recorded"])
        aggregate = state.aggregate(self.production)
        self.assertEqual(aggregate["shots"][0]["generation"]["status"], "GENERATED")
        self.assertEqual(aggregate["costs"]["actual"]["credits"], 2.5)

    def test_guarded_paid_runner_rejects_quote_execution_drift_before_provider_call(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        costs_path = state.data_dir(self.production) / "costs.json"
        costs = state.read_json(costs_path)
        costs["task_estimates"][0]["execution_fingerprint"] = execution_contract.fingerprint(
            "model", ["seedance_2_0", "--prompt", "different"]
        )
        state.atomic_write_json(costs_path, costs, backup=False)
        state.transition_generation(self.production, "SHOT_001", "READY", "agent")
        with self.assertRaisesRegex(state.StateError, "quote does not match"):
            run_shot.run_paid(self.production, "SHOT_001", "/provider/must/not/run", False, 30)

    def test_provider_job_id_never_accepts_unrelated_id(self) -> None:
        self.assertIsNone(run_shot.provider_job_id({"id": "asset-001"}))
        self.assertIsNone(run_shot.provider_job_id({"data": {"id": "asset-001"}}))
        self.assertEqual(run_shot.provider_job_id({"data": {"job_id": "job-001"}}), "job-001")

    def test_requirement_change_invalidates_lock_and_cost(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.set_requirement(self.production, "duration_seconds", 6, "CONFIRMED", "user", "revision")
        project = state.read_json(state.data_dir(self.production) / "project.json")
        costs = state.read_json(state.data_dir(self.production) / "costs.json")
        self.assertEqual(project["requirements_lock"]["status"], "UNLOCKED")
        self.assertEqual(project["cost_approval"]["status"], "UNAPPROVED")
        self.assertEqual(costs["task_estimates"], [])

    def test_cost_impacting_shot_change_invalidates_quote_and_approval(self) -> None:
        self.lock_and_budget()
        self.add_locked_asset()
        self.add_locked_shot()
        self.approve_current_shot_cost()
        state.update_shot(self.production, "SHOT_001", {"duration_seconds": 6}, "agent")
        project = state.read_json(state.data_dir(self.production) / "project.json")
        costs = state.read_json(state.data_dir(self.production) / "costs.json")
        self.assertEqual(project["cost_approval"]["status"], "UNAPPROVED")
        self.assertEqual(project["cost_approval"]["task_contracts"], {})
        self.assertEqual(costs["task_estimates"], [])

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
        self.assertFalse(state.validate(self.production))

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
