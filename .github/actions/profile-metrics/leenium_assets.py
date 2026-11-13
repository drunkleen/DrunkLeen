#!/usr/bin/env python3
"""Render GitHub-safe SVG assets using the canonical Leenium palette."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any

BG = "#0b1113"
SURFACE = "#11191c"
BORDER = "#365156"
FG = "#d8e3e0"
MUTED = "#718688"
ACCENT = "#33b8a8"
CYAN = "#59d6c5"
EMERALD = "#4dba7a"
BLUE = "#5e9bff"
YELLOW = "#d9c76b"
ORANGE = "#f4a259"
RED = "#e16f73"
FONT = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, Liberation Mono, monospace"


def _svg_open(width: int, height: int, label: str, *, grid: bool = False) -> str:
    pattern = ""
    background = f'<rect width="{width}" height="{height}" rx="22" fill="{BG}"/>'
    if grid:
        pattern = f"""
  <defs>
    <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
      <path d="M 28 0 L 0 0 0 28" fill="none" stroke="{BORDER}" stroke-opacity="0.18" stroke-width="1"/>
    </pattern>
    <linearGradient id="fade" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{ACCENT}" stop-opacity="0.12"/>
      <stop offset="0.55" stop-color="{BG}" stop-opacity="0"/>
      <stop offset="1" stop-color="{BLUE}" stop-opacity="0.08"/>
    </linearGradient>
  </defs>
  {background}
  <rect width="{width}" height="{height}" rx="22" fill="url(#grid)"/>
  <rect width="{width}" height="{height}" rx="22" fill="url(#fade)"/>"""
    else:
        pattern = background
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label)}">
  {pattern}
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="21" fill="none" stroke="{BORDER}" stroke-width="2"/>
"""


def _svg_close() -> str:
    return "</svg>\n"


def _text(x: float, y: float, value: str, size: int, color: str = FG, weight: int = 400, anchor: str = "start", opacity: float = 1.0) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{color}" fill-opacity="{opacity}" '
        f'font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">'
        f"{escape(value)}</text>"
    )


def _window_bar(width: int, title: str, right: str = "") -> str:
    parts = [
        f'<rect x="1" y="1" width="{width - 2}" height="52" rx="21" fill="{SURFACE}"/>',
        f'<path d="M1 52 H{width - 1}" stroke="{BORDER}"/>',
        f'<circle cx="28" cy="27" r="5" fill="{RED}"/>',
        f'<circle cx="47" cy="27" r="5" fill="{YELLOW}"/>',
        f'<circle cx="66" cy="27" r="5" fill="{EMERALD}"/>',
        _text(88, 33, title.upper(), 14, CYAN, 700),
    ]
    if right:
        parts.append(_text(width - 24, 33, right, 12, MUTED, 500, "end"))
    return "\n  ".join(parts)


def _chip(x: int, y: int, label: str, color: str, width: int) -> str:
    return "\n".join(
        [
            f'<rect x="{x}" y="{y}" width="{width}" height="34" rx="8" fill="{SURFACE}" stroke="{BORDER}"/>',
            f'<circle cx="{x + 17}" cy="{y + 17}" r="4" fill="{color}"/>',
            _text(x + 30, y + 22, label, 13, FG, 600),
        ]
    )


