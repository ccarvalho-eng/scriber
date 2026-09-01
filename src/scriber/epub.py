"""Build a deterministic, reflowable EPUB 3 package."""

from __future__ import annotations

import hashlib
import html
import re
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from scriber.model import BookConfig, Section


@dataclass(frozen=True)
class EpubBuild:
    path: Path
    identifier: str
    sections: int


def build_epub(
    config: BookConfig,
    sections: list[Section],
    ebook_cover: Path | None = None,
) -> EpubBuild:
    config.epub_dir.mkdir(parents=True, exist_ok=True)
    output = config.epub_dir / f"{config.slug}.epub"
    identifier = _identifier(config, sections)
    with tempfile.TemporaryDirectory(
        prefix="scriber-epub-", dir=config.epub_dir
    ) as raw:
        root = Path(raw)
        epub = root / "EPUB"
        text_dir = epub / "text"
        styles_dir = epub / "styles"
        images_dir = epub / "images"
        meta_inf = root / "META-INF"
        for directory in (text_dir, styles_dir, images_dir, meta_inf):
            directory.mkdir(parents=True, exist_ok=True)

        (root / "mimetype").write_text("application/epub+zip", encoding="ascii")
        (meta_inf / "container.xml").write_text(_container_xml(), encoding="utf-8")
        (styles_dir / "book.css").write_text(_stylesheet(), encoding="utf-8")

        filenames: list[tuple[Section, str]] = []
        for index, section in enumerate(sections, start=1):
            filename = f"section-{index:03d}.xhtml"
            filenames.append((section, filename))
            (text_dir / filename).write_text(
                _section_xhtml(config, section),
                encoding="utf-8",
            )

        cover_present = ebook_cover is not None and ebook_cover.exists()
        if cover_present and ebook_cover is not None:
            (images_dir / "cover.jpg").write_bytes(ebook_cover.read_bytes())
            (text_dir / "cover.xhtml").write_text(
                _cover_xhtml(config),
                encoding="utf-8",
            )
        (epub / "nav.xhtml").write_text(
            _nav_xhtml(config, filenames),
            encoding="utf-8",
        )
        (epub / "package.opf").write_text(
            _package_opf(config, identifier, filenames, cover_present),
            encoding="utf-8",
        )
        _write_archive(root, output, config.book.edition_date)

    return EpubBuild(
        path=output,
        identifier=f"urn:uuid:{identifier}",
        sections=len(sections),
    )


def _identifier(config: BookConfig, sections: list[Section]) -> uuid.UUID:
    digest = hashlib.sha256()
    digest.update(config.book.full_title.encode("utf-8"))
    digest.update(config.book.author.encode("utf-8"))
    for section in sections:
        digest.update(section.source.read_bytes())
    return uuid.uuid5(uuid.NAMESPACE_URL, digest.hexdigest())


def _section_xhtml(config: BookConfig, section: Section) -> str:
    blocks: list[str] = []
    if section.kind != "titlepage":
        blocks.append(f"<h1>{html.escape(section.title)}</h1>")
    else:
        blocks.append(f'<h1 class="book-title">{html.escape(section.title)}</h1>')
    active_list: str | None = None
    for block in section.blocks:
        list_tag = {
            "list_item": "ul",
            "ordered_item": "ol",
        }.get(block.kind)
        if list_tag:
            if active_list != list_tag:
                if active_list:
                    blocks.append(f"</{active_list}>")
                blocks.append(f"<{list_tag}>")
                active_list = list_tag
            blocks.append(f"<li>{_inline(block.text)}</li>")
            continue
        if active_list:
            blocks.append(f"</{active_list}>")
            active_list = None
        blocks.append(_block_xhtml(block.kind, block.text))
    if active_list:
        blocks.append(f"</{active_list}>")
    epub_type = {
        "titlepage": "titlepage",
        "copyright": "copyright-page",
        "dedication": "dedication",
        "epigraph": "epigraph",
        "foreword": "foreword",
        "preface": "preface",
        "prologue": "prologue",
        "interlude": "chapter",
        "epilogue": "epilogue",
        "afterword": "afterword",
        "toc": "toc",
        "chapter": "chapter",
        "acknowledgements": "acknowledgments",
        "about-author": "contributors",
        "author-note": "afterword",
        "note-to-reader": "notice",
        "endnotes": "endnotes",
        "glossary": "glossary",
        "bibliography": "bibliography",
        "also-by": "other-credits",
    }.get(section.kind, "frontmatter" if section.group == "front" else "backmatter")
    body = "\n      ".join(blocks)
    return _xhtml_document(
        config,
        section.title,
        f'    <section epub:type="{epub_type}">\n      {body}\n    </section>',
    )


def _block_xhtml(kind: str, text: str) -> str:
    value = _inline(text)
    if kind == "heading":
        return f"<h2>{value}</h2>"
    if kind == "quote":
        return f"<blockquote><p>{value}</p></blockquote>"
    if kind == "scene":
        return '<p class="scene">• &#160; • &#160; •</p>'
    if kind in {"note", "letter", "document"}:
        value = value.replace("\n", "<br/>")
        return f'<div class="character-document {kind}"><p>{value}</p></div>'
    return f"<p>{value}</p>"


def _cover_xhtml(config: BookConfig) -> str:
    return _xhtml_document(
        config,
        "Cover",
        (
            '    <section epub:type="cover" class="cover">'
            f'<img src="../images/cover.jpg" alt="Cover of {html.escape(config.book.full_title)}"/>'
            "</section>"
        ),
    )


