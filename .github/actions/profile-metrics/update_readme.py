#!/usr/bin/env python3
"""Update the profile README with local, non-AI development metrics."""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

GITHUB_API = "https://api.github.com"
WAKATIME_API = "https://wakatime.com/api/v1"
USER_AGENT = "drunkleen-profile-metrics/1.0"


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Fail closed so authenticated headers never cross an HTTP redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url,
            code,
            "Redirects are disabled for authenticated API requests",
            headers,
            fp,
        )


HTTP_OPENER = urllib.request.build_opener(NoRedirectHandler())


def request_json(
    url: str,
    headers: dict[str, str] | None = None,
    service: str = "API",
) -> Any:
    request_headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with HTTP_OPENER.open(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{service} request failed with HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"{service} request failed: {error.reason}") from error


def fetch_wakatime_stats(api_key: str) -> dict[str, Any]:
    basic = base64.b64encode(f"{api_key}:".encode()).decode()
    payload = request_json(
        f"{WAKATIME_API}/users/current/stats/last_7_days",
        {"Authorization": f"Basic {basic}"},
        service="WakaTime",
    )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("WakaTime response did not contain a data object")
    return data


def github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_repository_languages(token: str, username: str) -> Counter[str]:
    languages: Counter[str] = Counter()
    headers = github_headers(token)
    for page in range(1, 11):
        query = urllib.parse.urlencode(
            {
                "affiliation": "owner,collaborator,organization_member",
                "sort": "updated",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            }
        )
        repositories = request_json(f"{GITHUB_API}/user/repos?{query}", headers, service="GitHub")
        if not isinstance(repositories, list):
            raise RuntimeError("GitHub repositories response was not a list")
        for repository in repositories:
            owner = (repository.get("owner") or {}).get("login", "")
            if owner.casefold() != username.casefold():
                continue
            if repository.get("fork") or repository.get("archived"):
                continue
            language = repository.get("language")
            if language:
                languages[str(language)] += 1
        if len(repositories) < 100:
            break
    return languages


def fetch_recent_commit_periods(token: str, username: str, timezone_name: str) -> Counter[str]:
    periods: Counter[str] = Counter({"Morning": 0, "Daytime": 0, "Evening": 0, "Night": 0})
    headers = github_headers(token)
    local_timezone = ZoneInfo(timezone_name)

    for page in range(1, 11):
        query = urllib.parse.urlencode(
            {
                "q": f"author:{username}",
                "sort": "author-date",
                "order": "desc",
                "per_page": 100,
                "page": page,
            }
        )
        payload = request_json(f"{GITHUB_API}/search/commits?{query}", headers, service="GitHub")
        commits = payload.get("items", [])
        if not isinstance(commits, list):
            raise RuntimeError("GitHub commit search response did not contain an items list")

        for item in commits:
            raw_date = (((item.get("commit") or {}).get("author") or {}).get("date"))
            if not raw_date:
                continue
            committed_at = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
            hour = committed_at.astimezone(local_timezone).hour
            if 6 <= hour < 12:
                periods["Morning"] += 1
            elif 12 <= hour < 18:
                periods["Daytime"] += 1
            elif 18 <= hour < 24:
                periods["Evening"] += 1
            else:
                periods["Night"] += 1

        if len(commits) < 100:
            break

    return periods


def render_bar(percent: float, width: int = 25) -> str:
    bounded = max(0.0, min(100.0, float(percent)))
    filled = round(width * bounded / 100.0)
    return "█" * filled + "░" * (width - filled)


def render_metric_rows(items: list[dict[str, Any]], limit: int = 5) -> list[str]:
    rows: list[str] = []
    for item in items[:limit]:
        name = str(item.get("name", "Unknown"))
        text = str(item.get("text", "0 secs"))
        percent = float(item.get("percent", 0.0) or 0.0)
        rows.append(f"{name:<25} {text:<19} {render_bar(percent)}   {percent:05.2f} %")
    return rows or ["No activity tracked this week"]


