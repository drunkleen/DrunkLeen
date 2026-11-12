import importlib.util
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / ".github" / "actions" / "profile-metrics" / "update_readme.py"
spec = importlib.util.spec_from_file_location("profile_metrics", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load profile metrics module from {MODULE_PATH}")
profile_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile_metrics)


class ProfileMetricsTests(unittest.TestCase):
    def test_redirects_are_rejected_before_credentials_can_be_forwarded(self):
        handler = profile_metrics.NoRedirectHandler()
        request = urllib.request.Request(
            "https://api.github.com/user/repos",
            headers={"Authorization": "Bearer secret"},
        )
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://attacker.example/collect",
            )

    def test_wakatime_key_is_sent_as_query_parameter(self):
        captured = {}
        original_request_json = profile_metrics.request_json

        def fake_request_json(url, headers=None, service="API"):
            captured["url"] = url
            captured["headers"] = headers
            captured["service"] = service
            return {"data": {"languages": []}}

        setattr(profile_metrics, "request_json", fake_request_json)
        try:
            result = profile_metrics.fetch_wakatime_stats("waka_test/key")
        finally:
            setattr(profile_metrics, "request_json", original_request_json)

        self.assertEqual(result, {"languages": []})
        self.assertIn("api_key=waka_test%2Fkey", captured["url"])
        self.assertIsNone(captured["headers"])
        self.assertEqual(captured["service"], "WakaTime")

    def test_render_bar_uses_requested_width(self):
        self.assertEqual(profile_metrics.render_bar(50.0, width=10), "█████░░░░░")
        self.assertEqual(profile_metrics.render_bar(0.0, width=4), "░░░░")
        self.assertEqual(profile_metrics.render_bar(100.0, width=4), "████")

    def test_build_section_keeps_non_ai_metrics_only(self):
        waka = {
            "timezone": "Europe/Berlin",
            "languages": [
                {"name": "Rust", "text": "3 hrs", "percent": 75.0},
                {"name": "Go", "text": "1 hr", "percent": 25.0},
            ],
            "editors": [{"name": "Neovim", "text": "4 hrs", "percent": 100.0}],
            "operating_systems": [{"name": "Linux", "text": "4 hrs", "percent": 100.0}],
        }
        commits = {"Morning": 4, "Daytime": 3, "Evening": 2, "Night": 1}
        repositories = {"Rust": 5, "Go": 3}

        section = profile_metrics.build_section(
            waka,
            commits,
            repositories,
            now=datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
        )

        self.assertIn("**I'm an Early 🐤**", section)
        self.assertIn("This Week I Spent My Time On", section)
        self.assertIn("Rust", section)
        self.assertIn("Neovim", section)
        self.assertIn("Linux", section)
        self.assertIn("**I Mostly Code in Rust**", section)
        self.assertIn("Last Updated on 12/11/2026 12:00:00 UTC", section)
        self.assertNotIn("AI Code Time", section)
        self.assertNotIn("AI Coding", section)

    def test_replace_section_preserves_surrounding_readme(self):
        original = "before\n<!--START_SECTION:waka-->\nold\n<!--END_SECTION:waka-->\nafter\n"
        updated = profile_metrics.replace_section(original, "new stats", "waka")
        self.assertEqual(
            updated,
            "before\n<!--START_SECTION:waka-->\nnew stats\n<!--END_SECTION:waka-->\nafter\n",
        )

    def test_replace_section_rejects_missing_markers(self):
        with self.assertRaises(ValueError):
            profile_metrics.replace_section("no markers", "stats", "waka")


if __name__ == "__main__":
    unittest.main()
