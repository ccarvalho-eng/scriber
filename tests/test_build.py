from __future__ import annotations

import tempfile
import unittest
import zipfile
from hashlib import sha256
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
            chapter = workspace / "books/winter-road/manuscript/chapters/01_chapter.md"
            chapter.write_text(
                "# Chapter One\n\n" + ("A complete paragraph for pagination. " * 2000),
                encoding="utf-8",
            )
            config = discover_books(workspace)[0]
            result = build_book(config)

            self.assertTrue(result.pdf.path.exists())
            self.assertTrue(result.epub.path.exists())
            self.assertTrue((result.output_dir / "dimensions.json").exists())
            self.assertEqual(result.pdf.path.parent.name, "pdf")
            self.assertEqual(result.epub.path.parent.name, "epub")
            self.assertEqual(result.cover_template.parent.name, "cover")
            self.assertEqual(result.manifest.name, "publication_manifest.json")
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
            first_hashes = {
                path.name: _digest(path)
                for path in (
                    result.cover.print_pdf,
                    result.cover.preview,
                    result.cover.ebook_cover,
                )
            }
            rebuilt = build_book(discover_books(workspace)[0])
            assert rebuilt.cover is not None
            second_hashes = {
                path.name: _digest(path)
                for path in (
                    rebuilt.cover.print_pdf,
                    rebuilt.cover.preview,
                    rebuilt.cover.ebook_cover,
                )
            }
            self.assertEqual(first_hashes, second_hashes)

    def test_build_outputs_are_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="stable-book",
                title="Stable Book",
                author="Author Name",
            )
            config = discover_books(workspace)[0]
            first = build_book(config)
            first_hashes = {
                path.relative_to(first.output_dir): _digest(path)
                for path in (
                    first.pdf.path,
                    first.epub.path,
                    first.cover_template,
                    first.manifest,
                )
            }

            second = build_book(config)
            second_hashes = {
                path.relative_to(second.output_dir): _digest(path)
                for path in (
                    second.pdf.path,
                    second.epub.path,
                    second.cover_template,
                    second.manifest,
                )
            }

            self.assertEqual(first_hashes, second_hashes)

    def test_body_chapters_start_on_recto_pages(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="recto-book",
                title="Recto Book",
                author="Author Name",
            )
            chapters = workspace / "books/recto-book/manuscript/chapters"
            (chapters / "02_second.md").write_text(
                "# Chapter Two\n\nSecond chapter.",
                encoding="utf-8",
            )
            result = build_book(discover_books(workspace)[0])
            chapter_pages = [
                page
                for identifier, page in result.pdf.section_pages.items()
                if "chapter" in identifier or "second" in identifier
            ]
            self.assertEqual(len(chapter_pages), 2)
            self.assertTrue(all(page % 2 == 1 for page in chapter_pages))

    def test_character_note_renders_in_print_and_epub(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="note-book",
                title="Note Book",
                author="Author Name",
            )
            chapter = workspace / "books/note-book/manuscript/chapters/01_chapter.md"
            chapter.write_text(
                "# Chapter One\n\n"
                "Mara unfolded the paper.\n\n"
                "::: note\nMeet me at the north gate.\n\n— Elin\n:::\n\n"
                "* * *\n",
                encoding="utf-8",
            )

            result = build_book(discover_books(workspace)[0])

            print_text = "\n".join(
                page.extract_text() or ""
                for page in PdfReader(str(result.pdf.path)).pages
            )
            self.assertIn("Meet me at the north gate.", print_text)
            with zipfile.ZipFile(result.epub.path) as archive:
                sections = "\n".join(
                    archive.read(name).decode("utf-8")
                    for name in archive.namelist()
                    if name.startswith("EPUB/text/section-")
                )
            self.assertIn('class="character-document note"', sections)
            self.assertIn("Meet me at the north gate.", sections)


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
