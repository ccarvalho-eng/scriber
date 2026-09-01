"""Orchestrate a complete Scriber book build."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from scriber.cover import CoverBuild, build_cover, build_cover_template
from scriber.epub import EpubBuild, build_epub
from scriber.markdown import load_sections
from scriber.model import BookConfig
from scriber.pdf import PdfBuild, build_print_pdf
from scriber.profiles import CoverDimensions, get_profile
from scriber.report import write_metadata_sheet, write_proof_report
from scriber.validate import ValidationResult, validate_book


@dataclass(frozen=True)
class BookBuild:
    slug: str
    output_dir: Path
    pdf: PdfBuild
    epub: EpubBuild
    cover: CoverBuild | None
    cover_template: Path
    validation: ValidationResult
    proof_report: Path
    metadata_sheet: Path
    manifest: Path


def build_book(config: BookConfig, release: bool = False) -> BookBuild:
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
    cover_template = build_cover_template(config, pdf.page_count)
    epub = build_epub(
        config,
        sections,
        ebook_cover=cover.ebook_cover if cover else None,
    )
    dimensions_file = _write_dimensions(config, pdf, dimensions)
    validation = validate_book(
        config,
        strict_retailer=release,
        release=release,
    )
    artifact_paths = [pdf.path, epub.path, cover_template, dimensions_file]
    if cover:
        artifact_paths.extend([cover.print_pdf, cover.preview, cover.ebook_cover])
    metadata_sheet = write_metadata_sheet(config, pdf)
    artifact_paths.append(metadata_sheet)
    proof_report = write_proof_report(
        config,
        pdf,
        epub,
        validation,
        artifact_paths,
    )
    manifest = _write_manifest(
        config,
        pdf,
        epub,
        cover,
        cover_template,
        validation,
        proof_report,
        metadata_sheet,
    )
    return BookBuild(
        slug=config.slug,
        output_dir=config.output_dir,
        pdf=pdf,
        epub=epub,
        cover=cover,
        cover_template=cover_template,
        validation=validation,
        proof_report=proof_report,
        metadata_sheet=metadata_sheet,
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
        "profile_version": get_profile(config.publish.profile).version,
        "profile_source": get_profile(config.publish.profile).source_url,
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
    cover_template: Path,
    validation: ValidationResult,
    proof_report: Path,
    metadata_sheet: Path,
) -> Path:
    paths = [
        pdf.path,
        epub.path,
        config.output_dir / "dimensions.json",
        cover_template,
        proof_report,
        metadata_sheet,
    ]
    if cover:
        paths.extend([cover.print_pdf, cover.preview, cover.ebook_cover])
    values = {
        "schema_version": 2,
        "generated_at": f"{config.book.edition_date}T00:00:00+00:00",
        "book": {
            "slug": config.slug,
            "title": config.book.title,
            "subtitle": config.book.subtitle,
            "author": config.book.author,
            "language": config.book.language,
            "publisher": config.book.publisher,
            "imprint": config.book.imprint,
            "series": config.book.series,
            "series_number": config.book.series_number,
            "isbn_print": config.book.isbn_print,
            "isbn_epub": config.book.isbn_epub,
        },
        "profile": {
            "name": config.publish.profile,
            "version": get_profile(config.publish.profile).version,
            "source": get_profile(config.publish.profile).source_url,
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
        "cover_template": cover_template.relative_to(config.output_dir).as_posix(),
        "proof_report": proof_report.relative_to(config.output_dir).as_posix(),
        "metadata_sheet": metadata_sheet.relative_to(config.output_dir).as_posix(),
        "validation": {
            "valid": validation.valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
        },
        "files": {
            path.relative_to(config.output_dir).as_posix(): {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in paths
        },
    }
    output = config.output_dir / "publication_manifest.json"
    output.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    return output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
