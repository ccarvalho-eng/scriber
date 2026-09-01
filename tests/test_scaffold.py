from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from scriber.cli import main
from scriber.config import discover_books
from scriber.markdown import load_sections
from scriber.scaffold import create_book


class ScaffoldTest(unittest.TestCase):
    def test_new_cli_is_a_single_command_setup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with redirect_stdout(StringIO()):
                result = main(
                    [
                        "--workspace",
                        raw,
                        "new",
                        "one-command-book",
                        "--title",
                        "One Command Book",
                        "--author",
                        "Author Name",
                    ]
                )
            self.assertEqual(result, 0)
            self.assertTrue(Path(raw, "scriber.toml").exists())
            self.assertTrue(Path(raw, "books/one-command-book/book.toml").exists())

    def test_one_command_creates_workspace_and_complete_book(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            created = create_book(
                workspace=workspace,
                slug="winter-road",
                title="The Winter Road",
                subtitle="A Novel",
                author="Author Name",
            )

            self.assertTrue((workspace / "scriber.toml").exists())
            self.assertTrue((workspace / "books/winter-road/book.toml").exists())
            self.assertGreaterEqual(len(created), 8)
            books = discover_books(workspace)
            self.assertEqual([book.slug for book in books], ["winter-road"])
            sections = load_sections(books[0])
            self.assertEqual(
                [section.group for section in sections],
                ["front", "front", "front", "front", "body", "back", "back"],
            )

    def test_multiple_books_are_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            for slug, title in (("book-one", "Book One"), ("book-two", "Book Two")):
                create_book(
                    workspace=workspace,
                    slug=slug,
                    title=title,
                    author="Author Name",
                )
            self.assertEqual(
                [book.slug for book in discover_books(workspace)],
                ["book-one", "book-two"],
            )


if __name__ == "__main__":
    unittest.main()
