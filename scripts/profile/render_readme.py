#!/usr/bin/env python3
"""Render README.md from README.template.md and data/profile_signals.json."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "README.template.md"
SIGNALS_PATH = ROOT / "data" / "profile_signals.json"
README_PATH = ROOT / "README.md"


def _fmt_num(value: int) -> str:
    return f"{value:,}"


def _fmt_push_date(raw: str) -> str:
    if not raw:
        return "n/a"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return raw
    return dt.strftime("%Y-%m-%d")


def _build_rows(repos: list[dict[str, Any]]) -> str:
    rows: list[str] = []
    for repo in sorted(repos, key=lambda item: str(item.get("name", "")).lower()):
        name = str(repo.get("name", "unknown"))
        stars = int(repo.get("stars", 0))
        issues = int(repo.get("open_issues", 0))
        pushed_at = _fmt_push_date(str(repo.get("pushed_at", "")))
        rows.append(f"| `{name}` | {_fmt_num(stars)} | {_fmt_num(issues)} | {pushed_at} |")
    return "\n".join(rows)


def _build_topline(repos: list[dict[str, Any]]) -> str:
    total_stars = sum(int(repo.get("stars", 0)) for repo in repos)
    total_open_issues = sum(int(repo.get("open_issues", 0)) for repo in repos)

    pushed_dates = [
        _fmt_push_date(str(repo.get("pushed_at", "")))
        for repo in repos
        if str(repo.get("pushed_at", ""))
    ]
    freshest = max(pushed_dates) if pushed_dates else "n/a"

    return (
        f"Total stars: `{_fmt_num(total_stars)}` | "
        f"Open issues: `{_fmt_num(total_open_issues)}` | "
        f"Freshest push: `{freshest}`"
    )


def main() -> int:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    signals = json.loads(SIGNALS_PATH.read_text(encoding="utf-8"))

    repos = list(signals.get("repos", []))
    if not isinstance(repos, list):
        raise RuntimeError("Invalid signals format: repos must be a list")

    last_refreshed = str(signals.get("generated_at_utc", "")) or datetime.now(UTC).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")

    rendered = template
    rendered = rendered.replace("{{TOPLINE_SIGNALS}}", _build_topline(repos))
    rendered = rendered.replace("{{SIGNALS_TABLE_ROWS}}", _build_rows(repos))
    rendered = rendered.replace("{{LAST_REFRESHED_UTC}}", last_refreshed)

    README_PATH.write_text(rendered.rstrip() + "\n", encoding="utf-8")
    print(f"Rendered {README_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
