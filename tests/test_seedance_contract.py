from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cinematography as cine  # noqa: E402
from test_cinematography import seedance_snapshot  # noqa: E402


class SeedanceContractTests(unittest.TestCase):
    def grammar(self, duration: float = 5) -> dict:
        return cine.recommend(
            "주인공이 단서를 발견한다",
            genre="drama",
            provider="seedance_2_0",
            duration_seconds=duration,
            top_n=1,
        )["recommendations"][0]["grammar"]

    def compile(self, **kwargs):
        values = {
            "grammar": self.grammar(),
            "provider": "seedance_2_0",
            "subject": "the same protagonist",
            "setting": "a dim office with window light",
            "action": "finds a hidden note",
            "exit_state": "holds the note at chest height",
            "live_schema": seedance_snapshot(),
        }
        values.update(kwargs)
        grammar = values.pop("grammar")
        return cine.compile_prompt(grammar, **values)

    def test_missing_stale_and_tampered_schema_are_rejected(self) -> None:
        with self.assertRaisesRegex(cine.CinematographyError, "fresh live schema"):
            self.compile(live_schema=None)
        stale = seedance_snapshot()
        stale["captured_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        with self.assertRaisesRegex(cine.CinematographyError, "stale"):
            self.compile(live_schema=stale)
        tampered = seedance_snapshot()
        tampered["model_contracts"]["seedance_2_0"]["params"][0]["enum"].append("2:35:1")
        with self.assertRaisesRegex(cine.CinematographyError, "fingerprint mismatch"):
            self.compile(live_schema=tampered)

    def test_audio_is_off_by_default_and_only_enabled_by_audio_plan(self) -> None:
        self.assertFalse(self.compile()["native_params"]["generate_audio"])
        for mode in ("native_sfx", "native_dialogue", "audio_reference"):
            with self.subTest(mode=mode):
                references = None
                if mode == "audio_reference":
                    references = {"images": ["hero.png"], "audios": ["voice.wav"]}
                compiled = self.compile(seedance_plan={"audio_mode": mode}, references=references)
                self.assertTrue(compiled["native_params"]["generate_audio"])
        self.assertFalse(self.compile(seedance_plan={"audio_mode": "post_only"})["native_params"]["generate_audio"])

    def test_all_live_reference_boundaries_are_enforced(self) -> None:
        bad_cases = [
            ({"images": list(range(10))}, "image references"),
            ({"videos": list(range(4))}, "video references"),
            ({"images": [1], "audios": list(range(4))}, "audio references"),
            ({"images": list(range(8)), "videos": [1, 2, 3], "audios": [1, 2]}, "total references"),
            ({"audios": ["voice.wav"]}, "at least one visual"),
        ]
        for references, message in bad_cases:
            with self.subTest(message=message), self.assertRaisesRegex(cine.CinematographyError, message):
                self.compile(seedance_plan={"audio_mode": "audio_reference"}, references=references)
        with self.assertRaisesRegex(cine.CinematographyError, "including start/end"):
            self.compile(references={"start": "a", "end": "b", "images": list(range(8))})
        with self.assertRaisesRegex(cine.CinematographyError, "at most 720p"):
            self.compile(seedance_plan={"generation_mode": "fast", "resolution": "1080p"})

    def test_duration_and_single_shot_semantics_are_enforced(self) -> None:
        with self.assertRaisesRegex(cine.CinematographyError, "between 4 and 15"):
            self.compile(grammar=self.grammar(3))
        with self.assertRaisesRegex(cine.CinematographyError, "8 seconds or shorter"):
            self.compile(grammar=self.grammar(9))
        with self.assertRaisesRegex(cine.CinematographyError, "cuts or montage"):
            self.compile(action="finds a note, hard cut to a close-up")
        compiled = self.compile(seedance_plan={"camera_invariants": ["no cuts", "no zoom", "natural head movement"]})
        self.assertIn("no cuts; no zoom; natural head movement", compiled["prompt"])

    def test_multishot_requires_approval_and_timecoded_beats(self) -> None:
        plan = {
            "mode": "seedance_multishot_experimental",
            "shot_count": 2,
            "timed_beats": [
                {"time": "0-2s", "action": "wide establishing view"},
                {"time": "2-5s", "action": "push in to the note"},
            ],
        }
        with self.assertRaisesRegex(cine.CinematographyError, "explicit user approval"):
            self.compile(seedance_plan=plan)
        plan["experimental_approved"] = True
        compiled = self.compile(seedance_plan=plan)
        self.assertIn("Shot 1 [0-2s]", compiled["prompt"])
        self.assertIn("Shot 2 [2-5s]", compiled["prompt"])

    def test_reference_manifest_preserves_semantic_roles_without_alias_invention(self) -> None:
        references = {
            "manifest": [
                {
                    "semantic_role": "character",
                    "transport_field": "image_references",
                    "source": "hero.png",
                    "controls": ["identity", "wardrobe"],
                    "prompt_alias": None,
                }
            ]
        }
        compiled = self.compile(references=references)
        self.assertEqual(compiled["native_params"]["image_references"], ["hero.png"])
        self.assertNotIn("@character", compiled["prompt"])
        invalid = deepcopy(references)
        invalid["manifest"][0]["prompt_alias"] = "@character"
        with self.assertRaisesRegex(cine.CinematographyError, "aliases are not exposed"):
            self.compile(references=invalid)

    def test_mini_uses_its_smaller_live_contract(self) -> None:
        compiled = self.compile(
            provider="seedance_2_0_mini",
            live_schema=seedance_snapshot("seedance_2_0_mini"),
        )
        self.assertNotIn("mode", compiled["native_params"])
        with self.assertRaisesRegex(cine.CinematographyError, "not allowed"):
            self.compile(
                provider="seedance_2_0_mini",
                live_schema=seedance_snapshot("seedance_2_0_mini"),
                seedance_plan={"resolution": "1080p"},
            )


if __name__ == "__main__":
    unittest.main()
