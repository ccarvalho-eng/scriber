"""Iterative print-interior PDF renderer."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import reportlab
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    ActionFlowable,
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from scriber.model import BookConfig, Section
from scriber.profiles import get_profile


@dataclass(frozen=True)
class PdfBuild:
    path: Path
    page_count: int
    inside_margin_inches: float
    section_pages: dict[str, int]
    passes: int


class SectionMarker(Flowable):
    def __init__(
        self,
        section: Section,
        page_map: dict[str, int],
    ) -> None:
        super().__init__()
        self.section = section
        self.page_map = page_map
        self.width = 0
        self.height = 0

    def draw(self) -> None:
        canvas = cast(Any, self.canv)
        page = canvas.getPageNumber()
        self.page_map[self.section.identifier] = page
        canvas._scriber_section_title = self.section.title
        canvas._scriber_section_kind = self.section.kind
        canvas._scriber_section_group = self.section.group
        if self.section.group == "body" and not hasattr(canvas, "_scriber_body_start"):
            canvas._scriber_body_start = page


class RectoPad(ActionFlowable):
    """Advance past a left-hand page so the next section starts on recto."""

    def __init__(self) -> None:
        super().__init__(())

    def apply(self, doc) -> None:
        if doc.page % 2 == 0:
            doc.handle_pageBreak()


class InvariantCanvas(Canvas):
    """ReportLab canvas with stable IDs and timestamps."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs["invariant"] = 1
        kwargs["pageCompression"] = 1
        super().__init__(*args, **kwargs)


def build_print_pdf(config: BookConfig, sections: list[Section]) -> PdfBuild:
    profile = get_profile(config.publish.profile)
    config.pdf_dir.mkdir(parents=True, exist_ok=True)
    output = config.pdf_dir / f"{config.slug}_kdp_interior.pdf"
    previous_map: dict[str, int] = {}
    inside = max(
        config.layout.inside_margin_inches or 0,
        profile.minimum_inside_margin(profile.minimum_pages)
        + config.layout.gutter_safety_inches,
    )

    for pass_number in range(1, 9):
        temporary = config.pdf_dir / f".interior-pass-{pass_number}.pdf"
        page_map = _render_pass(
            config=config,
            sections=sections,
            output=temporary,
            inside_margin_inches=inside,
            toc_pages=previous_map,
        )
        raw_count = len(PdfReader(str(temporary)).pages)
        page_count = raw_count if raw_count % 2 == 0 else raw_count + 1
        required_inside = (
            profile.minimum_inside_margin(page_count)
            + config.layout.gutter_safety_inches
        )
        next_inside = max(config.layout.inside_margin_inches or 0, required_inside)
        stable = page_map == previous_map and abs(next_inside - inside) < 0.0001
        if stable:
            temporary.replace(output)
            final_count = _ensure_even_page_count(output)
            _strip_unused_default_font(output)
            return PdfBuild(
                path=output,
                page_count=final_count,
                inside_margin_inches=inside,
                section_pages=page_map,
                passes=pass_number,
            )
        previous_map = page_map
        inside = next_inside
        temporary.unlink(missing_ok=True)

    raise RuntimeError(f"Pagination did not stabilize for {config.slug}")


