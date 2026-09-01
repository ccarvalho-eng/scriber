from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scriber.build import build_book
from scriber.config import discover_books
from scriber.scaffold import create_book
from scriber.validate import validate_book


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

    def test_standard_color_uses_its_seventy_two_page_minimum(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="color-book",
                title="Color Book",
                author="Author Name",
            )
            source = workspace / "books/color-book/book.toml"
            source.write_text(
                source.read_text(encoding="utf-8")
                .replace('ink = "black"', 'ink = "standard-color"')
                .replace('paper = "cream"', 'paper = "white"'),
                encoding="utf-8",
            )

            result = build_book(discover_books(workspace)[0])

            self.assertTrue(
                any(
                    "profile minimum is 72" in warning
                    for warning in result.validation.warnings
                )
            )

    def test_unknown_trim_is_a_release_error_and_draft_warning(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="custom-trim",
                title="Custom Trim",
                author="Author Name",
            )
            source = workspace / "books/custom-trim/book.toml"
            source.write_text(
                source.read_text(encoding="utf-8")
                .replace("trim_width_inches = 6.0", "trim_width_inches = 6.1")
                .replace("trim_height_inches = 9.0", "trim_height_inches = 9.1"),
                encoding="utf-8",
            )
            config = discover_books(workspace)[0]

            draft = build_book(config)

            self.assertTrue(
                any(
                    "not a verified" in warning for warning in draft.validation.warnings
                )
            )
            strict = validate_book(config, strict_retailer=True)
            self.assertTrue(any("not a verified" in error for error in strict.errors))


if __name__ == "__main__":
    unittest.main()
