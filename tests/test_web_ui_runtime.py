from __future__ import annotations

import sys
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))
import web_ui_runtime  # noqa: E402


class WebUiRuntimeTests(unittest.TestCase):
    def test_platform_detection_distinguishes_wsl_windows_and_macos(self) -> None:
        self.assertEqual(
            web_ui_runtime.host_platform(system="Linux", release="5.15.0-microsoft-standard", environ={}),
            "wsl",
        )
        self.assertEqual(web_ui_runtime.host_platform(system="Windows", release="11", environ={}), "windows")
        self.assertEqual(web_ui_runtime.host_platform(system="Darwin", release="25", environ={}), "macos")

    def test_browser_command_uses_isolated_profile_and_loopback_cdp(self) -> None:
        command = web_ui_runtime.browser_command(
            "chrome", "/safe/profile", 9222, "https://higgsfield.ai/generate"
        )
        self.assertIn("--remote-debugging-port=9222", command)
        self.assertIn("--remote-debugging-address=127.0.0.1", command)
        self.assertIn("--user-data-dir=/safe/profile", command)
        self.assertEqual(command[-1], "https://higgsfield.ai/generate")

    def test_wsl_prefers_windows_browser_and_node(self) -> None:
        self.assertTrue(web_ui_runtime.candidate_browsers("wsl")[0].endswith("chrome.exe"))
        self.assertTrue(web_ui_runtime.candidate_nodes("wsl")[0].endswith("node.exe"))


if __name__ == "__main__":
    unittest.main()
