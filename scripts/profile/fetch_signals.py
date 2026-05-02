#!/usr/bin/env python3
"""Fetch sanitized first-party repo signals for profile README generation."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "sheawinkler"
REPOS = (
    "ContextLattice",
    "hermes-agent-ultra",
    "algotrader-community",
    "fastapi-sidecar",
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "data" / "profile_signals.json"


@dataclass(frozen=True)
class RepoSignal:
    name: str
    stars: int
    open_issues: int
    pushed_at: str


def fetch_repo(owner: str, repo: str, token: str | None = None) -> RepoSignal:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "sheawinkler-profile-readme-generator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url=url, headers=headers)

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"HTTP error for {repo}: {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error for {repo}: {exc.reason}") from exc

    return RepoSignal(
        name=repo,
        stars=int(payload.get("stargazers_count", 0)),
        open_issues=int(payload.get("open_issues_count", 0)),
        pushed_at=str(payload.get("pushed_at", "")),
    )


def main() -> int:
    token = os.getenv("PROFILE_README_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")
    generated_at_utc = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    repos: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for repo in REPOS:
        try:
            signal = fetch_repo(OWNER, repo, token=token)
            repos.append(
                {
                    "name": signal.name,
                    "stars": signal.stars,
                    "open_issues": signal.open_issues,
                    "pushed_at": signal.pushed_at,
                }
            )
        except RuntimeError as exc:
            errors.append({"repo": repo, "error": str(exc)})
            repos.append(
                {
                    "name": repo,
                    "stars": 0,
                    "open_issues": 0,
                    "pushed_at": "",
                }
            )

    payload = {
        "generated_at_utc": generated_at_utc,
        "owner": OWNER,
        "repos": repos,
        "errors": errors,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print(json.dumps({"status": "degraded", "errors": errors}, indent=2))
    else:
        print(json.dumps({"status": "ok", "repos": len(repos)}, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
