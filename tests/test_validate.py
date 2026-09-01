from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scriber.build import build_book
from scriber.config import discover_books
from scriber.scaffold import create_book


class ValidationTest(unittest.TestCase):
    def test_invalid_isbn_fails_a_build(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="isbn-book",
                title="ISBN Book",
                author="Author Name",
            )
            source = workspace / "books/isbn-book/book.toml"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    'isbn_print = ""',
                    'isbn_print = "9780000000000"',
                ),
                encoding="utf-8",
            )

            result = build_book(discover_books(workspace)[0])

            self.assertFalse(result.validation.valid)
            self.assertTrue(
                any("isbn_print" in error for error in result.validation.errors)
            )

    def test_release_runs_epubcheck_and_reports_retailer_limits(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="release-book",
                title="Release Book",
                author="Author Name",
            )
            completed = subprocess.CompletedProcess(
                args=["epubcheck"],
                returncode=0,
                stdout="No errors",
                stderr="",
            )
            with (
                patch(
                    "scriber.validate.available_release_tools",
                    return_value={"epubcheck": "epubcheck", "ace": None},
                ),
                patch("scriber.validate.subprocess.run", return_value=completed),
            ):
                result = build_book(discover_books(workspace)[0], release=True)

            self.assertIn("epubcheck", result.validation.checks)
            self.assertTrue(
                any("profile minimum" in error for error in result.validation.errors)
            )
            self.assertTrue(
                any("Ace by DAISY" in warning for warning in result.validation.warnings)
            )


if __name__ == "__main__":
    unittest.main()
