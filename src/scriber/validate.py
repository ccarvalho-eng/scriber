"""Validate generated Scriber outputs."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader

from scriber.cover import cover_source_warnings
from scriber.model import BookConfig
from scriber.profiles import get_profile


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checks: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_book(
    config: BookConfig,
    strict_retailer: bool = True,
    release: bool = False,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    checks: list[str] = []
    interior = config.pdf_dir / f"{config.slug}_kdp_interior.pdf"
    epub = config.epub_dir / f"{config.slug}.epub"
    if interior.exists():
        _validate_interior(config, interior, errors, warnings, strict_retailer)
        checks.append("print-interior")
    else:
        errors.append(f"Missing {interior.relative_to(config.root)}")
    if epub.exists():
        _validate_epub(epub, errors)
        checks.append("epub-package")
    else:
        errors.append(f"Missing {epub.relative_to(config.root)}")
    if config.cover.enabled:
        _validate_cover(config, interior, errors, warnings, release)
        checks.append("cover")
    _validate_metadata(config, errors, warnings, release)
    checks.append("metadata")
    if release and epub.exists():
        if _run_epubcheck(epub, errors):
            checks.append("epubcheck")
        if _run_ace(epub, errors, warnings):
            checks.append("ace")
    return ValidationResult(
        errors=tuple(errors),
        warnings=tuple(warnings),
        checks=tuple(checks),
    )


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
    minimum_outer = profile.minimum_outside_margin(config.publish.interior_bleed)
    for label, margin in (
        ("outside", config.layout.outside_margin_inches),
        ("top", config.layout.top_margin_inches),
        ("bottom", config.layout.bottom_margin_inches),
    ):
        if margin < minimum_outer:
            errors.append(
                f"{label.capitalize()} margin is {margin:.3f}; profile minimum is "
                f"{minimum_outer:.3f} inches"
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


def _validate_cover(
    config: BookConfig,
    interior: Path,
    errors: list[str],
    warnings: list[str],
    release: bool,
) -> None:
    cover = config.cover_dir / f"{config.slug}_paperback_cover.pdf"
    ebook_cover = config.cover_dir / f"{config.slug}_ebook_cover.jpg"
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
    source_warnings = cover_source_warnings(config, expected)
    if release:
        errors.extend(source_warnings)
    else:
        warnings.extend(source_warnings)
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


def available_release_tools() -> dict[str, str | None]:
    """Return the validators Scriber can invoke in the current environment."""

    epubcheck = shutil.which("epubcheck")
    if epubcheck and not _command_available([epubcheck, "--version"]):
        epubcheck = None
    jar = os.environ.get("EPUBCHECK_JAR")
    java = shutil.which("java")
    if (
        epubcheck is None
        and jar
        and Path(jar).is_file()
        and java
        and _command_available([java, "-jar", jar, "--version"])
    ):
        epubcheck = f"java -jar {jar}"
    ace = shutil.which("ace")
    if ace and not _command_available([ace, "--version"]):
        ace = None
    return {
        "epubcheck": epubcheck,
        "ace": ace,
    }


def _command_available(arguments: list[str]) -> bool:
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _validate_metadata(
    config: BookConfig,
    errors: list[str],
    warnings: list[str],
    release: bool,
) -> None:
    try:
        date.fromisoformat(config.book.edition_date)
    except ValueError:
        errors.append("book.edition_date must be an ISO date in YYYY-MM-DD form")
    if not 1000 <= config.book.copyright_year <= 9999:
        errors.append("book.copyright_year must use four digits")
    if not _valid_language_tag(config.book.language):
        errors.append("book.language must be a simple BCP 47 language tag")
    for label, value in (
        ("book.isbn_print", config.book.isbn_print),
        ("book.isbn_epub", config.book.isbn_epub),
    ):
        if value and not _valid_isbn(value):
            errors.append(f"{label} is not a valid ISBN-10 or ISBN-13")
    if release and not config.book.description:
        warnings.append(
            "book.description is empty; add retailer copy before publishing"
        )
    if release and not (config.book.publisher or config.book.imprint):
        warnings.append("book.publisher and book.imprint are empty")


def _valid_language_tag(value: str) -> bool:
    parts = value.split("-")
    return (
        bool(parts)
        and len(parts[0]) in {2, 3}
        and parts[0].isalpha()
        and all(1 <= len(part) <= 8 and part.isalnum() for part in parts[1:])
    )


def _valid_isbn(value: str) -> bool:
    compact = "".join(character for character in value if character not in " -")
    if len(compact) == 10:
        if not compact[:9].isdigit() or not (
            compact[-1].isdigit() or compact[-1].upper() == "X"
        ):
            return False
        digits = [int(character) for character in compact[:9]]
        check = 10 if compact[-1].upper() == "X" else int(compact[-1])
        return (
            sum((10 - index) * digit for index, digit in enumerate(digits + [check]))
            % 11
            == 0
        )
    if len(compact) == 13 and compact.isdigit():
        total = sum(
            int(character) * (1 if index % 2 == 0 else 3)
            for index, character in enumerate(compact[:12])
        )
        return (10 - total % 10) % 10 == int(compact[-1])
    return False


def _run_epubcheck(epub: Path, errors: list[str]) -> bool:
    tools = available_release_tools()
    command = tools["epubcheck"]
    if command is None:
        errors.append(
            "EPUBCheck is required for release builds; install the epubcheck "
            "command or set EPUBCHECK_JAR"
        )
        return False
    executable = shutil.which("epubcheck")
    if executable:
        arguments = [executable, str(epub)]
    else:
        jar = os.environ.get("EPUBCHECK_JAR")
        java = shutil.which("java")
        if not jar or not java:
            errors.append("EPUBCheck configuration is incomplete")
            return False
        arguments = [java, "-jar", jar, str(epub)]
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            check=False,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        errors.append(f"EPUBCheck could not complete: {error}")
        return True
    if result.returncode:
        summary = _command_summary(result.stdout, result.stderr)
        errors.append(f"EPUBCheck failed: {summary}")
    return True


def _run_ace(
    epub: Path,
    errors: list[str],
    warnings: list[str],
) -> bool:
    command = available_release_tools()["ace"]
    if command is None:
        warnings.append("Ace by DAISY is unavailable; accessibility audit was skipped")
        return False
    with tempfile.TemporaryDirectory(prefix="scriber-ace-") as destination:
        try:
            result = subprocess.run(
                [command, "-o", destination, str(epub)],
                capture_output=True,
                check=False,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            errors.append(f"Ace accessibility audit could not complete: {error}")
            return True
    if result.returncode:
        summary = _command_summary(result.stdout, result.stderr)
        errors.append(f"Ace accessibility audit failed: {summary}")
    return True


def _command_summary(stdout: str, stderr: str) -> str:
    lines = [
        line.strip() for line in (stdout + "\n" + stderr).splitlines() if line.strip()
    ]
    return " | ".join(lines[-5:]) or "validator returned a non-zero exit status"


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
