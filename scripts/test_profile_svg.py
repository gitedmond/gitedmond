"""Structural and idempotence tests for the generated profile cards."""

from __future__ import annotations

import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


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
        expected_rows = list(range(30, 280, 20)) + [310, 330, 350, 370, 390, 410, 450, 470, 490, 510]
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

            ids = {
                span.attrib["id"]
                for span in root.findall(".//svg:tspan", NS)
                if "id" in span.attrib
            }
            self.assertEqual(ids, expected_ids)
            content = "".join(root.itertext())
            self.assertIn("edmond@gitedmond", content)
            self.assertIn("Languages.Programming", content)
            self.assertIn("Hobbies.Hardware", content)
            self.assertIn("Lines of Code on GitHub", content)
            self.assertEqual(content.count("[pending]"), 4)

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

    def test_stats_update_is_idempotent_and_preserves_placeholders(self) -> None:
        values = {
            "repo_data": 123,
            "contrib_data": 45,
            "star_data": 6,
            "follower_data": 7,
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
            self.assertEqual(first.count("[pending]"), 4)


if __name__ == "__main__":
    unittest.main()
