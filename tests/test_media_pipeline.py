from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import media_pipeline as media  # noqa: E402


class MediaPipelineTests(unittest.TestCase):
    def test_boundary_candidates_cover_only_final_half_second(self) -> None:
        values = media.boundary_candidate_timestamps(5.0, window_seconds=0.5, count=8)
        self.assertEqual(len(values), 8)
        self.assertGreaterEqual(values[0], 4.499)
        self.assertLess(values[-1], 5.0)

    def test_sharpest_candidate_uses_lowest_blur_and_later_tie(self) -> None:
        selected = media.select_sharpest_candidate(
            [
                {"timestamp": 4.6, "blur_score": 5.0},
                {"timestamp": 4.7, "blur_score": 2.0},
                {"timestamp": 4.8, "blur_score": 2.0},
            ]
        )
        self.assertEqual(selected["timestamp"], 4.8)

    def test_blur_score_parser_fails_closed(self) -> None:
        self.assertEqual(media.parse_blur_score("[blurdetect] blur mean: 3.125"), 3.125)
        with self.assertRaisesRegex(media.MediaError, "did not return"):
            media.parse_blur_score("no score")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is required")
    def test_boundary_extraction_scores_real_final_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video = root / "input.mp4"
            command = [
                shutil.which("ffmpeg") or "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=320x240:rate=24:duration=1",
                "-vf",
                "boxblur=12:enable='gte(t,0.8)'",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(video),
            ]
            completed = subprocess.run(command, text=True, capture_output=True, timeout=60, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = media.extract_boundary_frames(
                shutil.which("ffmpeg") or "ffmpeg",
                shutil.which("ffprobe") or "ffprobe",
                video,
                root / "frames",
            )
            self.assertTrue(Path(result["start"]).is_file())
            self.assertTrue(Path(result["end"]).is_file())
            selection = result["selection"]
            self.assertEqual(selection["method"], "lowest_ffmpeg_blurdetect_mean")
            self.assertEqual(selection["window_seconds"], 0.5)
            self.assertEqual(len(selection["candidates"]), 8)
            self.assertLess(float(selection["selected_timestamp"]), 0.85)


if __name__ == "__main__":
    unittest.main()