def hero_svg(*, mobile: bool) -> str:
    if mobile:
        width, height = 390, 540
        out = [_svg_open(width, height, "Leen profile hero", grid=True), _window_bar(width, "leenium / profile", "master")]
        out += [
            _text(28, 103, "LEEN / DRUNKLEEN", 12, ACCENT, 700),
            _text(28, 150, "Developer.", 34, FG, 750),
            _text(28, 190, "Linux user.", 34, FG, 750),
            _text(28, 230, "Open-source builder.", 28, CYAN, 750),
            _text(28, 275, "I build practical tools, learn in public,", 15, MUTED, 400),
            _text(28, 300, "and publish what survives daily use.", 15, MUTED, 400),
            f'<rect x="28" y="334" width="334" height="96" rx="12" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(48, 368, "leen@galaxy", 14, EMERALD, 700),
            _text(150, 368, ":~$", 14, BLUE, 700),
            _text(48, 400, "whoami --verbose", 16, FG, 600),
            f'<rect x="48" y="413" width="9" height="18" fill="{ACCENT}"/>',
            _chip(28, 462, "RUST", ORANGE, 96),
            _chip(136, 462, "GO", CYAN, 78),
            _chip(226, 462, "LINUX", EMERALD, 112),
        ]
    else:
        width, height = 1200, 390
        out = [_svg_open(width, height, "Leen profile hero", grid=True), _window_bar(width, "leenium / profile", "master · dresden · online")]
        out += [
            _text(52, 108, "LEEN / DRUNKLEEN", 14, ACCENT, 700),
            _text(52, 166, "Developer. Linux user.", 42, FG, 750),
            _text(52, 216, "Open-source builder.", 42, CYAN, 750),
            _text(52, 258, "Rust, Go, Linux, networking and practical systems.", 17, MUTED, 400),
            f'<rect x="760" y="92" width="388" height="174" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(790, 126, "leen@galaxy", 15, EMERALD, 700),
            _text(900, 126, ":~$", 15, BLUE, 700),
            _text(790, 164, "whoami --verbose", 18, FG, 600),
            _text(790, 201, "open_source=true", 14, MUTED),
            _text(790, 229, "daily_driver=linux", 14, MUTED),
            f'<rect x="790" y="241" width="10" height="18" fill="{ACCENT}"/>',
            _chip(52, 304, "RUST", ORANGE, 112),
            _chip(176, 304, "GO", CYAN, 90),
            _chip(278, 304, "LINUX", EMERALD, 126),
            _chip(416, 304, "NETWORKING", BLUE, 174),
            _chip(602, 304, "SELF-HOSTING", YELLOW, 190),
        ]
    out.append(_svg_close())
    return "\n  ".join(out)


def about_svg(*, mobile: bool) -> str:
    if mobile:
        width, height = 390, 620
        out = [_svg_open(width, height, "About Leen"), _window_bar(width, "about / leen")]
        out += [
            _text(28, 100, "ABOUT", 13, ACCENT, 700),
            _text(28, 140, "Curiosity is the workflow.", 23, FG, 750),
            _text(28, 181, "I'm a developer and open-source", 15, MUTED),
            _text(28, 205, "enthusiast focused on Rust, Go, Linux,", 15, MUTED),
            _text(28, 229, "networking and system-level software.", 15, MUTED),
            f'<rect x="28" y="264" width="334" height="230" rx="12" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(48, 300, "CURRENT FOCUS", 12, CYAN, 700),
            _text(48, 338, "01  Open-source tools", 15, FG, 600),
            _text(48, 374, "02  Linux & self-hosting", 15, FG, 600),
            _text(48, 410, "03  Networking & security", 15, FG, 600),
            _text(48, 446, "04  Persian education", 15, FG, 600),
            _text(28, 540, "LOCATION", 11, MUTED, 700),
            _text(28, 568, "Dresden, Germany", 15, BLUE, 600),
            _text(214, 540, "STATUS", 11, MUTED, 700),
            _text(214, 568, "building", 15, EMERALD, 600),
        ]
    else:
        width, height = 1200, 370
        out = [_svg_open(width, height, "About Leen"), _window_bar(width, "about / leen", "curiosity > convention")]
        out += [
            _text(52, 105, "ABOUT", 13, ACCENT, 700),
            _text(52, 150, "Curiosity is the workflow.", 30, FG, 750),
            _text(52, 190, "I'm a developer and open-source enthusiast focused on", 16, MUTED),
            _text(52, 218, "Rust, Go, Linux, networking, and system-level software.", 16, MUTED),
            _text(52, 246, "I also build self-hosted systems and Persian education.", 16, MUTED),
            f'<rect x="706" y="86" width="442" height="214" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(736, 121, "CURRENT FOCUS", 12, CYAN, 700),
            _text(736, 160, "01", 13, ACCENT, 700), _text(780, 160, "Open-source tools", 15, FG, 600),
            _text(736, 199, "02", 13, ACCENT, 700), _text(780, 199, "Linux & self-hosting", 15, FG, 600),
            _text(736, 238, "03", 13, ACCENT, 700), _text(780, 238, "Networking & security", 15, FG, 600),
            _text(736, 277, "04", 13, ACCENT, 700), _text(780, 277, "Persian education", 15, FG, 600),
            _text(52, 282, "LOCATION", 11, MUTED, 700), _text(52, 311, "Dresden, Germany", 15, BLUE, 600),
            _text(254, 282, "STATUS", 11, MUTED, 700), _text(254, 311, "building", 15, EMERALD, 600),
            _text(412, 282, "MODE", 11, MUTED, 700), _text(412, 311, "open source", 15, YELLOW, 600),
        ]
    out.append(_svg_close())
    return "\n  ".join(out)


