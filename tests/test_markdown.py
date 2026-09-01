from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scriber.markdown import parse_section


class MarkdownTest(unittest.TestCase):
    def test_parses_emphasis_quotes_lists_and_scene_breaks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "01_chapter.md"
            source.write_text(
                "# Chapter One\n\n"
                "A paragraph with *emphasis*.\n\n"
                "> A quotation.\n\n"
                "- One item\n\n"
                "1. First note\n\n"
                "::: note\n"
                "Meet me by the gate.\n\n"
                "— Elin\n"
                ":::\n\n"
                "* * *\n\n"
                "After the break.\n",
                encoding="utf-8",
            )
            section = parse_section(source, "body")

            self.assertEqual(section.kind, "chapter")
            self.assertEqual(
                [block.kind for block in section.blocks],
                [
                    "paragraph",
                    "quote",
                    "list_item",
                    "ordered_item",
                    "note",
                    "scene",
                    "paragraph",
                ],
            )
            self.assertIn("— Elin", section.blocks[4].text)

    def test_requires_an_h1_title(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "untitled.md"
            source.write_text("No heading.", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "H1 title"):
                parse_section(source, "body")

    def test_rejects_an_unclosed_character_document(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            source = Path(raw) / "01_chapter.md"
            source.write_text(
                "# Chapter One\n\n::: letter\nDear reader,\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Unclosed"):
                parse_section(source, "body")


if __name__ == "__main__":
    unittest.main()