def _nav_xhtml(
    config: BookConfig,
    filenames: list[tuple[Section, str]],
) -> str:
    links = "\n".join(
        f'        <li><a href="text/{filename}">{html.escape(section.title)}</a></li>'
        for section, filename in filenames
        if section.kind != "titlepage"
    )
    body_start = next(
        filename for section, filename in filenames if section.group == "body"
    )
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      xml:lang="{html.escape(config.book.language)}">
  <head><title>Contents</title></head>
  <body>
    <nav epub:type="toc" id="toc"><h1>Contents</h1><ol>
{links}
    </ol></nav>
    <nav epub:type="landmarks" hidden="hidden"><ol>
      <li><a epub:type="bodymatter" href="text/{body_start}">Begin Reading</a></li>
    </ol></nav>
  </body>
</html>
'''


def _package_opf(
    config: BookConfig,
    identifier: uuid.UUID,
    filenames: list[tuple[Section, str]],
    cover_present: bool,
) -> str:
    manifests = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '<item id="css" href="styles/book.css" media-type="text/css"/>',
    ]
    spine = []
    if cover_present:
        manifests.extend(
            [
                '<item id="cover-image" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
                '<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/>',
            ]
        )
        spine.append('<itemref idref="cover"/>')
    for index, (_section, filename) in enumerate(filenames, start=1):
        manifests.append(
            f'<item id="section-{index:03d}" href="text/{filename}" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="section-{index:03d}"/>')
    modified = f"{config.book.edition_date}T00:00:00Z"
    optional_metadata: list[str] = []
    if config.book.description:
        optional_metadata.append(
            f"    <dc:description>{html.escape(config.book.description)}</dc:description>"
        )
    publisher = config.book.imprint or config.book.publisher
    if publisher:
        optional_metadata.append(
            f"    <dc:publisher>{html.escape(publisher)}</dc:publisher>"
        )
    if config.book.isbn_epub:
        optional_metadata.append(
            f"    <dc:identifier>urn:isbn:{html.escape(config.book.isbn_epub)}</dc:identifier>"
        )
    optional_metadata.extend(
        f"    <dc:subject>{html.escape(subject)}</dc:subject>"
        for subject in config.book.subjects
    )
    if config.book.series:
        optional_metadata.extend(
            [
                (
                    '    <meta property="belongs-to-collection" id="series">'
                    f"{html.escape(config.book.series)}</meta>"
                ),
                '    <meta refines="#series" property="collection-type">series</meta>',
            ]
        )
        if config.book.series_number:
            optional_metadata.append(
                '    <meta refines="#series" property="group-position">'
                f"{html.escape(config.book.series_number)}</meta>"
            )
    optional = "\n".join(optional_metadata)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0"
         unique-identifier="book-id" xml:lang="{html.escape(config.book.language)}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:uuid:{identifier}</dc:identifier>
    <dc:title>{html.escape(config.book.full_title)}</dc:title>
    <dc:creator>{html.escape(config.book.author)}</dc:creator>
    <dc:language>{html.escape(config.book.language)}</dc:language>
    <dc:rights>Copyright © {config.book.copyright_year} {html.escape(config.book.author)}</dc:rights>
{optional}
    <meta property="dcterms:modified">{modified}</meta>
    <meta property="schema:accessMode">textual</meta>
    <meta property="schema:accessibilityFeature">readingOrder</meta>
    <meta property="schema:accessibilityFeature">tableOfContents</meta>
    <meta property="schema:accessibilityHazard">none</meta>
    <meta property="schema:accessibilitySummary">This publication is text-led, includes a structured table of contents, and has no known hazards.</meta>
  </metadata>
  <manifest>
    {chr(10).join(manifests)}
  </manifest>
  <spine>
    {chr(10).join(spine)}
  </spine>
</package>
'''


def _xhtml_document(config: BookConfig, title: str, body: str) -> str:
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops"
      xml:lang="{html.escape(config.book.language)}">
  <head>
    <title>{html.escape(title)}</title>
    <link rel="stylesheet" type="text/css" href="../styles/book.css"/>
  </head>
  <body>
{body}
  </body>
</html>
'''


def _container_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _stylesheet() -> str:
    return """body { font-family: serif; line-height: 1.45; margin: 5%; }
h1 { text-align: center; margin: 20% 0 2em; }
h2 { margin-top: 1.5em; }
p { margin: 0; text-indent: 1.2em; }
h1 + p, h2 + p, blockquote p, .scene, li { text-indent: 0; }
blockquote { margin: 1em 8%; font-style: italic; }
.character-document { border: 1px solid #999; font-style: italic; margin: 1em 8%; padding: 0.8em; }
.character-document p { text-indent: 0; }
ul, ol { margin: 1em 0 1em 2em; padding: 0; }
li { margin: 0.25em 0; }
.scene { margin: 1em 0; text-align: center; }
.book-title { font-size: 2em; margin-top: 35%; }
.cover img { display: block; height: auto; width: 100%; }
"""


def _inline(value: str) -> str:
    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def _write_archive(root: Path, output: Path, edition_date: str) -> None:
    parsed = date.fromisoformat(edition_date)
    timestamp = (max(parsed.year, 1980), parsed.month, parsed.day, 0, 0, 0)
    with zipfile.ZipFile(output, "w", compresslevel=9) as archive:
        _write_entry(
            archive,
            "mimetype",
            (root / "mimetype").read_bytes(),
            timestamp,
            zipfile.ZIP_STORED,
        )
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == "mimetype":
                continue
            _write_entry(
                archive,
                path.relative_to(root).as_posix(),
                path.read_bytes(),
                timestamp,
                zipfile.ZIP_DEFLATED,
            )


def _write_entry(
    archive: zipfile.ZipFile,
    name: str,
    content: bytes,
    timestamp: tuple[int, int, int, int, int, int],
    compression: int,
) -> None:
    entry = zipfile.ZipInfo(name, date_time=timestamp)
    entry.compress_type = compression
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    archive.writestr(entry, content)