def stack_svg(*, mobile: bool) -> str:
    items = [
        ("Rust", ORANGE), ("Go", CYAN), ("Linux", EMERALD), ("Docker", BLUE),
        ("Kubernetes", BLUE), ("Git", ORANGE), ("Neovim", ACCENT), ("PostgreSQL", BLUE),
        ("Bash", YELLOW), ("Python", YELLOW), ("Java", RED), ("SQLite", CYAN),
    ]
    if mobile:
        width, height = 390, 500
        out = [_svg_open(width, height, "Technology stack"), _window_bar(width, "stack / modules")]
        out.append(_text(28, 96, "TOOLS I REACH FOR", 13, ACCENT, 700))
        for index, (name, color) in enumerate(items):
            col, row = index % 2, index // 2
            x, y = 28 + col * 170, 122 + row * 54
            out.append(_chip(x, y, name.upper(), color, 156))
        out += [_text(28, 467, "small tools · sharp edges · boring reliability", 12, MUTED)]
    else:
        width, height = 1200, 270
        out = [_svg_open(width, height, "Technology stack"), _window_bar(width, "stack / modules", "12 loaded")]
        out.append(_text(52, 98, "TOOLS I REACH FOR", 13, ACCENT, 700))
        for index, (name, color) in enumerate(items):
            col, row = index % 6, index // 6
            x, y = 52 + col * 184, 122 + row * 56
            out.append(_chip(x, y, name.upper(), color, 166))
        out += [_text(1148, 245, "small tools · sharp edges · boring reliability", 12, MUTED, 400, "end")]
    out.append(_svg_close())
    return "\n  ".join(out)


def projects_svg(*, mobile: bool) -> str:
    if mobile:
        width, height = 390, 1000
        out = [_svg_open(width, height, "Featured projects"), _window_bar(width, "projects / featured", "3 selected")]
        cards = [
            (82, "01 / THEME", "LEENIUM THEME", "Dark-teal desktop environment", "for Omarchy and daily tools.", ACCENT),
            (378, "02 / RUST", "LEENFETCH", "Fast, minimal system information", "built for real daily use.", ORANGE),
            (674, "03 / COMMUNITY", "PERSIAN RUST", "Persian educational resources", "for learning Rust together.", CYAN),
        ]
        for y, tag, title, line1, line2, color in cards:
            out += [
                f'<rect x="28" y="{y}" width="334" height="250" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
                _text(50, y + 38, tag, 11, color, 700),
                _text(50, y + 84, title, 24, FG, 750),
                _text(50, y + 126, line1, 14, MUTED),
                _text(50, y + 150, line2, 14, MUTED),
                _chip(50, y + 188, "PROJECT READY", color, 180),
            ]
    else:
        width, height = 1200, 680
        out = [_svg_open(width, height, "Featured projects"), _window_bar(width, "projects / featured", "3 selected")]
        out += [
            f'<rect x="52" y="86" width="1096" height="190" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(82, 126, "01 / THEME", 11, ACCENT, 700),
            _text(82, 180, "LEENIUM THEME", 29, FG, 750),
            _text(82, 224, "A cohesive dark-teal environment for Omarchy, terminal tools, editors, Waybar, browsers, and more.", 15, MUTED),
            _chip(900, 145, "PROJECT READY", ACCENT, 200),
        ]
        cards = [
            (52, "02 / RUST", "LEENFETCH", "Fast and minimal system information", "tool, built for performance and daily use.", ORANGE),
            (616, "03 / COMMUNITY", "PERSIAN RUST", "Persian educational content and resources", "for Rust learners and open-source contributors.", CYAN),
        ]
        for x, tag, title, line1, line2, color in cards:
            out += [
                f'<rect x="{x}" y="308" width="532" height="310" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
                _text(x + 30, 348, tag, 11, color, 700),
                _text(x + 30, 402, title, 27, FG, 750),
                _text(x + 30, 447, line1, 15, MUTED),
                _text(x + 30, 473, line2, 15, MUTED),
                _chip(x + 30, 526, "PROJECT READY", color, 190),
            ]
    out.append(_svg_close())
    return "\n  ".join(out)


