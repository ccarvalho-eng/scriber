from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from scriber.build import build_book
from scriber.config import discover_books
from scriber.scaffold import create_book
from scriber.validate import validate_book


class BuildTest(unittest.TestCase):
    def test_skeleton_builds_pdf_epub_and_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="winter-road",
                title="The Winter Road",
                author="Author Name",
            )
            chapter = workspace / "books/winter-road/manuscript/01_chapter.md"
            chapter.write_text(
                "# Chapter One\n\n" + ("A complete paragraph for pagination. " * 2000),
                encoding="utf-8",
            )
            config = discover_books(workspace)[0]
            result = build_book(config)

            self.assertTrue(result.pdf.path.exists())
            self.assertTrue(result.epub.path.exists())
            self.assertTrue((result.output_dir / "dimensions.json").exists())
            self.assertTrue(result.validation.valid)
            self.assertTrue(validate_book(config, strict_retailer=True).valid)
            self.assertEqual(len(PdfReader(str(result.pdf.path)).pages) % 2, 0)
            with zipfile.ZipFile(result.epub.path) as archive:
                self.assertEqual(archive.namelist()[0], "mimetype")
                self.assertIn("EPUB/package.opf", archive.namelist())

    def test_supplied_cover_panels_compile_after_pagination(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="covered-book",
                title="Covered Book",
                author="Author Name",
            )
            root = workspace / "books/covered-book"
            config_path = root / "book.toml"
            config_path.write_text(
                config_path.read_text(encoding="utf-8").replace(
                    "enabled = false",
                    "enabled = true",
                ),
                encoding="utf-8",
            )
            Image.new("RGB", (600, 960), "#1b3557").save(
                root / "assets/cover/front.png"
            )
            Image.new("RGB", (600, 960), "#57251b").save(root / "assets/cover/back.png")

            result = build_book(discover_books(workspace)[0])

            self.assertIsNotNone(result.cover)
            self.assertTrue(result.validation.valid)
            assert result.cover is not None
            self.assertTrue(result.cover.print_pdf.exists())
            self.assertTrue(result.cover.ebook_cover.exists())
            page = PdfReader(str(result.cover.print_pdf)).pages[0]
            width = float(page.mediabox.width) / 72
            self.assertAlmostEqual(
                width,
                result.cover.dimensions.width_inches,
                places=2,
            )


if __name__ == "__main__":
    unittest.main()
