"""Compile supplied cover panels after final pagination is known."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import reportlab
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from scriber.model import BookConfig
from scriber.profiles import CoverDimensions, get_profile


@dataclass(frozen=True)
class CoverBuild:
    print_pdf: Path
    preview: Path
    ebook_cover: Path
    dimensions: CoverDimensions
    source_warnings: tuple[str, ...]


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
    config.cover_dir.mkdir(parents=True, exist_ok=True)
    print_pdf = config.cover_dir / f"{config.slug}_paperback_cover.pdf"
    preview = config.cover_dir / f"{config.slug}_paperback_cover_preview.jpg"
    ebook_cover = config.cover_dir / f"{config.slug}_ebook_cover.jpg"
    _write_print_pdf(canvas, print_pdf, dimensions)
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
        source_warnings=cover_source_warnings(config, dimensions),
    )


def build_cover_template(config: BookConfig, page_count: int) -> Path:
    """Create a pixel-accurate cover guide after pagination is known."""

    dimensions = get_profile(config.publish.profile).cover_dimensions(
        page_count=page_count,
        trim_width_inches=config.layout.trim_width_inches,
        trim_height_inches=config.layout.trim_height_inches,
        ink=config.publish.ink,
        paper=config.publish.paper,
    )
    dpi = config.publish.dpi

    def scale(inches: float) -> int:
        return round(inches * dpi)

    width = scale(dimensions.width_inches)
    height = scale(dimensions.height_inches)
    bleed = scale(dimensions.bleed_inches)
    trim = scale(config.layout.trim_width_inches)
    spine = width - (2 * bleed) - (2 * trim)
    safe = scale(0.25)
    guide = Image.new("RGB", (width, height), "#f7f4ec")
    draw = ImageDraw.Draw(guide)
    fold_left = bleed + trim
    fold_right = fold_left + spine

    draw.rectangle(
        (bleed, bleed, width - bleed - 1, height - bleed - 1),
        outline="#d32f2f",
        width=4,
    )
    draw.line((fold_left, 0, fold_left, height), fill="#1565c0", width=4)
    draw.line((fold_right, 0, fold_right, height), fill="#1565c0", width=4)
    draw.rectangle(
        (
            bleed + safe,
            bleed + safe,
            fold_left - safe,
            height - bleed - safe,
        ),
        outline="#2e7d32",
        width=3,
    )
    draw.rectangle(
        (
            fold_right + safe,
            bleed + safe,
            width - bleed - safe,
            height - bleed - safe,
        ),
        outline="#2e7d32",
        width=3,
    )
    barcode_width = scale(2.0)
    barcode_height = scale(1.2)
    barcode_right = fold_left - safe
    barcode_bottom = height - bleed - safe
    draw.rectangle(
        (
            barcode_right - barcode_width,
            barcode_bottom - barcode_height,
            barcode_right,
            barcode_bottom,
        ),
        fill="#ffffff",
        outline="#6a1b9a",
        width=3,
    )
    font = ImageFont.load_default(size=max(12, round(dpi / 12)))
    draw.text((bleed + safe, bleed + safe), "BACK", fill="#222222", font=font)
    draw.text((fold_right + safe, bleed + safe), "FRONT", fill="#222222", font=font)
    draw.text(
        (barcode_right - barcode_width + 12, barcode_bottom - barcode_height + 12),
        "KEEP CLEAR FOR BARCODE",
        fill="#6a1b9a",
        font=font,
    )
    draw.text(
        (12, 12),
        "Red: trim  Blue: folds  Green: safe area",
        fill="#222222",
        font=font,
    )
    config.cover_dir.mkdir(parents=True, exist_ok=True)
    output = config.cover_dir / f"{config.slug}_cover_template.png"
    guide.save(output, "PNG", dpi=(dpi, dpi), optimize=True)
    return output


def cover_source_warnings(
    config: BookConfig,
    dimensions: CoverDimensions,
) -> tuple[str, ...]:
    """Report panel resolution and aspect-ratio risks before compilation."""

    if config.cover.front is None or config.cover.back is None:
        return ()
    dpi = config.publish.dpi
    expected = (
        round((config.layout.trim_width_inches + dimensions.bleed_inches) * dpi),
        round(dimensions.height_inches * dpi),
    )
    warnings: list[str] = []
    for label, path in (("front", config.cover.front), ("back", config.cover.back)):
        if not path.exists():
            continue
        with Image.open(path) as source:
            width, height = source.size
        effective_dpi = min(
            width / (config.layout.trim_width_inches + dimensions.bleed_inches),
            height / dimensions.height_inches,
        )
        if width < expected[0] or height < expected[1]:
            warnings.append(
                f"{label.capitalize()} cover is {width}x{height}px "
                f"({effective_dpi:.0f} effective DPI); {expected[0]}x{expected[1]}px "
                f"is required for {dpi} DPI output"
            )
        source_ratio = width / height
        target_ratio = expected[0] / expected[1]
        if abs(source_ratio - target_ratio) / target_ratio > 0.02:
            warnings.append(
                f"{label.capitalize()} cover aspect ratio requires cropping to fit"
            )
    return tuple(warnings)


def _write_print_pdf(
    image: Image.Image,
    output: Path,
    dimensions: CoverDimensions,
) -> None:
    encoded = BytesIO()
    image.save(encoded, "PNG", optimize=True)
    encoded.seek(0)
    width = dimensions.width_inches * 72
    height = dimensions.height_inches * 72
    document = Canvas(
        str(output),
        pagesize=(width, height),
        invariant=1,
        pageCompression=1,
    )
    document.drawImage(ImageReader(encoded), 0, 0, width=width, height=height)
    document.showPage()
    document.save()


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
