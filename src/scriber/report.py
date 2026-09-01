"""Generate deterministic, author-readable release reports."""

from __future__ import annotations

from html import escape
from pathlib import Path

from scriber.epub import EpubBuild
from scriber.model import BookConfig
from scriber.pdf import PdfBuild
from scriber.profiles import get_profile
from scriber.validate import ValidationResult


def write_proof_report(
    config: BookConfig,
    pdf: PdfBuild,
    epub: EpubBuild,
    validation: ValidationResult,
    artifact_paths: list[Path],
) -> Path:
    """Write a self-contained HTML report for reviewing a build."""

    status = "READY" if validation.valid and not validation.warnings else "REVIEW"
    if validation.errors:
        status = "BLOCKED"
    sections = "\n".join(
        f"<tr><td>{escape(identifier)}</td><td>{page}</td></tr>"
        for identifier, page in pdf.section_pages.items()
    )
    artifacts = "\n".join(
        f'<li><a href="{escape(path.relative_to(config.output_dir).as_posix())}">'
        f"{escape(path.relative_to(config.output_dir).as_posix())}</a></li>"
        for path in artifact_paths
        if path.exists()
    )
    artifacts += (
        '\n<li><a href="publication_manifest.json">publication_manifest.json</a></li>'
    )
    errors = _html_messages(validation.errors, "No blocking errors.")
    warnings = _html_messages(validation.warnings, "No warnings.")
    checks = ", ".join(escape(check) for check in validation.checks)
    output = config.output_dir / "proof_report.html"
    output.write_text(
        "<!doctype html>\n"
        f'<html lang="{escape(config.book.language)}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(config.book.full_title)} — Scriber proof</title>\n"
        "<style>\n"
        ":root{color-scheme:light dark;font-family:system-ui,sans-serif}"
        "body{max-width:70rem;margin:3rem auto;padding:0 1.5rem;line-height:1.5}"
        ".status{display:inline-block;padding:.25rem .6rem;border:1px solid;"
        "border-radius:.3rem;font-weight:700}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border-bottom:1px solid #8886;padding:.45rem;text-align:left}"
        "code{font-size:.9em}"
        "</style>\n"
        "</head>\n<body>\n"
        f"<h1>{escape(config.book.full_title)}</h1>\n"
        f"<p>{escape(config.book.author)}</p>\n"
        f'<p class="status">{status}</p>\n'
        "<h2>Edition</h2>\n"
        "<dl>"
        f"<dt>Profile</dt><dd>{escape(config.publish.profile)}</dd>"
        f"<dt>Page count</dt><dd>{pdf.page_count}</dd>"
        f"<dt>Trim</dt><dd>{config.layout.trim_width_inches:g} × "
        f"{config.layout.trim_height_inches:g} in</dd>"
        f"<dt>Ink and paper</dt><dd>{escape(config.publish.ink)} / "
        f"{escape(config.publish.paper)}</dd>"
        f"<dt>Validation checks</dt><dd>{checks}</dd>"
        "</dl>\n"
        f"<h2>Blocking errors</h2>\n{errors}\n"
        f"<h2>Warnings</h2>\n{warnings}\n"
        "<h2>Section starts</h2>\n"
        "<table><thead><tr><th>Section</th><th>Page</th></tr></thead>"
        f"<tbody>{sections}</tbody></table>\n"
        f"<h2>Artifacts</h2>\n<ul>{artifacts}</ul>\n"
        f"<p>EPUB identifier: <code>{escape(epub.identifier)}</code></p>\n"
        "</body>\n</html>\n",
        encoding="utf-8",
    )
    return output


def write_metadata_sheet(config: BookConfig, pdf: PdfBuild) -> Path:
    """Write retailer metadata in a copy-friendly Markdown document."""

    profile = get_profile(config.publish.profile)
    try:
        minimum_pages, maximum_pages = profile.page_limits(
            config.layout.trim_width_inches,
            config.layout.trim_height_inches,
            config.publish.ink,
            config.publish.paper,
        )
        page_range = f"{minimum_pages}–{maximum_pages}"
    except ValueError:
        page_range = "Unverified by the active Scriber profile"
    values = (
        ("Title", config.book.title),
        ("Subtitle", config.book.subtitle),
        ("Author", config.book.author),
        ("Language", config.book.language),
        ("Publisher", config.book.publisher),
        ("Imprint", config.book.imprint),
        ("Series", config.book.series),
        ("Series number", config.book.series_number),
        ("Print ISBN", config.book.isbn_print),
        ("EPUB ISBN", config.book.isbn_epub),
        ("Edition date", config.book.edition_date),
        ("Subjects", ", ".join(config.book.subjects)),
        ("Publishing profile", config.publish.profile),
        ("Format", config.publish.format),
        ("Ink", config.publish.ink),
        ("Paper", config.publish.paper),
        (
            "Trim",
            (
                f"{config.layout.trim_width_inches:g} × "
                f"{config.layout.trim_height_inches:g} inches"
            ),
        ),
        ("Final page count", str(pdf.page_count)),
        ("Allowed page range", page_range),
    )
    rows = "\n".join(
        f"| {label} | {_markdown_cell(value) if value else 'Not set'} |"
        for label, value in values
    )
    description = config.book.description or "Not set"
    if config.cover.enabled:
        cover_files = (
            f"- Print cover: `cover/{config.slug}_paperback_cover.pdf`\n"
            f"- Ebook cover: `cover/{config.slug}_ebook_cover.jpg`\n"
        )
    else:
        cover_files = (
            "- Covers: not generated; add both configured cover panels and rebuild\n"
        )
    output = config.output_dir / "retailer_metadata.md"
    output.write_text(
        f"# Retailer metadata: {config.book.full_title}\n\n"
        "Use this sheet when creating or updating the retailer listing. "
        "The listing, interior, and cover must use matching details.\n\n"
        "| Field | Value |\n| --- | --- |\n"
        f"{rows}\n\n"
        "## Description\n\n"
        f"{description}\n\n"
        "## Upload files\n\n"
        f"- Print interior: `pdf/{config.slug}_kdp_interior.pdf`\n"
        f"- Ebook manuscript: `epub/{config.slug}.epub`\n"
        f"{cover_files}",
        encoding="utf-8",
    )
    return output


def _html_messages(messages: tuple[str, ...], empty: str) -> str:
    if not messages:
        return f"<p>{escape(empty)}</p>"
    return (
        "<ul>"
        + "".join(f"<li>{escape(message)}</li>" for message in messages)
        + "</ul>"
    )


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")
