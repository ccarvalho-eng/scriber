"""Resolve bundled and book-specific typography assets."""

from __future__ import annotations

from pathlib import Path

from scriber.model import BookConfig


def font_paths(config: BookConfig) -> dict[str, Path]:
    bundled = Path(__file__).with_name("fonts")
    if config.typography.regular is not None:
        body = {
            "regular": config.typography.regular,
            "bold": config.typography.bold,
            "italic": config.typography.italic,
            "bold_italic": config.typography.bold_italic,
        }
    else:
        body = {
            "regular": bundled / "Gelasio-Regular.ttf",
            "bold": bundled / "Gelasio-Bold.ttf",
            "italic": bundled / "Gelasio-Italic.ttf",
            "bold_italic": bundled / "Gelasio-BoldItalic.ttf",
        }
    return {
        style: path
        for style, path in {
            **body,
            "display": bundled / "Cinzel-Variable.ttf",
        }.items()
        if path is not None
    }
