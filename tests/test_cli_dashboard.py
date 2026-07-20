from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent
CLI = SKILL / "scripts" / "sonol_higgsfield.py"
SERVER = SKILL / "scripts" / "dashboard_server.py"


class CliDashboardTests(unittest.TestCase):
    def test_cli_recommends_three_grammar_plans(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(CLI), "recommend-grammar", "제품을 고급스럽게 공개", "--genre", "product_ad", "--platform", "reels", "--provider", "seedance_2_0", "--top", "3"],
            text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(len(payload["recommendations"]), 3)
        self.assertTrue(all(item["grammar"]["status"] == "RECOMMENDED" for item in payload["recommendations"]))

    def test_cli_initializes_and_rejects_premature_lock(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            production = Path(folder) / "production"
            created = subprocess.run(
                [sys.executable, str(CLI), "init", str(production), "--name", "CLI Test"],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(json.loads(created.stdout)["production"], str(production.resolve()))
            rejected = subprocess.run(
                [sys.executable, str(CLI), "lock-requirements", str(production), "--actor", "user"],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("not confirmed", rejected.stderr)

    def test_loopback_dashboard_and_action_token(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            production = Path(folder) / "production"
            subprocess.run(
                [sys.executable, str(CLI), "init", str(production), "--name", "Web Test"],
                capture_output=True,
                timeout=30,
                check=True,
            )
            process = subprocess.Popen(
                [sys.executable, str(SERVER), str(production), "--port", "0", "--token", "test-token"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                assert process.stdout is not None
                line = process.stdout.readline().strip()
                self.assertIn("127.0.0.1:", line)
                base = line.split("Dashboard: ", 1)[1].split("/?", 1)[0]
                with urllib.request.urlopen(base + "/api/state", timeout=5) as response:
                    payload = json.load(response)
                self.assertEqual(payload["project"]["project"]["name"], "Web Test")

                request = urllib.request.Request(
                    base + "/api/action",
                    data=json.dumps({"action": "lock_requirements"}).encode(),
                    headers={"Content-Type": "application/json", "X-Sonol-Token": "wrong"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 403)

                request = urllib.request.Request(
                    base + "/api/action",
                    data=json.dumps({"action": "lock_requirements"}).encode(),
                    headers={"Content-Type": "application/json", "X-Sonol-Token": "test-token"},
                    method="POST",
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 400)
                self.assertIn("not confirmed", caught.exception.read().decode())
            finally:
                process.terminate()
                process.wait(timeout=10)
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()


if __name__ == "__main__":
    unittest.main()