def footer_svg(*, mobile: bool) -> str:
    if mobile:
        width, height = 390, 196
        out = [_svg_open(width, height, "Profile links")]
        out += [
            _text(28, 46, "LEENIUM.STATUS", 12, ACCENT, 700),
            _text(28, 82, "github / drunkleen", 14, FG, 600),
            _text(28, 112, "web / drunkleen.com", 14, FG, 600),
            _text(28, 142, "mail / anakin@drunkleen.com", 14, FG, 600),
            _text(28, 174, "● online", 12, EMERALD, 700),
        ]
    else:
        width, height = 1200, 126
        out = [_svg_open(width, height, "Profile links")]
        out += [
            _text(34, 43, "LEENIUM.STATUS", 12, ACCENT, 700),
            _text(34, 82, "github / drunkleen", 14, FG, 600),
            _text(350, 82, "web / drunkleen.com", 14, FG, 600),
            _text(660, 82, "mail / anakin@drunkleen.com", 14, FG, 600),
            _text(1166, 82, "● online", 12, EMERALD, 700, "end"),
        ]
    out.append(_svg_close())
    return "\n  ".join(out)


def _metric_bar(x: int, y: int, width: int, item: dict[str, Any], *, label_width: int, font_size: int = 13) -> list[str]:
    name = str(item.get("name") or "Unknown")
    text = str(item.get("text") or "0 secs")
    percent = max(0.0, min(100.0, float(item.get("percent", 0.0) or 0.0)))
    track_x = x + label_width
    track_width = width - label_width - 74
    fill_width = max(2, round(track_width * percent / 100.0)) if percent else 0
    parts = [
        _text(x, y + 5, name, font_size, FG, 600),
        f'<rect x="{track_x}" y="{y - 8}" width="{track_width}" height="12" rx="6" fill="{BORDER}" fill-opacity="0.45"/>',
    ]
    if fill_width:
        parts.append(f'<rect x="{track_x}" y="{y - 8}" width="{fill_width}" height="12" rx="6" fill="{ACCENT}"/>')
    parts += [
        _text(x + width, y + 5, f"{percent:0.1f}%", font_size - 1, CYAN, 700, "end"),
        _text(track_x, y + 25, text, font_size - 2, MUTED),
    ]
    return parts


