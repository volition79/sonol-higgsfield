from __future__ import annotations

import importlib.util
import json
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

    def test_atempo_chain_handles_extreme_factors(self) -> None:
        self.assertEqual(media_pipeline.atempo_chain(1.0), "atempo=1.00000000")
        self.assertIn("atempo=2.00000000", media_pipeline.atempo_chain(5.0))
        self.assertIn("atempo=0.50000000", media_pipeline.atempo_chain(0.2))
        with self.assertRaises(media_pipeline.MediaError):
            media_pipeline.atempo_chain(0)

    def test_reference_cost_arithmetic_uses_matching_actual_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            production = base / "production"
            state.initialize(production, "Cost", SKILL / "assets" / "dashboard-template")
            state.add_scene(production, "SCENE_001", "One", 1)
            state.add_shot(production, "SHOT_001", "SCENE_001", "One", 1)
            argv = [
                "seedance_2_0", "--duration", "5", "--resolution", "720p",
                "--generate-audio", "false",
            ]
            state.update_shot(
                production,
                "SHOT_001",
                {
                    "duration_seconds": 5,
                    "execution": {"mode": "model", "argv": argv},
                },
                "agent",
            )
            profile = estimate_costs.execution_profile("model", argv)
            state.record_actual_cost(
                production, "HISTORICAL_001", 10, "agent", "job-history-1", execution_profile=profile
            )
            result = estimate_costs.calculate(production, attempts=2)
            self.assertEqual(result["total_estimated_credits"], 20.0)
            self.assertEqual(result["covered_shots"], 1)
            costs = state.read_json(state.data_dir(production) / "costs.json")
            self.assertEqual(costs["reference_estimates"]["method"], "recent_actual_arithmetic")
            self.assertNotIn("scenarios", costs)

    def test_final_mix_drops_source_audio_and_uses_external_stems(self) -> None:
        command = media_pipeline.final_mix_command(
            "ffmpeg",
            Path("picture.mp4"),
            Path("final.mp4"),
            dialogue=Path("dialogue.wav"),
            music=Path("music.wav"),
        )
        self.assertEqual(command.count("-i"), 3)
        self.assertIn("0:v:0", command)
        self.assertIn("[mix]", command)
        self.assertNotIn("0:a:0", " ".join(command))

    def test_preserve_audio_keeps_generated_picture_and_sound_without_stems(self) -> None:
        command = media_pipeline.preserve_audio_command(
            "ffmpeg", Path("generated.mp4"), Path("accepted.mp4")
        )
        self.assertEqual(command.count("-i"), 1)
        self.assertIn("0:v:0", command)
        self.assertIn("0:a:0", command)
        self.assertIn("copy", command)

    def test_schema_snapshot_fingerprints_contracts(self) -> None:
        contract = {"job_type": "seedance_2_0", "params": []}
        first = inspect_live_schema.stable_hash(contract)
        second = inspect_live_schema.stable_hash({"params": [], "job_type": "seedance_2_0"})
        self.assertEqual(first, second)
        self.assertNotEqual(first, inspect_live_schema.stable_hash({"job_type": "seedance_2_0", "params": [1]}))


if __name__ == "__main__":
    unittest.main()
