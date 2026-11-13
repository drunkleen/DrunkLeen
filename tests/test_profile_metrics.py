import importlib.util
import unittest
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / ".github" / "actions" / "profile-metrics" / "update_readme.py"
ASSETS_MODULE_PATH = Path(__file__).parents[1] / ".github" / "actions" / "profile-metrics" / "leenium_assets.py"
README_PATH = Path(__file__).parents[1] / "README.md"
spec = importlib.util.spec_from_file_location("profile_metrics", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load profile metrics module from {MODULE_PATH}")
profile_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile_metrics)

assets_spec = importlib.util.spec_from_file_location("leenium_assets", ASSETS_MODULE_PATH)
if assets_spec is None or assets_spec.loader is None:
    raise RuntimeError(f"Unable to load Leenium assets module from {ASSETS_MODULE_PATH}")
leenium_assets = importlib.util.module_from_spec(assets_spec)
assets_spec.loader.exec_module(leenium_assets)


class ProfileMetricsTests(unittest.TestCase):
    def test_static_leenium_assets_restore_the_full_visual_system(self):
        assets = leenium_assets.build_static_assets()

        expected = {
            "hero-desktop.svg", "hero-mobile.svg",
            "about-desktop.svg", "about-mobile.svg",
            "stack-desktop.svg", "stack-mobile.svg",
            "projects-desktop.svg", "projects-mobile.svg",
            "footer-desktop.svg", "footer-mobile.svg",
        }
        self.assertEqual(set(assets), expected)
        for svg in assets.values():
            ET.fromstring(svg)
            self.assertIn("#0b1113", svg)
            self.assertIn("#33b8a8", svg)

    def test_desktop_about_copy_stays_clear_of_current_focus_panel(self):
        root = ET.fromstring(leenium_assets.about_svg(mobile=False))
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        left_copy = [
            "".join(node.itertext())
            for node in root.findall("svg:text", namespace)
            if node.get("x") == "52" and 180 <= int(node.get("y", "0")) <= 255
        ]

        self.assertGreaterEqual(len(left_copy), 3)
        self.assertTrue(all(len(line) <= 64 for line in left_copy), left_copy)

    def test_project_svg_has_no_fake_unclickable_repository_cta(self):
        assets = leenium_assets.build_static_assets()

        self.assertNotIn("VIEW REPOSITORY", assets["projects-desktop.svg"])
        self.assertNotIn("VIEW REPOSITORY", assets["projects-mobile.svg"])

    def test_readme_exposes_real_clickable_project_actions(self):
        readme = README_PATH.read_text(encoding="utf-8")

        self.assertIn('href="https://github.com/drunkleen/leenium.omarchy"', readme)
        self.assertIn('href="https://leenium.drunkleen.com"', readme)
        self.assertIn('href="https://github.com/drunkleen/leenfetch"', readme)
        self.assertIn('href="https://github.com/persian-rust"', readme)
        self.assertIn('href="https://drunkleen.com"', readme)
        self.assertIn("BLOG", readme)

    def test_metrics_svg_preserves_other_and_mobile_repository_breakdown(self):
        waka = {
            "timezone": "Europe/Berlin",
            "languages": [
                {"name": name, "text": "1 hr", "percent": percent}
                for name, percent in [
                    ("Go", 25), ("Rust", 20), ("Python", 18),
                    ("Lua", 15), ("Markdown", 12), ("Other", 10),
                ]
            ],
            "editors": [{"name": "Neovim", "text": "6 hrs", "percent": 100}],
            "operating_systems": [{"name": "Linux", "text": "6 hrs", "percent": 100}],
        }
        repositories = {"Go": 5, "Rust": 3, "Other": 2}

        svg = leenium_assets.build_metrics_svg(waka, {}, repositories, mobile=True)

        ET.fromstring(svg)
        self.assertIn("Other", svg)
        self.assertIn("REPOSITORY LANGUAGES", svg)

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
            "total_seconds": 14400,
            "languages": [
                {"name": "Rust", "text": "3 hrs", "percent": 75.0, "total_seconds": 10800},
                {"name": "Go", "text": "1 hr", "percent": 25.0, "total_seconds": 3600},
            ],
            "editors": [{"name": "Neovim", "text": "4 hrs", "percent": 100.0, "total_seconds": 14400}],
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
        self.assertIn("WAKATIME // 7 DAY SIGNAL", section)
        self.assertIn("TOTAL DEV", section)
        self.assertIn("4 hrs", section)
        self.assertIn("TOP LANGUAGE", section)
        self.assertIn("<table>", section)
        self.assertIn("<pre>", section)
        self.assertIn("<details>", section)
        self.assertIn("Rust", section)
        self.assertIn("Neovim", section)
        self.assertIn("Linux", section)
        self.assertIn("Repository languages", section)
        self.assertIn("Last Updated on 12/11/2026 12:00:00 UTC", section)
        self.assertNotIn("AI Code Time", section)
        self.assertNotIn("AI Coding", section)
        self.assertNotIn("<img", section)
        self.assertNotIn("```", section)

    def test_terminal_dashboard_escapes_provider_text(self):
        waka = {
            "languages": [{"name": "<Rust & Go>", "text": "1 hr", "percent": 100.0}],
            "editors": [],
            "operating_systems": [],
        }

        section = profile_metrics.build_section(waka, {}, {})

        self.assertIn("&lt;Rust &amp; Go&gt;", section)
        self.assertNotIn("<Rust & Go>", section)

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