def build_metrics_svg(
    waka: dict[str, Any],
    commits: dict[str, int],
    repositories: dict[str, int],
    *,
    now: datetime | None = None,
    mobile: bool,
) -> str:
    now = now or datetime.now(timezone.utc)
    all_languages = list(waka.get("languages") or [])
    languages = list(all_languages[:5])
    other = next((item for item in all_languages if str(item.get("name", "")).casefold() == "other"), None)
    if other is not None and other not in languages:
        languages = languages[:4] + [other]
    editors = list(waka.get("editors") or [])
    systems = list(waka.get("operating_systems") or [])
    editor = str(editors[0].get("name") if editors else "No activity")
    editor_time = str(editors[0].get("text") if editors else "0 secs")
    system = str(systems[0].get("name") if systems else "Unknown")
    timezone_name = str(waka.get("timezone") or "Europe/Berlin")
    total_commits = sum(max(0, int(value)) for value in commits.values())
    ordered_repositories = sorted(repositories.items(), key=lambda item: (-item[1], item[0].casefold()))[:5]
    total_repositories = sum(repositories.values())
    updated = now.astimezone(timezone.utc).strftime("%d %b %Y").upper()

    if mobile:
        width, height = 390, 1080
        out = [_svg_open(width, height, "Development telemetry"), _window_bar(width, "development telemetry")]
        out += [
            _text(28, 96, "LAST 7 DAYS", 12, ACCENT, 700),
            _text(28, 130, "Development telemetry", 24, FG, 750),
            _text(28, 157, f"{timezone_name} · updated {updated}", 12, MUTED),
            f'<rect x="28" y="186" width="334" height="374" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(48, 220, "LANGUAGES", 12, CYAN, 700),
        ]
        y = 257
        for item in languages:
            out.extend(_metric_bar(48, y, 294, item, label_width=92, font_size=12))
            y += 62
        if not languages:
            out.append(_text(48, 270, "No activity tracked", 14, MUTED))
        out += [
            f'<rect x="28" y="582" width="334" height="152" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(48, 618, "ENVIRONMENT", 12, CYAN, 700),
            _text(48, 654, "EDITOR", 10, MUTED, 700), _text(144, 654, editor, 14, FG, 700),
            _text(48, 686, "TIME", 10, MUTED, 700), _text(144, 686, editor_time, 14, ACCENT, 700),
            _text(48, 718, "SYSTEM", 10, MUTED, 700), _text(144, 718, system, 14, FG, 700),
            f'<rect x="28" y="756" width="334" height="274" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(48, 791, "GITHUB SIGNAL", 12, CYAN, 700),
            _text(48, 830, str(total_commits), 26, FG, 750), _text(48, 854, "commits sampled", 10, MUTED),
            _text(230, 830, str(total_repositories), 26, FG, 750), _text(230, 854, "repositories", 10, MUTED),
            _text(48, 894, "REPOSITORY LANGUAGES", 10, MUTED, 700),
        ]
        y_repo = 926
        for language, count in ordered_repositories[:4]:
            out.append(_text(48, y_repo, language, 12, FG, 600))
            out.append(_text(330, y_repo, f"{count} repos", 11, BLUE, 600, "end"))
            y_repo += 25
        out += [_text(28, 1060, "generated locally · no separate AI section", 11, MUTED)]
    else:
        width, height = 1200, 720
        out = [_svg_open(width, height, "Development telemetry"), _window_bar(width, "development telemetry", f"{timezone_name} · {updated}")]
        out += [
            _text(52, 105, "LAST 7 DAYS", 12, ACCENT, 700),
            _text(52, 145, "Development telemetry", 31, FG, 750),
            _text(52, 176, "Language time includes provider-attributed assisted development; unclassified activity stays Other.", 13, MUTED),
            f'<rect x="52" y="208" width="704" height="448" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(82, 246, "LANGUAGES", 12, CYAN, 700),
        ]
        y = 292
        for item in languages:
            out.extend(_metric_bar(82, y, 638, item, label_width=150, font_size=14))
            y += 69
        if not languages:
            out.append(_text(82, 300, "No activity tracked", 15, MUTED))
        out += [
            f'<rect x="784" y="208" width="364" height="204" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(814, 246, "ENVIRONMENT", 12, CYAN, 700),
            _text(814, 292, "EDITOR", 10, MUTED, 700), _text(920, 292, editor, 15, FG, 700),
            _text(814, 330, "TIME", 10, MUTED, 700), _text(920, 330, editor_time, 15, ACCENT, 700),
            _text(814, 368, "SYSTEM", 10, MUTED, 700), _text(920, 368, system, 15, FG, 700),
            f'<rect x="784" y="436" width="364" height="220" rx="14" fill="{SURFACE}" stroke="{BORDER}"/>',
            _text(814, 474, "GITHUB SIGNAL", 12, CYAN, 700),
            _text(814, 526, str(total_commits), 32, FG, 750), _text(814, 550, "commits sampled", 10, MUTED),
            _text(1020, 526, str(total_repositories), 32, FG, 750), _text(1020, 550, "repositories", 10, MUTED),
            _text(814, 570, "TOP REPOSITORY LANGUAGES", 10, MUTED, 700),
        ]
        y_repo = 600
        for language, count in ordered_repositories[:3]:
            out.append(_text(814, y_repo, language, 13, FG, 600))
            out.append(_text(1118, y_repo, f"{count} repos", 12, BLUE, 600, "end"))
            y_repo += 26
        out += [_text(52, 692, "generated locally · GitHub Actions · no separate AI section", 11, MUTED)]

    out.append(_svg_close())
    return "\n  ".join(out)


def build_static_assets() -> dict[str, str]:
    return {
        "hero-desktop.svg": hero_svg(mobile=False),
        "hero-mobile.svg": hero_svg(mobile=True),
        "about-desktop.svg": about_svg(mobile=False),
        "about-mobile.svg": about_svg(mobile=True),
        "stack-desktop.svg": stack_svg(mobile=False),
        "stack-mobile.svg": stack_svg(mobile=True),
        "projects-desktop.svg": projects_svg(mobile=False),
        "projects-mobile.svg": projects_svg(mobile=True),
        "footer-desktop.svg": footer_svg(mobile=False),
        "footer-mobile.svg": footer_svg(mobile=True),
    }
