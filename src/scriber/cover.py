"""Compile supplied cover panels after final pagination is known."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import reportlab
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

from scriber.model import BookConfig
from scriber.profiles import CoverDimensions, get_profile


@dataclass(frozen=True)
class CoverBuild:
    print_pdf: Path
    preview: Path
    ebook_cover: Path
    dimensions: CoverDimensions


def build_cover(config: BookConfig, page_count: int) -> CoverBuild | None:
    if not config.cover.enabled:
        return None
    if config.cover.front is None or config.cover.back is None:
        raise ValueError("Enabled cover requires front and back image paths")
    for path in (config.cover.front, config.cover.back):
        if not path.exists():
            raise FileNotFoundError(f"Cover image not found: {path}")

    profile = get_profile(config.publish.profile)
    dimensions = profile.cover_dimensions(
        page_count=page_count,
        trim_width_inches=config.layout.trim_width_inches,
        trim_height_inches=config.layout.trim_height_inches,
        ink=config.publish.ink,
        paper=config.publish.paper,
    )
    dpi = config.publish.dpi
    width_px = round(dimensions.width_inches * dpi)
    height_px = round(dimensions.height_inches * dpi)
    bleed_px = round(dimensions.bleed_inches * dpi)
    trim_width_px = round(config.layout.trim_width_inches * dpi)
    spine_px = width_px - (2 * bleed_px) - (2 * trim_width_px)
    background = ImageColor.getrgb(config.cover.background)
    canvas = Image.new("RGB", (width_px, height_px), background)

    with Image.open(config.cover.back) as source:
        back = ImageOps.fit(
            source.convert("RGB"),
            (bleed_px + trim_width_px, height_px),
            method=Image.Resampling.LANCZOS,
        )
        canvas.paste(back, (0, 0))
    front_x = bleed_px + trim_width_px + spine_px
    with Image.open(config.cover.front) as source:
        front = ImageOps.fit(
            source.convert("RGB"),
            (trim_width_px + bleed_px, height_px),
            method=Image.Resampling.LANCZOS,
        )
        canvas.paste(front, (front_x, 0))

    _draw_spine(canvas, config, page_count, spine_px, bleed_px + trim_width_px)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    print_pdf = config.output_dir / "paperback-cover.pdf"
    preview = config.output_dir / "paperback-cover-preview.jpg"
    ebook_cover = config.output_dir / "ebook-cover.jpg"
    canvas.save(print_pdf, "PDF", resolution=dpi)
    preview_image = canvas.copy()
    preview_image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
    preview_image.save(preview, "JPEG", quality=92, subsampling=0)

    with Image.open(config.cover.front) as source:
        ebook = ImageOps.fit(
            source.convert("RGB"),
            (1600, 2560),
            method=Image.Resampling.LANCZOS,
        )
        ebook.save(ebook_cover, "JPEG", quality=95, subsampling=0)

    return CoverBuild(
        print_pdf=print_pdf,
        preview=preview,
        ebook_cover=ebook_cover,
        dimensions=dimensions,
    )


def _draw_spine(
    canvas: Image.Image,
    config: BookConfig,
    page_count: int,
    spine_width: int,
    spine_x: int,
) -> None:
    profile = get_profile(config.publish.profile)
    if not profile.spine_text_allowed(page_count):
        return
    labels = []
    if config.cover.spine_title:
        labels.append(config.book.title)
    if config.cover.spine_author:
        labels.append(config.book.author)
    text = "  •  ".join(labels)
    if not text or spine_width < 38:
        return

    font_path = Path(reportlab.__file__).resolve().parent / "fonts" / "VeraBd.ttf"
    font_size = max(18, min(42, spine_width - 24))
    font = ImageFont.truetype(str(font_path), font_size)
    layer = Image.new("RGBA", (canvas.height, spine_width), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.text(
        (layer.width / 2, layer.height / 2),
        text,
        font=font,
        fill=ImageColor.getrgb(config.cover.text_color),
        anchor="mm",
    )
    rotated = layer.rotate(90, expand=True)
    canvas.paste(rotated, (spine_x, 0), rotated)
