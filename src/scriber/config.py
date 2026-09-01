"""Load a Scriber workspace and its book configurations."""

from __future__ import annotations

import glob
import re
import tomllib
from pathlib import Path
from typing import Any

from scriber.model import (
    BookConfig,
    BookMetadata,
    ContentsConfig,
    CoverConfig,
    LayoutConfig,
    PublishConfig,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def discover_books(workspace: Path, slugs: list[str] | None = None) -> list[BookConfig]:
    workspace = workspace.resolve()
    if slugs:
        sources = [workspace / "books" / slug / "book.toml" for slug in slugs]
    else:
        sources = sorted((workspace / "books").glob("*/book.toml"))
    if not sources:
        raise FileNotFoundError(f"No books found under {workspace / 'books'}")
    return [load_book_config(source, workspace) for source in sources]


def load_book_config(source: Path, workspace: Path | None = None) -> BookConfig:
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(f"Book configuration not found: {source}")
    root = source.parent
    workspace = (workspace or root.parent.parent).resolve()
    with source.open("rb") as handle:
        values = tomllib.load(handle)

    slug = root.name
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(f"Invalid book slug: {slug}")

    book_values = _table(values, "book")
    contents_values = _table(values, "contents")
    layout_values = _table(values, "layout")
    publish_values = _table(values, "publish")
    cover_values = values.get("cover", {})
    if not isinstance(cover_values, dict):
        raise TypeError("cover must be a TOML table")

    metadata = BookMetadata(
        title=_required_string(book_values, "title"),
        subtitle=str(book_values.get("subtitle", "")).strip(),
        author=_required_string(book_values, "author"),
        language=_required_string(book_values, "language"),
        copyright_year=int(book_values["copyright_year"]),
        edition_date=_required_string(book_values, "edition_date"),
    )
    contents = ContentsConfig(
        front=_string_tuple(contents_values, "front"),
        body=_string_tuple(contents_values, "body"),
        back=_string_tuple(contents_values, "back"),
    )
    inside_value = layout_values.get("inside_margin_inches", "auto")
    inside_margin = (
        None
        if inside_value == "auto"
        else _positive_float(inside_value, "inside_margin_inches")
    )
    layout = LayoutConfig(
        trim_width_inches=_positive_float(
            layout_values.get("trim_width_inches", 6.0), "trim_width_inches"
        ),
        trim_height_inches=_positive_float(
            layout_values.get("trim_height_inches", 9.0), "trim_height_inches"
        ),
        inside_margin_inches=inside_margin,
        outside_margin_inches=_positive_float(
            layout_values.get("outside_margin_inches", 0.5),
            "outside_margin_inches",
        ),
        top_margin_inches=_positive_float(
            layout_values.get("top_margin_inches", 0.7), "top_margin_inches"
        ),
        bottom_margin_inches=_positive_float(
            layout_values.get("bottom_margin_inches", 0.7),
            "bottom_margin_inches",
        ),
        gutter_safety_inches=float(layout_values.get("gutter_safety_inches", 0.125)),
        body_font_size=_positive_float(
            layout_values.get("body_font_size", 10.5), "body_font_size"
        ),
        body_leading=_positive_float(
            layout_values.get("body_leading", 14.5), "body_leading"
        ),
        chapter_font_size=_positive_float(
            layout_values.get("chapter_font_size", 20), "chapter_font_size"
        ),
    )
    publish = PublishConfig(
        profile=str(publish_values.get("profile", "kdp-paperback")),
        format=str(publish_values.get("format", "paperback")),
        ink=str(publish_values.get("ink", "black")),
        paper=str(publish_values.get("paper", "cream")),
        interior_bleed=bool(publish_values.get("interior_bleed", False)),
        max_pages=int(publish_values.get("max_pages", 828)),
        dpi=int(publish_values.get("dpi", 300)),
    )
    if publish.interior_bleed:
        raise ValueError(
            "Interior bleed is not supported in Scriber 0.1; use a no-bleed layout"
        )
    enabled = bool(cover_values.get("enabled", False))
    cover = CoverConfig(
        enabled=enabled,
        front=_optional_path(root, cover_values.get("front")),
        back=_optional_path(root, cover_values.get("back")),
        background=str(cover_values.get("background", "#20242a")),
        spine_title=bool(cover_values.get("spine_title", True)),
        spine_author=bool(cover_values.get("spine_author", True)),
        text_color=str(cover_values.get("text_color", "#ffffff")),
    )
    if cover.enabled and (cover.front is None or cover.back is None):
        raise ValueError("Enabled covers require both front and back image paths")

    return BookConfig(
        workspace=workspace,
        root=root,
        source=source,
        slug=slug,
        book=metadata,
        contents=contents,
        layout=layout,
        publish=publish,
        cover=cover,
    )


def expand_content_patterns(config: BookConfig) -> list[tuple[str, Path]]:
    expanded: list[tuple[str, Path]] = []
    for group, patterns in (
        ("front", config.contents.front),
        ("body", config.contents.body),
        ("back", config.contents.back),
    ):
        for pattern in patterns:
            matches = sorted(
                Path(value) for value in glob.glob(str(config.root / pattern))
            )
            if not matches:
                raise FileNotFoundError(
                    f"Content pattern {pattern!r} matched no files for {config.slug}"
                )
            for match in matches:
                resolved = match.resolve()
                if not resolved.is_relative_to(config.root.resolve()):
                    raise ValueError(
                        f"Content path escapes the book directory: {match}"
                    )
                expanded.append((group, resolved))
    paths = [path.resolve() for _, path in expanded]
    if len(paths) != len(set(paths)):
        raise ValueError(f"Content patterns include duplicate files for {config.slug}")
    return expanded


def _table(values: dict[str, Any], key: str) -> dict[str, Any]:
    value = values.get(key)
    if not isinstance(value, dict):
        raise TypeError(f"Missing or invalid [{key}] table")
    return value


def _required_string(values: dict[str, Any], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _string_tuple(values: dict[str, Any], key: str) -> tuple[str, ...]:
    value = values.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"contents.{key} must be an array of path patterns")
    return tuple(value)


def _positive_float(value: object, label: str) -> float:
    number = float(value)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _optional_path(root: Path, value: object) -> Path | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TypeError("Cover paths must be strings")
    path = Path(value)
    resolved = (path if path.is_absolute() else root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Cover path escapes the book directory: {value}")
    return resolved
