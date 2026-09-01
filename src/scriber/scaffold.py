"""Create Scriber workspaces and fill-in-ready book skeletons."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def initialize_workspace(workspace: Path) -> list[Path]:
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    marker = workspace / "scriber.toml"
    if not marker.exists():
        marker.write_text(
            '[workspace]\nname = "My Library"\n',
            encoding="utf-8",
        )
        created.append(marker)
    books = workspace / "books"
    books.mkdir(parents=True, exist_ok=True)
    return created


def create_book(
    workspace: Path,
    slug: str,
    title: str,
    author: str,
    subtitle: str = "",
    language: str = "en-US",
) -> list[Path]:
    workspace = workspace.resolve()
    initialize_workspace(workspace)
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError("slug must use lowercase letters, numbers, and single hyphens")
    if not title.strip() or not author.strip():
        raise ValueError("title and author are required")
    root = workspace / "books" / slug
    if root.exists():
        raise FileExistsError(f"Book already exists: {root}")

    for directory in (
        root / "front",
        root / "manuscript",
        root / "back",
        root / "assets" / "cover",
    ):
        directory.mkdir(parents=True, exist_ok=False)

    values = {
        root / "book.toml": _book_config(
            title=title.strip(),
            subtitle=subtitle.strip(),
            author=author.strip(),
            language=language.strip(),
        ),
        root / "front" / "00_title.md": _title_page(title, subtitle, author),
        root / "front" / "01_copyright.md": _copyright_page(title, author),
        root / "front" / "02_dedication.md": "# Dedication\n\nFor...\n",
        root / "front" / "03_contents.md": "# Contents\n",
        root / "manuscript" / "01_chapter.md": (
            "# Chapter One\n\nBegin the manuscript here.\n"
        ),
        root / "back" / "01_acknowledgements.md": (
            "# Acknowledgements\n\nAdd acknowledgements here.\n"
        ),
        root / "back" / "02_about_the_author.md": (
            f"# About the Author\n\n{author.strip()} is...\n"
        ),
    }
    for path, content in values.items():
        path.write_text(content, encoding="utf-8")
    return list(values)


def _book_config(
    title: str,
    subtitle: str,
    author: str,
    language: str,
) -> str:
    today = datetime.now(UTC).date()
    year = today.year
    edition_date = today.isoformat()
    return f'''[book]
title = {_toml_string(title)}
subtitle = {_toml_string(subtitle)}
author = {_toml_string(author)}
language = {_toml_string(language)}
copyright_year = {year}
edition_date = "{edition_date}"

[contents]
front = ["front/*.md"]
body = ["manuscript/*.md"]
back = ["back/*.md"]

[layout]
trim_width_inches = 6.0
trim_height_inches = 9.0
inside_margin_inches = "auto"
outside_margin_inches = 0.5
top_margin_inches = 0.7
bottom_margin_inches = 0.7
gutter_safety_inches = 0.125
body_font_size = 10.5
body_leading = 14.5
chapter_font_size = 20

[publish]
profile = "kdp-paperback"
format = "paperback"
ink = "black"
paper = "cream"
interior_bleed = false
max_pages = 828
dpi = 300

[cover]
enabled = false
front = "assets/cover/front.png"
back = "assets/cover/back.png"
background = "#20242a"
spine_title = true
spine_author = true
text_color = "#ffffff"
'''


def _title_page(title: str, subtitle: str, author: str) -> str:
    lines = [f"# {title.strip()}"]
    if subtitle.strip():
        lines.extend(["", f"## {subtitle.strip()}"])
    lines.extend(["", author.strip(), ""])
    return "\n".join(lines)


def _copyright_page(title: str, author: str) -> str:
    year = datetime.now(UTC).year
    return (
        f"# Copyright\n\n{title.strip()}\n\n"
        f"Copyright © {year} {author.strip()}\n\nAll rights reserved.\n"
    )


def _toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
