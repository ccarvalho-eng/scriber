"""Build a deterministic, reflowable EPUB 3 package."""

from __future__ import annotations

import hashlib
import html
import re
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
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
    config.output_dir.mkdir(parents=True, exist_ok=True)
    output = config.output_dir / "book.epub"
    identifier = _identifier(config, sections)
    with tempfile.TemporaryDirectory(
        prefix="scriber-epub-", dir=config.output_dir
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
        _write_archive(root, output)

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
    for block in section.blocks:
        value = _inline(block.text)
        if block.kind == "heading":
            blocks.append(f"<h2>{value}</h2>")
        elif block.kind == "quote":
            blocks.append(f"<blockquote><p>{value}</p></blockquote>")
        elif block.kind == "scene":
            blocks.append('<p class="scene">• &nbsp; • &nbsp; •</p>')
        elif block.kind == "list_item":
            blocks.append(f'<p class="list-item">• {value}</p>')
        else:
            blocks.append(f"<p>{value}</p>")
    epub_type = {
        "titlepage": "titlepage",
        "copyright": "copyright-page",
        "dedication": "dedication",
        "toc": "toc",
        "chapter": "chapter",
        "acknowledgements": "acknowledgments",
        "about-author": "contributors",
    }.get(section.kind, "frontmatter" if section.group == "front" else "backmatter")
    body = "\n      ".join(blocks)
    return _xhtml_document(
        config,
        section.title,
        f'    <section epub:type="{epub_type}">\n      {body}\n    </section>',
    )


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
    return f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0"
         unique-identifier="book-id" xml:lang="{html.escape(config.book.language)}">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">urn:uuid:{identifier}</dc:identifier>
    <dc:title>{html.escape(config.book.full_title)}</dc:title>
    <dc:creator>{html.escape(config.book.author)}</dc:creator>
    <dc:language>{html.escape(config.book.language)}</dc:language>
    <dc:rights>Copyright © {config.book.copyright_year} {html.escape(config.book.author)}</dc:rights>
    <meta property="dcterms:modified">{modified}</meta>
    <meta property="schema:accessMode">textual</meta>
    <meta property="schema:accessibilityFeature">readingOrder</meta>
    <meta property="schema:accessibilityFeature">tableOfContents</meta>
    <meta property="schema:accessibilityHazard">none</meta>
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
h1 + p, h2 + p, blockquote p, .scene, .list-item { text-indent: 0; }
blockquote { margin: 1em 8%; font-style: italic; }
.scene { margin: 1em 0; text-align: center; }
.book-title { font-size: 2em; margin-top: 35%; }
.cover img { display: block; height: auto; width: 100%; }
"""


def _inline(value: str) -> str:
    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def _write_archive(root: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "w") as archive:
        archive.write(root / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == "mimetype":
                continue
            archive.write(
                path,
                path.relative_to(root).as_posix(),
                compress_type=zipfile.ZIP_DEFLATED,
            )
