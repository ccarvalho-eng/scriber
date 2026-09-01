from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scriber.config import discover_books
from scriber.scaffold import create_book


class ConfigTest(unittest.TestCase):
    def test_new_book_uses_convention_content_without_contents_table(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="convention-book",
                title="Convention Book",
                author="Author Name",
            )
            config = discover_books(workspace)[0]
            content = config.source.read_text(encoding="utf-8")

            self.assertNotIn("[contents]", content)
            self.assertEqual(
                config.contents.body,
                ("manuscript/chapters/*.md",),
            )
            self.assertEqual(config.schema_version, 2)
            self.assertNotIn("max_pages", content)

    def test_partial_custom_font_family_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="font-book",
                title="Font Book",
                author="Author Name",
            )
            source = workspace / "books/font-book/book.toml"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "[typography]\n",
                    '[typography]\nregular = "assets/fonts/regular.ttf"\n',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "requires regular"):
                discover_books(workspace)

    def test_cover_paths_cannot_escape_book_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="safe-book",
                title="Safe Book",
                author="Author Name",
            )
            source = workspace / "books/safe-book/book.toml"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    'front = "assets/cover/front.png"',
                    'front = "../front.png"',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "escapes"):
                discover_books(workspace)

    def test_invalid_edition_date_is_rejected_before_build(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="date-book",
                title="Date Book",
                author="Author Name",
            )
            source = workspace / "books/date-book/book.toml"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    'edition_date = "',
                    'edition_date = "not-a-date',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                discover_books(workspace)

    def test_boolean_options_require_toml_booleans(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="boolean-book",
                title="Boolean Book",
                author="Author Name",
            )
            source = workspace / "books/boolean-book/book.toml"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "chapter_start_recto = true",
                    'chapter_start_recto = "false"',
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(TypeError, "must be true or false"):
                discover_books(workspace)


if __name__ == "__main__":
    unittest.main()
