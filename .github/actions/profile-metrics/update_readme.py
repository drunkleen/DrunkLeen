#!/usr/bin/env python3
"""Update the profile README with local, non-AI development metrics."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
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
    query = urllib.parse.urlencode({"api_key": api_key})
    payload = request_json(
        f"{WAKATIME_API}/users/current/stats/last_7_days?{query}",
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
            language = repository.get("language") or "Other"
            languages[str(language)] += 1
        if len(repositories) < 100:
            break
    return languages


def fetch_recent_commit_periods(
    token: str,
    username: str,
    timezone_name: str,
    now: datetime | None = None,
) -> Counter[str]:
    periods: Counter[str] = Counter({"Morning": 0, "Daytime": 0, "Evening": 0, "Night": 0})
    headers = github_headers(token)
    local_timezone = ZoneInfo(timezone_name)
    local_now = (now or datetime.now(timezone.utc)).astimezone(local_timezone)
    since = (local_now - timedelta(days=7)).date().isoformat()

    for page in range(1, 11):
        query = urllib.parse.urlencode(
            {
                "q": f"author:{username} author-date:>={since}",
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


def format_duration(total_seconds: float) -> str:
    seconds = max(0, round(float(total_seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hr" if hours == 1 else f"{hours} hrs")
    if minutes:
        parts.append(f"{minutes} min" if minutes == 1 else f"{minutes} mins")
    if not parts:
        parts.append(f"{seconds} sec" if seconds == 1 else f"{seconds} secs")
    return " ".join(parts)


def normalize_editors(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    for item in items:
        name = str(item.get("name") or "Unknown")
        comparable = re.sub(r"[^a-z0-9]+", "", name.casefold())
        if "opencode" in comparable or "vscode" in comparable or "visualstudiocode" in comparable:
            name = "Neovim"
        totals[name] = totals.get(name, 0.0) + float(item.get("total_seconds", 0.0) or 0.0)

    total_seconds = sum(totals.values())
    normalized = [
        {
            "name": name,
            "total_seconds": seconds,
            "text": format_duration(seconds),
            "percent": round(seconds / total_seconds * 100.0, 2) if total_seconds else 0.0,
        }
        for name, seconds in totals.items()
    ]
    return sorted(normalized, key=lambda item: (-float(item["total_seconds"]), str(item["name"]).casefold()))


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


def select_metric_items(items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    selected = list(items[:limit])
    other = next((item for item in items if str(item.get("name", "")).casefold() == "other"), None)
    if other is not None and other not in selected:
        selected = selected[: max(0, limit - 1)] + [other]
    return selected


def html_metric_table(title: str, items: list[dict[str, Any]], *, preserve_other: bool = False) -> str:
    visible = select_metric_items(items) if preserve_other else list(items[:5])
    rows = [
        "<table>",
        f"<tr><th align=\"left\" colspan=\"4\">{escape(title)}</th></tr>",
        "<tr><th align=\"left\">Name</th><th align=\"left\">Time</th><th align=\"left\">Activity</th><th align=\"right\">Share</th></tr>",
    ]
    if not visible:
        rows.append('<tr><td colspan="4"><em>No activity tracked this week</em></td></tr>')
    for item in visible:
        name = escape(str(item.get("name") or "Unknown"))
        text = escape(str(item.get("text") or "0 secs"))
        percent = max(0.0, min(100.0, float(item.get("percent", 0.0) or 0.0)))
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f"<td><code>{text}</code></td>"
            f"<td><code>{render_bar(percent, width=16)}</code></td>"
            f"<td align=\"right\">{percent:0.2f}%</td>"
            "</tr>"
        )
    rows.append("</table>")
    return "\n".join(rows)


def metric_total_seconds(waka: dict[str, Any]) -> float:
    explicit = float(waka.get("total_seconds", 0.0) or 0.0)
    if explicit > 0:
        return explicit
    return sum(float(item.get("total_seconds", 0.0) or 0.0) for item in list(waka.get("languages") or []))


def terminal_metric_lines(
    label: str,
    items: list[dict[str, Any]],
    *,
    preserve_other: bool = False,
) -> list[str]:
    visible = select_metric_items(items) if preserve_other else list(items[:5])
    lines = [f"  {label}"]
    if not visible:
        return lines + ["    no signal"]
    for item in visible:
        name = str(item.get("name") or "Unknown")[:16]
        text = str(item.get("text") or "0 secs")[:13]
        percent = max(0.0, min(100.0, float(item.get("percent", 0.0) or 0.0)))
        lines.append(f"    {name:<16} {render_bar(percent, width=18)}  {percent:6.2f}%  {text:>13}")
    return lines


def terminal_dashboard(
    waka: dict[str, Any],
    editors: list[dict[str, Any]],
    systems: list[dict[str, Any]],
) -> str:
    languages = list(waka.get("languages") or [])
    total_seconds = metric_total_seconds(waka)
    top_language = str(languages[0].get("name") or "No signal") if languages else "No signal"
    top_percent = float(languages[0].get("percent", 0.0) or 0.0) if languages else 0.0
    editor_name = str(editors[0].get("name") or "No signal") if editors else "No signal"
    system_name = str(systems[0].get("name") or "No signal") if systems else "No signal"

    lines = [
        "╭─ WAKATIME // 7 DAY SIGNAL ─────────────────────────────────────────────╮",
        f"│ TOTAL DEV   {format_duration(total_seconds):<18} DAILY AVG   {format_duration(total_seconds / 7):<16} │",
        f"│ TOP LANGUAGE {top_language[:14]:<14} {top_percent:6.2f}%     EDITOR      {editor_name[:16]:<16} │",
        f"│ SYSTEM       {system_name[:16]:<16} STATUS      TRACKING LIVE             │",
        "├─────────────────────────────────────────────────────────────────────────┤",
        *terminal_metric_lines("LANGUAGES", languages, preserve_other=True),
        "│",
        *terminal_metric_lines("EDITORS", editors),
        "│",
        *terminal_metric_lines("OPERATING SYSTEMS", systems),
        "╰─────────────────────────────────────────────────────────────────────────╯",
    ]
    return f"<pre>\n{escape(chr(10).join(lines))}\n</pre>"


def build_section(
    waka: dict[str, Any],
    commits: dict[str, int],
    repositories: dict[str, int],
    now: datetime | None = None,
) -> str:
    now = now or datetime.now(timezone.utc)
    timezone_name = str(waka.get("timezone") or "Europe/Berlin")
    editors = normalize_editors(list(waka.get("editors") or []))
    systems = list(waka.get("operating_systems") or [])
    languages = list(waka.get("languages") or [])

    commit_labels = [("Morning", "Morning"), ("Daytime", "Daytime"), ("Evening", "Evening"), ("Night", "Night")]
    total_commits = sum(max(0, commits.get(name, 0)) for name, _ in commit_labels)
    commit_rows = [
        "<table>",
        '<tr><th align="left" colspan="3">Commit rhythm</th></tr>',
        '<tr><th align="left">Period</th><th align="left">Activity</th><th align="right">Commits</th></tr>',
    ]
    for name, label in commit_labels:
        count = max(0, commits.get(name, 0))
        percent = count / total_commits * 100.0 if total_commits else 0.0
        commit_rows.append(
            f'<tr><td>{label}</td><td><code>{render_bar(percent, width=16)}</code></td><td align="right">{count}</td></tr>'
        )
    commit_rows.append("</table>")

    ordered_repositories = sorted(repositories.items(), key=lambda item: (-item[1], item[0].casefold()))
    repository_total = sum(repositories.values())
    repository_rows = [
        "<table>",
        '<tr><th align="left" colspan="3">Repository languages</th></tr>',
        '<tr><th align="left">Language</th><th align="left">Share</th><th align="right">Repositories</th></tr>',
    ]
    if not ordered_repositories:
        repository_rows.append('<tr><td colspan="3"><em>No repository language data available</em></td></tr>')
    for language, count in ordered_repositories[:5]:
        percent = count / repository_total * 100.0 if repository_total else 0.0
        repository_rows.append(
            f'<tr><td>{escape(language)}</td><td><code>{render_bar(percent, width=16)}</code></td><td align="right">{count}</td></tr>'
        )
    repository_rows.append("</table>")

    total_seconds = metric_total_seconds(waka)
    top_language = str(languages[0].get("name") or "No signal") if languages else "No signal"
    top_editor = str(editors[0].get("name") or "No signal") if editors else "No signal"

    lines = [
        '<div align="center">',
        '<h2>Development signal</h2>',
        '<p><code>LEENIUM://TELEMETRY</code> · <strong>LAST 7 DAYS</strong> · WakaTime + GitHub</p>',
        f'<p><small>{escape(timezone_name)} · generated from live development activity</small></p>',
        '</div>',
        "",
        '<table><tr>',
        f'<td align="center"><strong>{escape(format_duration(total_seconds))}</strong><br><sub>TOTAL DEV</sub></td>',
        f'<td align="center"><strong>{escape(format_duration(total_seconds / 7))}</strong><br><sub>DAILY AVG</sub></td>',
        f'<td align="center"><strong>{escape(top_language)}</strong><br><sub>TOP LANGUAGE</sub></td>',
        f'<td align="center"><strong>{escape(top_editor)}</strong><br><sub>EDITOR</sub></td>',
        f'<td align="center"><strong>{total_commits}</strong><br><sub>COMMITS</sub></td>',
        '</tr></table>',
        "",
        terminal_dashboard(waka, editors, systems),
        "",
        '<details>',
        '<summary><strong>Open full telemetry</strong> · languages, environment, commit rhythm, repositories</summary>',
        "",
        html_metric_table("Programming languages", languages, preserve_other=True),
        "",
        html_metric_table("Editors", editors),
        "",
        html_metric_table("Operating systems", systems),
        "",
        *commit_rows,
        "",
        *repository_rows,
        "",
        '</details>',
        "",
        f'<p align="center"><small>Last Updated on {now.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")}</small></p>',
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
