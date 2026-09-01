"""Load a Scriber workspace and its book configurations."""

from __future__ import annotations

import glob
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from scriber.model import (
    BookConfig,
    BookMetadata,
    ContentsConfig,
    CoverConfig,
    LayoutConfig,
    PublishConfig,
    TypographyConfig,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CURRENT_SCHEMA_VERSION = 2
DEFAULT_CONTENTS = {
    "front": ("manuscript/front_matter/*.md",),
    "body": ("manuscript/chapters/*.md",),
    "back": ("manuscript/back_matter/*.md",),
}


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
    output = root / "dist"
    if output.exists() and not output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Build output path escapes the book directory")
    with source.open("rb") as handle:
        values = tomllib.load(handle)

    slug = root.name
    if not SLUG_PATTERN.fullmatch(slug):
        raise ValueError(f"Invalid book slug: {slug}")

    book_values = _table(values, "book")
    schema_version = int(values.get("schema_version", 1))
    if schema_version not in {1, CURRENT_SCHEMA_VERSION}:
        raise ValueError(
            f"Unsupported schema_version {schema_version}; "
            f"Scriber supports 1 and {CURRENT_SCHEMA_VERSION}"
        )
    contents_values = values.get("contents", {})
    if not isinstance(contents_values, dict):
        raise TypeError("contents must be a TOML table")
    layout_values = _table(values, "layout")
    typography_values = values.get("typography", {})
    if not isinstance(typography_values, dict):
        raise TypeError("typography must be a TOML table")
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
        edition_date=_iso_date(book_values, "edition_date"),
        description=str(book_values.get("description", "")).strip(),
        publisher=str(book_values.get("publisher", "")).strip(),
        imprint=str(book_values.get("imprint", "")).strip(),
        series=str(book_values.get("series", "")).strip(),
        series_number=str(book_values.get("series_number", "")).strip(),
        isbn_print=str(book_values.get("isbn_print", "")).strip(),
        isbn_epub=str(book_values.get("isbn_epub", "")).strip(),
        subjects=_optional_string_tuple(book_values, "subjects"),
    )
    contents = ContentsConfig(
        front=_content_patterns(contents_values, "front"),
        body=_content_patterns(contents_values, "body"),
        back=_content_patterns(contents_values, "back"),
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
        paragraph_indent_inches=_nonnegative_float(
            layout_values.get("paragraph_indent_inches", 0.22),
            "paragraph_indent_inches",
        ),
        chapter_start_recto=_boolean(
            layout_values.get("chapter_start_recto", True),
            "layout.chapter_start_recto",
        ),
    )
    typography = TypographyConfig(
        regular=_optional_asset_path(root, typography_values.get("regular"), "font"),
        bold=_optional_asset_path(root, typography_values.get("bold"), "font"),
        italic=_optional_asset_path(root, typography_values.get("italic"), "font"),
        bold_italic=_optional_asset_path(
            root, typography_values.get("bold_italic"), "font"
        ),
        hyphenation=_boolean(
            typography_values.get("hyphenation", True),
            "typography.hyphenation",
        ),
    )
    supplied_fonts = (
        typography.regular,
        typography.bold,
        typography.italic,
        typography.bold_italic,
    )
    if any(supplied_fonts) and not all(supplied_fonts):
        raise ValueError(
            "Custom typography requires regular, bold, italic, and bold_italic fonts"
        )
    publish = PublishConfig(
        profile=str(publish_values.get("profile", "kdp-paperback")),
        format=str(publish_values.get("format", "paperback")),
        ink=str(publish_values.get("ink", "black")),
        paper=str(publish_values.get("paper", "cream")),
        interior_bleed=_boolean(
            publish_values.get("interior_bleed", False),
            "publish.interior_bleed",
        ),
        max_pages=_positive_int(publish_values.get("max_pages", 828), "max_pages"),
        dpi=_positive_int(publish_values.get("dpi", 300), "dpi"),
    )
    if publish.interior_bleed:
        raise ValueError(
            "Interior bleed is not supported in Scriber 0.1; use a no-bleed layout"
        )
    front = _optional_asset_path(
        root, cover_values.get("front", "assets/cover/front.png"), "cover"
    )
    back = _optional_asset_path(
        root, cover_values.get("back", "assets/cover/back.png"), "cover"
    )
    enabled_value = cover_values.get("enabled", "auto")
    if enabled_value == "auto":
        enabled = bool(front and back and front.exists() and back.exists())
    elif isinstance(enabled_value, bool):
        enabled = enabled_value
    else:
        raise ValueError('cover.enabled must be true, false, or "auto"')
    cover = CoverConfig(
        enabled=enabled,
        front=front,
        back=back,
        background=str(cover_values.get("background", "#20242a")),
        spine_title=_boolean(
            cover_values.get("spine_title", True),
            "cover.spine_title",
        ),
        spine_author=_boolean(
            cover_values.get("spine_author", True),
            "cover.spine_author",
        ),
        text_color=str(cover_values.get("text_color", "#ffffff")),
    )
    if cover.enabled and (cover.front is None or cover.back is None):
        raise ValueError("Enabled covers require both front and back image paths")

    return BookConfig(
        workspace=workspace,
        root=root,
        source=source,
        slug=slug,
        schema_version=schema_version,
        book=metadata,
        contents=contents,
        layout=layout,
        typography=typography,
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


def _iso_date(values: dict[str, Any], key: str) -> str:
    value = _required_string(values, key)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{key} must use YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{key} must be a valid calendar date") from error
    return value


def _content_patterns(values: dict[str, Any], key: str) -> tuple[str, ...]:
    if key not in values:
        return DEFAULT_CONTENTS[key]
    return _string_tuple(values, key)


def _string_tuple(values: dict[str, Any], key: str) -> tuple[str, ...]:
    value = values.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"contents.{key} must be an array of path patterns")
    return tuple(value)


def _optional_string_tuple(values: dict[str, Any], key: str) -> tuple[str, ...]:
    if key not in values:
        return ()
    return _string_tuple(values, key)


def _positive_float(value: object, label: str) -> float:
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"{label} must be numeric")
    number = float(value)
    if number <= 0:
        raise ValueError(f"{label} must be positive")
    return number


def _nonnegative_float(value: object, label: str) -> float:
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"{label} must be numeric")
    number = float(value)
    if number < 0:
        raise ValueError(f"{label} must not be negative")
    return number


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{label} must be true or false")
    return value


def _optional_asset_path(root: Path, value: object, label: str) -> Path | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TypeError(f"{label.capitalize()} paths must be strings")
    path = Path(value)
    resolved = (path if path.is_absolute() else root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(
            f"{label.capitalize()} path escapes the book directory: {value}"
        )
    return resolved