def _render_pass(
    config: BookConfig,
    sections: list[Section],
    output: Path,
    inside_margin_inches: float,
    toc_pages: dict[str, int],
) -> dict[str, int]:
    fonts = _register_fonts(config)
    styles = _styles(config, fonts)
    page_map: dict[str, int] = {}
    trim_width = config.layout.trim_width_inches * inch
    trim_height = config.layout.trim_height_inches * inch
    content_width = (
        trim_width - (inside_margin_inches + config.layout.outside_margin_inches) * inch
    )
    if content_width <= inch:
        raise ValueError("Resolved print margins leave less than one inch for text")
    story: list[Flowable] = []
    for index, section in enumerate(sections):
        if index:
            story.append(PageBreak())
            if config.layout.chapter_start_recto and section.group == "body":
                story.append(RectoPad())
        story.extend(
            _section_story(
                section,
                page_map,
                toc_pages,
                sections,
                styles,
                content_width,
            )
        )

    odd_frame = Frame(
        inside_margin_inches * inch,
        config.layout.bottom_margin_inches * inch,
        trim_width
        - (inside_margin_inches + config.layout.outside_margin_inches) * inch,
        trim_height
        - (config.layout.top_margin_inches + config.layout.bottom_margin_inches) * inch,
        id="odd",
        showBoundary=0,
    )
    even_frame = Frame(
        config.layout.outside_margin_inches * inch,
        config.layout.bottom_margin_inches * inch,
        trim_width
        - (inside_margin_inches + config.layout.outside_margin_inches) * inch,
        trim_height
        - (config.layout.top_margin_inches + config.layout.bottom_margin_inches) * inch,
        id="even",
        showBoundary=0,
    )

    def on_page(canvas, document) -> None:
        frame = odd_frame if canvas.getPageNumber() % 2 else even_frame
        document.pageTemplate.frames = [frame]

    def on_page_end(canvas, _document) -> None:
        _draw_page_furniture(canvas, config, inside_margin_inches, fonts["regular"])

    document = BaseDocTemplate(
        str(output),
        pagesize=(trim_width, trim_height),
        title=config.book.full_title,
        author=config.book.author,
        creator="Scriber",
    )
    document.addPageTemplates(
        [
            PageTemplate(
                id="mirrored",
                frames=[odd_frame],
                onPage=on_page,
                onPageEnd=on_page_end,
            )
        ]
    )
    document.build(story, canvasmaker=InvariantCanvas)
    return page_map


def _section_story(
    section: Section,
    page_map: dict[str, int],
    toc_pages: dict[str, int],
    all_sections: list[Section],
    styles: dict[str, ParagraphStyle],
    content_width: float,
) -> list[Flowable]:
    story: list[Flowable] = [SectionMarker(section, page_map)]
    if section.kind == "titlepage":
        story.extend(
            [
                Spacer(1, 2.1 * inch),
                Paragraph(_inline(section.title.upper()), styles["title"]),
            ]
        )
    elif section.kind == "copyright":
        story.append(Spacer(1, 4.5 * inch))
        story.append(Paragraph(_inline(section.title), styles["front_heading"]))
    else:
        story.extend(
            [
                Spacer(1, 0.55 * inch if section.group == "body" else 0.2 * inch),
                Paragraph(_inline(section.title), styles["chapter"]),
            ]
        )

    if section.kind == "toc":
        story.append(_toc_table(all_sections, toc_pages, styles, content_width))
        return story

    first_paragraph = True
    ordered_index = 0
    for block in section.blocks:
        if block.kind == "scene":
            story.append(Paragraph("• &nbsp; • &nbsp; •", styles["scene"]))
            first_paragraph = True
            ordered_index = 0
        elif block.kind == "heading":
            story.append(Paragraph(_inline(block.text), styles["subheading"]))
            first_paragraph = True
            ordered_index = 0
        elif block.kind == "quote":
            story.append(Paragraph(_inline(block.text), styles["quote"]))
            first_paragraph = True
            ordered_index = 0
        elif block.kind in {"note", "letter", "document"}:
            story.append(
                Paragraph(
                    _inline(block.text).replace("\n", "<br/>"),
                    styles["document"],
                )
            )
            first_paragraph = True
            ordered_index = 0
        elif block.kind == "list_item":
            story.append(Paragraph(f"• &nbsp; {_inline(block.text)}", styles["list"]))
            ordered_index = 0
        elif block.kind == "ordered_item":
            ordered_index += 1
            story.append(
                Paragraph(
                    f"{ordered_index}. &nbsp; {_inline(block.text)}",
                    styles["list"],
                )
            )
        else:
            ordered_index = 0
            style = styles["body_first"] if first_paragraph else styles["body"]
            story.append(Paragraph(_inline(block.text), style))
            first_paragraph = False
    return story


