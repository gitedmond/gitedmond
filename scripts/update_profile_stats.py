"""Refresh the public GitHub figures shown in the profile SVG cards."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SVG_FILES = (ROOT / "light_mode.svg", ROOT / "dark_mode.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, ownerAffiliations: OWNER) {
      totalCount
      nodes { stargazerCount }
    }
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
  }
}
"""


def github_data() -> dict[str, int]:
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ.get("PROFILE_USER", "gitedmond")
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "gitedmond-profile-stats",
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if "errors" in payload:
        raise RuntimeError(payload["errors"])

    user = payload["data"]["user"]
    repositories = user["repositories"]
    return {
        "repo_data": repositories["totalCount"],
        "star_data": sum(node["stargazerCount"] for node in repositories["nodes"]),
        "contrib_data": user["contributionsCollection"]["contributionCalendar"][
            "totalContributions"
        ],
        "follower_data": user["followers"]["totalCount"],
    }


def update_svg(path: Path, values: dict[str, int]) -> None:
    text = path.read_text(encoding="utf-8")
    for element_id, value in values.items():
        pattern = rf'(<tspan[^>]*\bid="{element_id}"[^>]*>)[^<]*(</tspan>)'
        text, replacements = re.subn(pattern, rf"\g<1>{value:,}\g<2>", text)
        if replacements != 1:
            raise RuntimeError(f"Missing #{element_id} in {path.name}")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    figures = github_data()
    for svg_path in SVG_FILES:
        update_svg(svg_path, figures)
