"""Shared domain types for Scriber builds."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class BookMetadata:
    title: str
    subtitle: str
    author: str
    language: str
    copyright_year: int
    edition_date: str

    @property
    def full_title(self) -> str:
        if self.subtitle:
            return f"{self.title}: {self.subtitle}"
        return self.title


@dataclass(frozen=True)
class ContentsConfig:
    front: tuple[str, ...]
    body: tuple[str, ...]
    back: tuple[str, ...]


@dataclass(frozen=True)
class LayoutConfig:
    trim_width_inches: float
    trim_height_inches: float
    inside_margin_inches: float | None
    outside_margin_inches: float
    top_margin_inches: float
    bottom_margin_inches: float
    gutter_safety_inches: float
    body_font_size: float
    body_leading: float
    chapter_font_size: float


@dataclass(frozen=True)
class PublishConfig:
    profile: str
    format: str
    ink: str
    paper: str
    interior_bleed: bool
    max_pages: int
    dpi: int


@dataclass(frozen=True)
class CoverConfig:
    enabled: bool
    front: Path | None
    back: Path | None
    background: str
    spine_title: bool
    spine_author: bool
    text_color: str


@dataclass(frozen=True)
class BookConfig:
    workspace: Path
    root: Path
    source: Path
    slug: str
    book: BookMetadata
    contents: ContentsConfig
    layout: LayoutConfig
    publish: PublishConfig
    cover: CoverConfig

    @property
    def output_dir(self) -> Path:
        return self.root / "dist"


@dataclass(frozen=True)
class Block:
    kind: str
    text: str


@dataclass(frozen=True)
class Section:
    identifier: str
    group: str
    kind: str
    title: str
    source: Path
    blocks: tuple[Block, ...] = field(default_factory=tuple)
