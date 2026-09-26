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
    id
    repositories(
      first: 100
      after: $cursor
      ownerAffiliations: OWNER
      privacy: PUBLIC
    ) {
      totalCount
      nodes { id stargazerCount }
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

CONTRIBUTED_QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    repositoriesContributedTo(
      first: 100
      after: $cursor
      includeUserRepositories: true
      privacy: PUBLIC
    ) {
      nodes { id }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

COMMITS_QUERY = """
query($repository: ID!, $author: ID!, $cursor: String) {
  node(id: $repository) {
    ... on Repository {
      isPrivate
      defaultBranchRef {
        target {
          ... on Commit {
            history(first: 100, after: $cursor, author: {id: $author}) {
              nodes { oid additions deletions }
              pageInfo { hasNextPage endCursor }
            }
          }
        }
      }
    }
  }
}
"""


def _graphql(query: str, variables: dict[str, str | None]) -> dict:
    token = os.environ["GITHUB_TOKEN"]
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
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
    return payload["data"]


def github_data() -> dict[str, int]:
    """Count authored commits and changed lines on public default branches."""
    login = os.environ.get("PROFILE_USER", "gitedmond")
    cursor = None
    repo_ids = set()
    stars = 0

    while True:
        user = _graphql(QUERY, {"login": login, "cursor": cursor})["user"]
        if user is None:
            raise RuntimeError(f"GitHub user {login!r} not found")
        user_id = user["id"]
        repositories = user["repositories"]
        stars += sum(node["stargazerCount"] for node in repositories["nodes"])
        repo_ids.update(node["id"] for node in repositories["nodes"])
        page_info = repositories["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    cursor = None
    while True:
        contributed = _graphql(
            CONTRIBUTED_QUERY, {"login": login, "cursor": cursor}
        )["user"]["repositoriesContributedTo"]
        repo_ids.update(node["id"] for node in contributed["nodes"])
        page_info = contributed["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    seen_commits = set()
    additions = deletions = 0
    for repo_id in sorted(repo_ids):
        cursor = None
        while True:
            repository = _graphql(
                COMMITS_QUERY,
                {"repository": repo_id, "author": user_id, "cursor": cursor},
            )["node"]
            if repository is None or repository["isPrivate"]:
                raise RuntimeError(f"Expected a public repository for {repo_id}")
            branch = repository["defaultBranchRef"]
            if branch is None:
                break
            history = branch["target"]["history"]
            for commit in history["nodes"]:
                if commit["oid"] in seen_commits:
                    continue
                seen_commits.add(commit["oid"])
                additions += commit["additions"]
                deletions += commit["deletions"]
            page_info = history["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

    return {
        "repo_data": repositories["totalCount"],
        "contrib_data": user["repositoriesContributedTo"]["totalCount"],
        "star_data": stars,
        "follower_data": user["followers"]["totalCount"],
        "commit_data": len(seen_commits),
        "line_data": additions + deletions,
        "addition_data": additions,
        "deletion_data": deletions,
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
        "commit_data_dots": _dots(20, values["commit_data"]),
        "commit_data": f'{values["commit_data"]:,}',
        "line_data_dots": _dots(4, values["line_data"]),
        "line_data": f'{values["line_data"]:,}',
        "addition_data": f'{values["addition_data"]:,}',
        "deletion_data": f'{values["deletion_data"]:,}',
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
