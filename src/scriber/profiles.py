"""Versioned retailer publishing rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CoverDimensions:
    page_count: int
    spine_inches: float
    width_inches: float
    height_inches: float
    bleed_inches: float


@dataclass(frozen=True)
class KdpPaperbackProfile:
    name: str = "kdp-paperback"
    version: str = "2026-08-31"
    cover_bleed_inches: float = 0.125
    minimum_pages: int = 24

    def minimum_inside_margin(self, page_count: int) -> float:
        for maximum, margin in (
            (150, 0.375),
            (300, 0.5),
            (500, 0.625),
            (700, 0.75),
            (828, 0.875),
        ):
            if page_count <= maximum:
                return margin
        raise ValueError("KDP paperback page count exceeds 828 pages")

    def minimum_outside_margin(self, interior_bleed: bool) -> float:
        if interior_bleed:
            return 0.375
        return 0.25

    def spine_inches_per_page(self, ink: str, paper: str) -> float:
        key = (ink.lower(), paper.lower())
        values = {
            ("black", "white"): 0.002252,
            ("black", "cream"): 0.0025,
            ("black", "groundwood"): 0.00235,
            ("premium-color", "white"): 0.002347,
            ("standard-color", "white"): 0.002252,
        }
        if key not in values:
            raise ValueError(f"Unsupported KDP ink and paper combination: {key}")
        return values[key]

    def cover_dimensions(
        self,
        page_count: int,
        trim_width_inches: float,
        trim_height_inches: float,
        ink: str,
        paper: str,
    ) -> CoverDimensions:
        spine = page_count * self.spine_inches_per_page(ink, paper)
        width = (
            self.cover_bleed_inches
            + trim_width_inches
            + spine
            + trim_width_inches
            + self.cover_bleed_inches
        )
        height = trim_height_inches + (2 * self.cover_bleed_inches)
        return CoverDimensions(
            page_count=page_count,
            spine_inches=spine,
            width_inches=width,
            height_inches=height,
            bleed_inches=self.cover_bleed_inches,
        )

    def spine_text_allowed(self, page_count: int) -> bool:
        return page_count > 79


def get_profile(name: str) -> KdpPaperbackProfile:
    if name != "kdp-paperback":
        raise ValueError(f"Unknown publishing profile: {name}")
    return KdpPaperbackProfile()
