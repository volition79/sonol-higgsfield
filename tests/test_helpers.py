from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import estimate_costs  # noqa: E402
import inspect_live_schema  # noqa: E402
import media_pipeline  # noqa: E402
import project_state as state  # noqa: E402


class HelperTests(unittest.TestCase):
    def test_redaction_is_recursive(self) -> None:
        value = {"email": "a@example.com", "nested": [{"access_token": "secret", "credits": 10}]}
        redacted = inspect_live_schema.redact(value)
        self.assertEqual(redacted["email"], "[REDACTED]")
        self.assertEqual(redacted["nested"][0]["access_token"], "[REDACTED]")
        self.assertEqual(redacted["nested"][0]["credits"], 10)

    def test_cost_parser_and_media_upload_detection(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            media = Path(folder) / "input.png"
            media.write_bytes(b"not an image")
            found = estimate_costs.local_media_args([
                "model", f"--image_references={json.dumps([str(media)])}", "--video-references", "[]"
            ])
            self.assertEqual(found, [str(media.resolve())])
        self.assertEqual(estimate_costs.parse_credits({"credits": 2.5}), 2.5)
        with self.assertRaises(state.StateError):
            estimate_costs.parse_credits({"price": "unknown"})

    def test_atempo_chain_handles_extreme_factors(self) -> None:
        self.assertEqual(media_pipeline.atempo_chain(1.0), "atempo=1.00000000")
        self.assertIn("atempo=2.00000000", media_pipeline.atempo_chain(5.0))
        self.assertIn("atempo=0.50000000", media_pipeline.atempo_chain(0.2))
        with self.assertRaises(media_pipeline.MediaError):
            media_pipeline.atempo_chain(0)

    def test_explicit_three_scenario_quotes_with_fake_cli(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            production = base / "production"
            state.initialize(production, "Cost", SKILL / "assets" / "dashboard-template")
            state.add_scene(production, "SCENE_001", "One", 1)
            state.add_shot(production, "SHOT_001", "SCENE_001", "One", 1)
            options = {
                "economy": ["fake_model", "--quality", "economy"],
                "recommended": ["fake_model", "--quality", "recommended"],
                "highest_quality": ["fake_model", "--quality", "highest_quality"],
            }
            state.update_shot(
                production,
                "SHOT_001",
                {
                    "cost_options": options,
                    "execution": {"mode": "model", "argv": options["recommended"]},
                },
                "agent",
            )
            fake = base / "fake-higgsfield"
            fake.write_text(
                "#!/usr/bin/env python3\nimport json,sys\n"
                "quality=sys.argv[-1]\n"
                "print(json.dumps({'credits': {'economy':1,'recommended':2,'highest_quality':4}[quality]}))\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            totals = estimate_costs.estimate(production, str(fake), False)
            self.assertEqual(totals, {"economy": 1.0, "recommended": 2.0, "highest_quality": 4.0})
            costs = state.read_json(state.data_dir(production) / "costs.json")
            self.assertEqual(len(costs["task_estimates"]), 3)
            self.assertTrue(all(item["execution_fingerprint"].startswith("sha256:") for item in costs["task_estimates"]))

    def test_schema_snapshot_fingerprints_contracts(self) -> None:
        contract = {"job_type": "seedance_2_0", "params": []}
        first = inspect_live_schema.stable_hash(contract)
        second = inspect_live_schema.stable_hash({"params": [], "job_type": "seedance_2_0"})
        self.assertEqual(first, second)
        self.assertNotEqual(first, inspect_live_schema.stable_hash({"job_type": "seedance_2_0", "params": [1]}))


if __name__ == "__main__":
    unittest.main()
