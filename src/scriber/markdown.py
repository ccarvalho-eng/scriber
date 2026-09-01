"""Parse the intentionally small Markdown subset used by Scriber."""

from __future__ import annotations

import re
from pathlib import Path

from scriber.config import expand_content_patterns
from scriber.model import Block, BookConfig, Section


def load_sections(config: BookConfig) -> list[Section]:
    sections: list[Section] = []
    for index, (group, path) in enumerate(expand_content_patterns(config), start=1):
        sections.append(parse_section(path, group, index))
    if not any(section.group == "body" for section in sections):
        raise ValueError(f"Book {config.slug} has no body sections")
    return sections


def parse_section(path: Path, group: str, index: int = 1) -> Section:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"Empty content file: {path}")
    title_index = next(
        (i for i, line in enumerate(lines) if line.startswith("# ")), None
    )
    if title_index is None:
        raise ValueError(f"Content file must begin with an H1 title: {path}")
    title = lines[title_index][2:].strip()
    if not title:
        raise ValueError(f"Content title cannot be empty: {path}")
    kind = _section_kind(path, group)
    identifier = f"section-{index:03d}-{_slugify(path.stem)}"
    return Section(
        identifier=identifier,
        group=group,
        kind=kind,
        title=title,
        source=path,
        blocks=tuple(_parse_blocks(lines[title_index + 1 :])),
    )


def _parse_blocks(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    paragraph: list[str] = []
    quote: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(Block("paragraph", " ".join(paragraph)))
            paragraph.clear()

    def flush_quote() -> None:
        if quote:
            blocks.append(Block("quote", " ".join(quote)))
            quote.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_quote()
            continue
        if line in {"* * *", "---"}:
            flush_paragraph()
            flush_quote()
            blocks.append(Block("scene", ""))
            continue
        if line.startswith("## "):
            flush_paragraph()
            flush_quote()
            blocks.append(Block("heading", line[3:].strip()))
            continue
        if line.startswith(">"):
            flush_paragraph()
            quote.append(line[1:].strip())
            continue
        if line.startswith("- "):
            flush_paragraph()
            flush_quote()
            blocks.append(Block("list_item", line[2:].strip()))
            continue
        flush_quote()
        paragraph.append(line)

    flush_paragraph()
    flush_quote()
    return blocks


def _section_kind(path: Path, group: str) -> str:
    stem = re.sub(r"^\d+[-_]", "", path.stem.lower())
    known = {
        "title": "titlepage",
        "title_page": "titlepage",
        "copyright": "copyright",
        "dedication": "dedication",
        "epigraph": "epigraph",
        "contents": "toc",
        "toc": "toc",
        "acknowledgements": "acknowledgements",
        "acknowledgments": "acknowledgements",
        "about_the_author": "about-author",
    }
    return known.get(stem, "chapter" if group == "body" else group)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"