def _toc_table(
    sections: list[Section],
    toc_pages: dict[str, int],
    styles: dict[str, ParagraphStyle],
    content_width: float,
) -> Table:
    rows: list[list[Paragraph]] = []
    body_identifier = next(
        (section.identifier for section in sections if section.group == "body"),
        None,
    )
    body_start = toc_pages.get(body_identifier) if body_identifier else None
    for section in sections:
        if section.group == "front" or section.kind == "toc":
            continue
        page = toc_pages.get(section.identifier)
        printed_page = (
            page - body_start + 1
            if page is not None and body_start is not None
            else None
        )
        rows.append(
            [
                Paragraph(_inline(section.title), styles["toc"]),
                Paragraph(
                    str(printed_page) if printed_page is not None else "",
                    styles["toc_page"],
                ),
            ]
        )
    page_column = min(0.35 * inch, content_width * 0.15)
    table = Table(rows, colWidths=[content_width - page_column, page_column])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _draw_page_furniture(
    canvas,
    config: BookConfig,
    inside_margin: float,
    regular_font: str,
) -> None:
    body_start = getattr(canvas, "_scriber_body_start", None)
    kind = getattr(canvas, "_scriber_section_kind", "")
    if body_start is None or kind in {"titlepage", "copyright"}:
        return
    physical_page = canvas.getPageNumber()
    printed_page = physical_page - body_start + 1
    width = config.layout.trim_width_inches * inch
    outside = config.layout.outside_margin_inches * inch
    inside = inside_margin * inch
    x = width - outside if physical_page % 2 else inside
    canvas.saveState()
    canvas.setFont(regular_font, 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawCentredString(x, 0.38 * inch, str(printed_page))
    title = getattr(canvas, "_scriber_section_title", "")
    group = getattr(canvas, "_scriber_section_group", "")
    if title and group == "body":
        canvas.setFont(regular_font, 7.5)
        canvas.drawCentredString(
            width / 2, config.layout.trim_height_inches * inch - 0.4 * inch, title
        )
    canvas.restoreState()


def _styles(
    config: BookConfig,
    fonts: dict[str, str],
) -> dict[str, ParagraphStyle]:
    body_size = config.layout.body_font_size
    leading = config.layout.body_leading
    hyphenation = (
        config.book.language.split("-", maxsplit=1)[0]
        if config.typography.hyphenation
        else ""
    )
    return {
        "title": ParagraphStyle(
            "Title",
            fontName=fonts["bold"],
            fontSize=26,
            leading=32,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "front_heading": ParagraphStyle(
            "FrontHeading",
            fontName=fonts["bold"],
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "chapter": ParagraphStyle(
            "Chapter",
            fontName=fonts["bold"],
            fontSize=config.layout.chapter_font_size,
            leading=config.layout.chapter_font_size * 1.2,
            alignment=TA_CENTER,
            spaceAfter=24,
        ),
        "subheading": ParagraphStyle(
            "Subheading",
            fontName=fonts["bold"],
            fontSize=body_size + 1,
            leading=leading,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=fonts["regular"],
            fontSize=body_size,
            leading=leading,
            alignment=TA_JUSTIFY,
            firstLineIndent=config.layout.paragraph_indent_inches * inch,
            spaceAfter=0,
            allowWidows=0,
            allowOrphans=0,
            hyphenationLang=hyphenation,
        ),
        "body_first": ParagraphStyle(
            "BodyFirst",
            fontName=fonts["regular"],
            fontSize=body_size,
            leading=leading,
            alignment=TA_JUSTIFY,
            firstLineIndent=0,
            spaceAfter=0,
            allowWidows=0,
            allowOrphans=0,
            hyphenationLang=hyphenation,
        ),
        "quote": ParagraphStyle(
            "Quote",
            fontName=fonts["italic"],
            fontSize=body_size - 0.5,
            leading=leading,
            leftIndent=0.28 * inch,
            rightIndent=0.28 * inch,
            spaceBefore=6,
            spaceAfter=6,
        ),
        "document": ParagraphStyle(
            "Document",
            fontName=fonts["italic"],
            fontSize=body_size - 0.25,
            leading=leading,
            leftIndent=0.35 * inch,
            rightIndent=0.35 * inch,
            borderWidth=0.5,
            borderColor=colors.HexColor("#999999"),
            borderPadding=10,
            spaceBefore=10,
            spaceAfter=10,
        ),
        "list": ParagraphStyle(
            "List",
            fontName=fonts["regular"],
            fontSize=body_size,
            leading=leading,
            leftIndent=0.2 * inch,
            firstLineIndent=-0.15 * inch,
        ),
        "scene": ParagraphStyle(
            "Scene",
            fontName=fonts["regular"],
            fontSize=8,
            leading=12,
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=8,
        ),
        "toc": ParagraphStyle(
            "Toc",
            fontName=fonts["regular"],
            fontSize=9,
            leading=12,
        ),
        "toc_page": ParagraphStyle(
            "TocPage",
            fontName=fonts["regular"],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
        ),
    }


def _register_fonts(config: BookConfig) -> dict[str, str]:
    font_dir = Path(reportlab.__file__).resolve().parent / "fonts"
    paths = {
        "regular": config.typography.regular or font_dir / "Vera.ttf",
        "bold": config.typography.bold or font_dir / "VeraBd.ttf",
        "italic": config.typography.italic or font_dir / "VeraIt.ttf",
        "bold_italic": config.typography.bold_italic or font_dir / "VeraBI.ttf",
    }
    digest = hashlib.sha256()
    for style, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Typography font not found: {path}")
        digest.update(style.encode("ascii"))
        digest.update(path.read_bytes())
    family = f"Scriber-{config.slug}-{digest.hexdigest()[:10]}"
    names = {
        "regular": f"{family}-Regular",
        "bold": f"{family}-Bold",
        "italic": f"{family}-Italic",
        "bold_italic": f"{family}-BoldItalic",
    }
    if names["regular"] in pdfmetrics.getRegisteredFontNames():
        return names
    for style, path in paths.items():
        pdfmetrics.registerFont(TTFont(names[style], str(path)))
    pdfmetrics.registerFontFamily(
        family,
        normal=names["regular"],
        bold=names["bold"],
        italic=names["italic"],
        boldItalic=names["bold_italic"],
    )
    return names


def _inline(value: str) -> str:
    escaped = html.escape(value, quote=False)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", escaped)
    return escaped


def _ensure_even_page_count(path: Path) -> int:
    reader = PdfReader(str(path))
    count = len(reader.pages)
    if count % 2 == 0:
        return count
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    first_page = reader.pages[0]
    writer.add_blank_page(
        width=float(first_page.mediabox.width),
        height=float(first_page.mediabox.height),
    )
    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))
    temporary = path.with_suffix(".even.pdf")
    with temporary.open("wb") as handle:
        writer.write(handle)
    temporary.replace(path)
    return count + 1


def _strip_unused_default_font(path: Path) -> None:
    reader = PdfReader(str(path))
    writer = PdfWriter()
    initialization = re.compile(
        rb"BT\s+/F1\s+[-+]?(?:\d+(?:\.\d*)?|\.\d+)\s+Tf\s+"
        rb"[-+]?(?:\d+(?:\.\d*)?|\.\d+)\s+TL\s+ET"
    )
    font_use = re.compile(rb"/F1\s+[-+]?(?:\d+(?:\.\d*)?|\.\d+)\s+Tf")
    for source_page in reader.pages:
        page = source_page
        content = page.get_contents()
        remaining = b""
        if content is not None:
            remaining = initialization.sub(b"", content.get_data())
            stream = DecodedStreamObject()
            stream.set_data(remaining)
            page[NameObject("/Contents")] = stream
        resources = page.get("/Resources")
        if resources is not None and not font_use.search(remaining):
            fonts = resources.get_object().get("/Font")
            if fonts is not None:
                font_dictionary = fonts.get_object()
                if NameObject("/F1") in font_dictionary:
                    del font_dictionary[NameObject("/F1")]
        writer.add_page(page)
    if reader.metadata:
        writer.add_metadata(dict(reader.metadata))
    temporary = path.with_suffix(".fonts.pdf")
    with temporary.open("wb") as handle:
        writer.write(handle)
    temporary.replace(path)
