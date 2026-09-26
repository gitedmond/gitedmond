"""Structural and idempotence tests for the generated profile cards."""

from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import render_profile  # noqa: E402
import update_profile_stats  # noqa: E402


NS = {"svg": "http://www.w3.org/2000/svg"}


class ProfileSvgTests(unittest.TestCase):
    def test_generated_files_match_the_canonical_renderer(self) -> None:
        stats = render_profile.read_existing_stats(ROOT / "dark_mode.svg")
        for theme in render_profile.THEMES:
            actual = (ROOT / f"{theme}_mode.svg").read_text(encoding="utf-8")
            self.assertEqual(actual, render_profile.render_svg(theme, stats))

    def test_reference_geometry_and_structure(self) -> None:
        expected_rows = list(range(30, 260, 20)) + [290, 310, 330, 350, 370, 430, 450, 470, 490]
        expected_palettes = {
            "dark": {
                "background": "#161b22",
                "text": "#c9d1d9",
                "key": "#ffa657",
                "value": "#a5d6ff",
                "muted": "#616e7f",
            },
            "light": {
                "background": "#f6f8fa",
                "text": "#24292f",
                "key": "#953800",
                "value": "#0a3069",
                "muted": "#c2cfde",
            },
        }
        expected_ids = {
            "repo_data_dots",
            "repo_data",
            "contrib_data",
            "star_data_dots",
            "star_data",
            "follower_data_dots",
            "follower_data",
            "commit_data_dots",
            "commit_data",
            "line_data_dots",
            "line_data",
            "addition_data",
            "deletion_data",
        }

        trees = {}
        for theme in render_profile.THEMES:
            path = ROOT / f"{theme}_mode.svg"
            tree = ET.parse(path)
            trees[theme] = tree
            root = tree.getroot()
            self.assertEqual(root.attrib["width"], "985px")
            self.assertEqual(root.attrib["height"], "530px")
            self.assertEqual(root.attrib["font-size"], "16px")
            self.assertEqual(
                root.attrib["font-family"], "ConsolasFallback,Consolas,monospace"
            )

            texts = root.findall("svg:text", NS)
            self.assertEqual(len(texts), 2)
            self.assertEqual(texts[0].attrib["x"], "15")
            self.assertEqual(texts[1].attrib["x"], "390")
            palette = expected_palettes[theme]
            self.assertEqual(root.find("svg:rect", NS).attrib["fill"], palette["background"])
            self.assertEqual(texts[0].attrib["fill"], palette["text"])
            self.assertEqual(texts[1].attrib["fill"], palette["text"])
            style = root.find("svg:style", NS).text or ""
            for color in (palette["key"], palette["value"], palette["muted"]):
                self.assertIn(color, style)
            self.assertIn("size-adjust: 109%", style)
            art_rows = texts[0].findall("svg:tspan", NS)
            self.assertEqual(len(art_rows), 25)
            self.assertTrue(all(len(row.text or "") <= 39 for row in art_rows))

            right_rows = [
                int(span.attrib["y"])
                for span in texts[1].findall("svg:tspan", NS)
                if span.attrib.get("x") == "390" and "y" in span.attrib
            ]
            self.assertEqual(right_rows, expected_rows)
            separator = next(
                span for span in texts[1].findall("svg:tspan", NS)
                if span.attrib.get("x") == "390" and span.attrib.get("y") == "190"
            )
            self.assertEqual(separator.text, ". ")
            ids = {
                span.attrib["id"]
                for span in root.findall(".//svg:tspan", NS)
                if "id" in span.attrib
            }
            self.assertEqual(ids, expected_ids)
            content = "".join(root.itertext())
            self.assertIn("edmond@gitedmond", content)
            self.assertIn("Languages.Programming", content)
            self.assertIn("Languages.Spoken", content)
            self.assertNotIn("Languages.Real", content)
            self.assertNotIn("Host:", content)
            self.assertNotIn("Kernel:", content)
            self.assertIn("Email.Personal", content)
            self.assertLess(content.index("Email.Personal"), content.index("Email.Work"))
            self.assertIn("Hobbies.Life", content)
            self.assertIn("Hobbies.Hardware", content)
            self.assertIn("Lines Changed", content)
            self.assertNotIn("[pending]", content)

        dark_spans = [
            (node.attrib, node.text)
            for node in trees["dark"].getroot().findall(".//svg:tspan", NS)
        ]
        light_spans = [
            (node.attrib, node.text)
            for node in trees["light"].getroot().findall(".//svg:tspan", NS)
        ]
        self.assertEqual(dark_spans, light_spans)

    def test_public_only_query(self) -> None:
        query = " ".join(update_profile_stats.QUERY.split())
        self.assertIn("privacy: PUBLIC", query)
        self.assertIn("repositoriesContributedTo", query)
        self.assertIn("includeUserRepositories: false", query)
        self.assertNotIn("contributionsCollection", query)
        contributed_query = " ".join(update_profile_stats.CONTRIBUTED_QUERY.split())
        self.assertIn("privacy: PUBLIC", contributed_query)
        self.assertIn("includeUserRepositories: true", contributed_query)
        self.assertIn("author: {id: $author}", update_profile_stats.COMMITS_QUERY)

    def test_commit_totals_page_and_deduplicate_public_history(self) -> None:
        def page(nodes, next_cursor=None):
            return {
                "nodes": nodes,
                "pageInfo": {
                    "hasNextPage": next_cursor is not None,
                    "endCursor": next_cursor,
                },
            }

        def graphql(query, variables):
            cursor = variables["cursor"]
            if query == update_profile_stats.QUERY:
                nodes = ([{"id": "A", "stargazerCount": 1}] if cursor is None
                         else [{"id": "B", "stargazerCount": 2}])
                return {"user": {
                    "id": "user-id",
                    "repositories": {"totalCount": 2, **page(nodes, "owner2" if cursor is None else None)},
                    "repositoriesContributedTo": {"totalCount": 1},
                    "followers": {"totalCount": 4},
                }}
            if query == update_profile_stats.CONTRIBUTED_QUERY:
                nodes = [{"id": "B" if cursor is None else "C"}]
                return {"user": {"repositoriesContributedTo": page(
                    nodes, "contrib2" if cursor is None else None
                )}}
            self.assertEqual(query, update_profile_stats.COMMITS_QUERY)
            self.assertEqual(variables["author"], "user-id")
            repo = variables["repository"]
            commits = {
                ("A", None): ([{"oid": "x", "additions": 2, "deletions": 1}], "hist2"),
                ("A", "hist2"): ([{"oid": "y", "additions": 5, "deletions": 2}], None),
                ("B", None): ([{"oid": "x", "additions": 2, "deletions": 1}], None),
                ("C", None): ([{"oid": "z", "additions": 1, "deletions": 3}], None),
            }
            nodes, next_cursor = commits[(repo, cursor)]
            return {"node": {
                "isPrivate": False,
                "defaultBranchRef": {"target": {"history": page(nodes, next_cursor)}},
            }}

        with patch.object(update_profile_stats, "_graphql", side_effect=graphql):
            self.assertEqual(update_profile_stats.github_data(), {
                "repo_data": 2,
                "contrib_data": 1,
                "star_data": 3,
                "follower_data": 4,
                "commit_data": 3,
                "line_data": 14,
                "addition_data": 8,
                "deletion_data": 6,
            })

    def test_stats_update_is_idempotent_and_preserves_placeholders(self) -> None:
        values = {
            "repo_data": 123,
            "contrib_data": 45,
            "star_data": 6,
            "follower_data": 7,
            "commit_data": 8,
            "line_data": 21,
            "addition_data": 13,
            "deletion_data": 8,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "card.svg"
            path.write_text(
                render_profile.render_svg("dark", render_profile.DEFAULT_STATS),
                encoding="utf-8",
            )
            self.assertTrue(update_profile_stats.update_svg(path, values))
            first = path.read_text(encoding="utf-8")
            self.assertFalse(update_profile_stats.update_svg(path, values))
            self.assertEqual(first, path.read_text(encoding="utf-8"))
            self.assertNotIn("[pending]", first)
            self.assertIn('id="line_data">21</tspan>', first)


if __name__ == "__main__":
    unittest.main()
