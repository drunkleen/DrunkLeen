import importlib.util
import unittest
import urllib.error
import urllib.parse
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

    def test_editor_aliases_are_merged_into_neovim(self):
        editors = [
            {"name": "Neovim", "total_seconds": 3600, "text": "1 hr", "percent": 25.0},
            {"name": "Opencode Cli", "total_seconds": 7200, "text": "2 hrs", "percent": 50.0},
            {"name": "Codex Vscode", "total_seconds": 1800, "text": "30 mins", "percent": 12.5},
            {"name": "Zed", "total_seconds": 1800, "text": "30 mins", "percent": 12.5},
        ]

        normalized = profile_metrics.normalize_editors(editors)

        self.assertEqual([item["name"] for item in normalized], ["Neovim", "Zed"])
        self.assertEqual(normalized[0]["total_seconds"], 12600.0)
        self.assertEqual(normalized[0]["text"], "3 hrs 30 mins")
        self.assertEqual(normalized[0]["percent"], 87.5)

    def test_build_section_displays_alias_editors_as_neovim(self):
        waka = {
            "timezone": "Europe/Berlin",
            "languages": [{"name": "Go", "text": "2 hrs", "percent": 100.0}],
            "editors": [
                {"name": "Opencode Cli", "total_seconds": 5400, "text": "1 hr 30 mins", "percent": 75.0},
                {"name": "Codex Vscode", "total_seconds": 1800, "text": "30 mins", "percent": 25.0},
            ],
            "operating_systems": [{"name": "Linux", "text": "2 hrs", "percent": 100.0}],
        }

        section = profile_metrics.build_section(waka, {}, {})

        self.assertIn("Neovim", section)
        self.assertNotIn("Opencode", section)
        self.assertNotIn("Vscode", section)

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

        self.assertIn("LAST 7 DAYS", section)
        self.assertIn("<table>", section)
        self.assertIn("Rust", section)
        self.assertIn("Neovim", section)
        self.assertIn("Linux", section)
        self.assertIn("Repository languages", section)
        self.assertIn("Last Updated on 12/11/2026 12:00:00 UTC", section)
        self.assertNotIn("AI Code Time", section)
        self.assertNotIn("AI Coding", section)
        self.assertNotIn("<img", section)
        self.assertNotIn("```", section)

    def test_build_section_preserves_other_outside_top_five(self):
        waka = {
            "languages": [
                {"name": name, "text": "1 hr", "percent": percent}
                for name, percent in [
                    ("Go", 25), ("Rust", 20), ("Python", 18),
                    ("Lua", 15), ("Markdown", 12), ("Other", 10),
                ]
            ],
            "editors": [],
            "operating_systems": [],
        }

        section = profile_metrics.build_section(waka, {}, {})

        self.assertIn(">Other</td>", section)

    def test_commit_search_is_limited_to_last_seven_days(self):
        captured = []
        original_request_json = profile_metrics.request_json

        def fake_request_json(url, headers=None, service="API"):
            captured.append(url)
            return {"items": []}

        setattr(profile_metrics, "request_json", fake_request_json)
        try:
            profile_metrics.fetch_recent_commit_periods(
                "token",
                "drunkleen",
                "Europe/Berlin",
                now=datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc),
            )
        finally:
            setattr(profile_metrics, "request_json", original_request_json)

        query = urllib.parse.parse_qs(urllib.parse.urlparse(captured[0]).query)["q"][0]
        self.assertIn("author-date:>=2026-11-05", query)

    def test_repository_without_primary_language_is_counted_as_other(self):
        original_request_json = profile_metrics.request_json

        def fake_request_json(url, headers=None, service="API"):
            return [
                {"owner": {"login": "drunkleen"}, "fork": False, "archived": False, "language": "Go"},
                {"owner": {"login": "drunkleen"}, "fork": False, "archived": False, "language": None},
            ]

        setattr(profile_metrics, "request_json", fake_request_json)
        try:
            languages = profile_metrics.fetch_repository_languages("token", "drunkleen")
        finally:
            setattr(profile_metrics, "request_json", original_request_json)

        self.assertEqual(languages["Go"], 1)
        self.assertEqual(languages["Other"], 1)

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
