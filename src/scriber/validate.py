"""Validate generated Scriber outputs."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader

from scriber.model import BookConfig
from scriber.profiles import get_profile


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_book(config: BookConfig, strict_retailer: bool = True) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    interior = config.output_dir / "paperback-interior.pdf"
    epub = config.output_dir / "book.epub"
    if interior.exists():
        _validate_interior(config, interior, errors, warnings, strict_retailer)
    else:
        errors.append("Missing paperback-interior.pdf")
    if epub.exists():
        _validate_epub(epub, errors)
    else:
        errors.append("Missing book.epub")
    if config.cover.enabled:
        _validate_cover(config, interior, errors)
    return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))


def _validate_interior(
    config: BookConfig,
    path: Path,
    errors: list[str],
    warnings: list[str],
    strict_retailer: bool,
) -> None:
    profile = get_profile(config.publish.profile)
    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    if not reader.pages:
        errors.append("Paperback interior contains no pages")
        return
    if page_count % 2:
        errors.append("Paperback interior page count must be even")
    if page_count < profile.minimum_pages:
        message = (
            f"Paperback has {page_count} pages; profile minimum is "
            f"{profile.minimum_pages}"
        )
        if strict_retailer:
            errors.append(message)
        else:
            warnings.append(message)
    if page_count > config.publish.max_pages:
        errors.append(
            f"Paperback has {page_count} pages; configured maximum is "
            f"{config.publish.max_pages}"
        )

    width = float(reader.pages[0].mediabox.width) / 72
    height = float(reader.pages[0].mediabox.height) / 72
    expected = (
        config.layout.trim_width_inches,
        config.layout.trim_height_inches,
    )
    if abs(width - expected[0]) > 0.001 or abs(height - expected[1]) > 0.001:
        errors.append(
            f"Interior trim is {width:.3f} x {height:.3f}; expected "
            f"{expected[0]:.3f} x {expected[1]:.3f} inches"
        )
    unembedded = _unembedded_fonts(reader)
    if unembedded:
        errors.append(f"Interior contains unembedded fonts: {sorted(unembedded)}")


def _validate_epub(path: Path, errors: list[str]) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.namelist()[0] != "mimetype":
                errors.append("EPUB mimetype must be the first archive entry")
            if archive.read("mimetype") != b"application/epub+zip":
                errors.append("EPUB has an invalid mimetype")
            required = {
                "META-INF/container.xml",
                "EPUB/package.opf",
                "EPUB/nav.xhtml",
            }
            missing = required.difference(archive.namelist())
            if missing:
                errors.append(f"EPUB is missing files: {sorted(missing)}")
            for name in archive.namelist():
                if name.endswith((".xml", ".xhtml", ".opf")):
                    ElementTree.fromstring(archive.read(name))
    except (
        KeyError,
        OSError,
        ValueError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
    ) as error:
        errors.append(f"Invalid EPUB package: {error}")


def _validate_cover(config: BookConfig, interior: Path, errors: list[str]) -> None:
    cover = config.output_dir / "paperback-cover.pdf"
    ebook_cover = config.output_dir / "ebook-cover.jpg"
    if not cover.exists():
        errors.append("Missing paperback-cover.pdf")
        return
    if not ebook_cover.exists():
        errors.append("Missing ebook-cover.jpg")
    if not interior.exists():
        return
    page_count = len(PdfReader(str(interior)).pages)
    expected = get_profile(config.publish.profile).cover_dimensions(
        page_count=page_count,
        trim_width_inches=config.layout.trim_width_inches,
        trim_height_inches=config.layout.trim_height_inches,
        ink=config.publish.ink,
        paper=config.publish.paper,
    )
    reader = PdfReader(str(cover))
    if len(reader.pages) != 1:
        errors.append("Paperback cover must be a single-page PDF")
        return
    page = reader.pages[0]
    width = float(page.mediabox.width) / 72
    height = float(page.mediabox.height) / 72
    if abs(width - expected.width_inches) > 0.01:
        errors.append(
            f"Cover width is {width:.3f}; expected {expected.width_inches:.3f} inches"
        )
    if abs(height - expected.height_inches) > 0.01:
        errors.append(
            f"Cover height is {height:.3f}; expected {expected.height_inches:.3f} inches"
        )


def _unembedded_fonts(reader: PdfReader) -> set[str]:
    unembedded: set[str] = set()
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        fonts = resources.get("/Font") or {}
        for reference in fonts.values():
            font = reference.get_object()
            descriptor_reference = font.get("/FontDescriptor")
            if descriptor_reference is None:
                descendants = font.get("/DescendantFonts") or []
                if descendants:
                    descendant = descendants[0].get_object()
                    descriptor_reference = descendant.get("/FontDescriptor")
            descriptor = (
                descriptor_reference.get_object() if descriptor_reference else None
            )
            embedded = descriptor and any(
                key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")
            )
            if not embedded:
                unembedded.add(str(font.get("/BaseFont", "unknown")))
    return unembedded
