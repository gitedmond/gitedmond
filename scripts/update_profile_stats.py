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
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(
      first: 100
      after: $cursor
      ownerAffiliations: OWNER
      privacy: PUBLIC
    ) {
      totalCount
      nodes { stargazerCount }
      pageInfo { hasNextPage endCursor }
    }
    repositoriesContributedTo(
      first: 1
      includeUserRepositories: false
      privacy: PUBLIC
    ) { totalCount }
    followers { totalCount }
  }
}
"""


def github_data() -> dict[str, int]:
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ.get("PROFILE_USER", "gitedmond")
    cursor = None
    user = None
    stars = 0

    while True:
        request = Request(
            "https://api.github.com/graphql",
            data=json.dumps(
                {"query": QUERY, "variables": {"login": login, "cursor": cursor}}
            ).encode(),
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
        stars += sum(node["stargazerCount"] for node in repositories["nodes"])
        page_info = repositories["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    assert user is not None
    return {
        "repo_data": repositories["totalCount"],
        "contrib_data": user["repositoriesContributedTo"]["totalCount"],
        "star_data": stars,
        "follower_data": user["followers"]["totalCount"],
    }


def _dots(total_width: int, value: int) -> str:
    count = max(1, total_width - len(f"{value:,}") - 2)
    return f" {'.' * count} "


def svg_values(values: dict[str, int]) -> dict[str, str]:
    return {
        "repo_data_dots": _dots(8, values["repo_data"]),
        "repo_data": f'{values["repo_data"]:,}',
        "contrib_data": f'{values["contrib_data"]:,}',
        "star_data_dots": _dots(16, values["star_data"]),
        "star_data": f'{values["star_data"]:,}',
        "follower_data_dots": _dots(12, values["follower_data"]),
        "follower_data": f'{values["follower_data"]:,}',
    }


def update_svg(path: Path, values: dict[str, int]) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = original
    for element_id, value in svg_values(values).items():
        pattern = rf'(<tspan[^>]*\bid="{element_id}"[^>]*>)[^<]*(</tspan>)'
        updated, replacements = re.subn(
            pattern, lambda match: f"{match.group(1)}{value}{match.group(2)}", updated
        )
        if replacements != 1:
            raise RuntimeError(f"Missing #{element_id} in {path.name}")
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


if __name__ == "__main__":
    figures = github_data()
    for svg_path in SVG_FILES:
        update_svg(svg_path, figures)