def render_commit_rows(periods: dict[str, int]) -> tuple[str, list[str]]:
    labels = [
        ("Morning", "🌞 Morning"),
        ("Daytime", "🌆 Daytime"),
        ("Evening", "🌃 Evening"),
        ("Night", "🌙 Night"),
    ]
    total = sum(max(0, periods.get(name, 0)) for name, _ in labels)
    dominant = max(labels, key=lambda item: periods.get(item[0], 0))[0]
    titles = {
        "Morning": "I'm an Early 🐤",
        "Daytime": "I'm a Daytime 🐱",
        "Evening": "I'm an Evening 🦉",
        "Night": "I'm a Night 🦉",
    }
    rows: list[str] = []
    for name, label in labels:
        count = max(0, periods.get(name, 0))
        percent = (count / total * 100.0) if total else 0.0
        rows.append(f"{label:<25} {count:<19} {render_bar(percent)}   {percent:05.2f} %")
    return titles[dominant], rows


def render_repository_rows(languages: dict[str, int]) -> tuple[str, list[str]]:
    ordered = sorted(languages.items(), key=lambda item: (-item[1], item[0].casefold()))
    if not ordered:
        return "I Mostly Code in Open Source", ["No repository language data available"]
    total = sum(count for _, count in ordered)
    title = f"I Mostly Code in {ordered[0][0]}"
    rows = []
    for language, count in ordered[:5]:
        percent = count / total * 100.0 if total else 0.0
        rows.append(f"{language:<25} {count} repos{' ' * 12} {render_bar(percent)}   {percent:05.2f} %")
    return title, rows


def build_section(
    waka: dict[str, Any],
    commits: dict[str, int],
    repositories: dict[str, int],
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(timezone.utc)
    timezone_name = str(waka.get("timezone") or "Europe/Berlin")
    productivity_title, commit_rows = render_commit_rows(commits)
    repository_title, repository_rows = render_repository_rows(repositories)

    lines = [
        f"**{productivity_title}** ",
        "",
        "```text",
        *commit_rows,
        "```",
        "",
        "📊 **This Week I Spent My Time On** ",
        "",
        "```text",
        f"🕑︎ Time Zone: {timezone_name}",
        "",
        "💬 Programming Languages: ",
        *render_metric_rows(list(waka.get("languages") or [])),
        "",
        "🔥 Editors: ",
        *render_metric_rows(list(waka.get("editors") or [])),
        "",
        "💻 Operating System: ",
        *render_metric_rows(list(waka.get("operating_systems") or [])),
        "```",
        "",
        f"**{repository_title}** ",
        "",
        "```text",
        *repository_rows,
        "```",
        "",
        f"Last Updated on {now.astimezone(timezone.utc).strftime('%d/%m/%Y %H:%M:%S UTC')}",
    ]
    return "\n".join(lines).rstrip()


def replace_section(readme: str, section: str, section_name: str = "waka") -> str:
    start = f"<!--START_SECTION:{section_name}-->"
    end = f"<!--END_SECTION:{section_name}-->"
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)
    if not pattern.search(readme):
        raise ValueError(f"README markers {start} and {end} were not found")
    replacement = f"{start}\n{section}\n{end}"
    return pattern.sub(replacement, readme, count=1)


def set_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"{name}={value}\n")


def required_input(name: str) -> str:
    value = os.environ.get(f"INPUT_{name.upper()}", "").strip()
    if not value:
        raise RuntimeError(f"Action input {name} is required")
    return value


def main() -> int:
    try:
        wakatime_api_key = required_input("wakatime_api_key")
        github_token = required_input("github_token")
        username = os.environ.get("INPUT_USERNAME", "drunkleen").strip() or "drunkleen"
        readme_path = Path(os.environ.get("INPUT_README_PATH", "README.md"))
        section_name = os.environ.get("INPUT_SECTION_NAME", "waka").strip() or "waka"
        timezone_name = os.environ.get("INPUT_TIMEZONE", "Europe/Berlin").strip() or "Europe/Berlin"

        waka = fetch_wakatime_stats(wakatime_api_key)
        commits = fetch_recent_commit_periods(github_token, username, timezone_name)
        repositories = fetch_repository_languages(github_token, username)

        original = readme_path.read_text(encoding="utf-8")
        section = build_section(waka, commits, repositories)
        updated = replace_section(original, section, section_name)
        changed = updated != original
        if changed:
            readme_path.write_text(updated, encoding="utf-8")
        set_output("changed", str(changed).lower())
        print(f"Profile metrics updated: changed={str(changed).lower()}")
        return 0
    except Exception as error:
        print(f"profile-metrics: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
