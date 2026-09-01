"""Orchestrate a complete Scriber book build."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scriber.cover import CoverBuild, build_cover
from scriber.epub import EpubBuild, build_epub
from scriber.markdown import load_sections
from scriber.model import BookConfig
from scriber.pdf import PdfBuild, build_print_pdf
from scriber.profiles import CoverDimensions, get_profile
from scriber.validate import ValidationResult, validate_book


@dataclass(frozen=True)
class BookBuild:
    slug: str
    output_dir: Path
    pdf: PdfBuild
    epub: EpubBuild
    cover: CoverBuild | None
    validation: ValidationResult
    manifest: Path


def build_book(config: BookConfig) -> BookBuild:
    sections = load_sections(config)
    pdf = build_print_pdf(config, sections)
    dimensions = get_profile(config.publish.profile).cover_dimensions(
        page_count=pdf.page_count,
        trim_width_inches=config.layout.trim_width_inches,
        trim_height_inches=config.layout.trim_height_inches,
        ink=config.publish.ink,
        paper=config.publish.paper,
    )
    cover = build_cover(config, pdf.page_count)
    epub = build_epub(
        config,
        sections,
        ebook_cover=cover.ebook_cover if cover else None,
    )
    _write_dimensions(config, pdf, dimensions)
    validation = validate_book(config, strict_retailer=False)
    manifest = _write_manifest(config, pdf, epub, cover, validation)
    return BookBuild(
        slug=config.slug,
        output_dir=config.output_dir,
        pdf=pdf,
        epub=epub,
        cover=cover,
        validation=validation,
        manifest=manifest,
    )


def _write_dimensions(
    config: BookConfig,
    pdf: PdfBuild,
    cover: CoverDimensions,
) -> Path:
    output = config.output_dir / "dimensions.json"
    values = {
        "profile": config.publish.profile,
        "page_count": pdf.page_count,
        "trim_inches": [
            config.layout.trim_width_inches,
            config.layout.trim_height_inches,
        ],
        "inside_margin_inches": pdf.inside_margin_inches,
        "cover": {
            "bleed_inches": cover.bleed_inches,
            "spine_inches": round(cover.spine_inches, 6),
            "width_inches": round(cover.width_inches, 6),
            "height_inches": round(cover.height_inches, 6),
        },
    }
    output.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    return output


def _write_manifest(
    config: BookConfig,
    pdf: PdfBuild,
    epub: EpubBuild,
    cover: CoverBuild | None,
    validation: ValidationResult,
) -> Path:
    paths = [
        pdf.path,
        epub.path,
        config.output_dir / "dimensions.json",
    ]
    if cover:
        paths.extend([cover.print_pdf, cover.preview, cover.ebook_cover])
    values = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "book": {
            "slug": config.slug,
            "title": config.book.title,
            "subtitle": config.book.subtitle,
            "author": config.book.author,
            "language": config.book.language,
        },
        "profile": {
            "name": config.publish.profile,
            "version": get_profile(config.publish.profile).version,
            "format": config.publish.format,
            "ink": config.publish.ink,
            "paper": config.publish.paper,
        },
        "interior": {
            "path": pdf.path.name,
            "page_count": pdf.page_count,
            "layout_passes": pdf.passes,
            "inside_margin_inches": pdf.inside_margin_inches,
            "section_pages": pdf.section_pages,
        },
        "epub": {
            "path": epub.path.name,
            "identifier": epub.identifier,
            "sections": epub.sections,
        },
        "cover_compiled": cover is not None,
        "validation": {
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
        },
        "files": {
            path.name: {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in paths
        },
    }
    output = config.output_dir / "build-manifest.json"
    output.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    return output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
