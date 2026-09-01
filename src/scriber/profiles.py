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
    version: str = "2026-09-01"
    source_url: str = "https://kdp.amazon.com/en_US/help/topic/G201834180"
    cover_bleed_inches: float = 0.125
    minimum_pages: int = 24

    @property
    def verified_trim_sizes(self) -> tuple[tuple[float, float], ...]:
        """Return KDP trim sizes covered by the embedded page-limit matrix."""

        return (
            (5.0, 8.0),
            (5.06, 7.81),
            (5.25, 8.0),
            (5.5, 8.5),
            (6.0, 9.0),
            (6.14, 9.21),
            (6.69, 9.61),
            (7.0, 10.0),
            (7.44, 9.69),
            (7.5, 9.25),
            (8.0, 10.0),
        )

    def trim_supported(self, width: float, height: float) -> bool:
        return any(
            abs(width - supported_width) < 0.001
            and abs(height - supported_height) < 0.001
            for supported_width, supported_height in self.verified_trim_sizes
        )

    def page_limits(
        self,
        trim_width_inches: float,
        trim_height_inches: float,
        ink: str,
        paper: str,
    ) -> tuple[int, int]:
        """Return current KDP limits for a verified print-option combination."""

        if not self.trim_supported(trim_width_inches, trim_height_inches):
            raise ValueError(
                f"{trim_width_inches:g} x {trim_height_inches:g} inches is not a "
                "verified KDP paperback trim size in this Scriber profile"
            )
        key = (ink.lower(), paper.lower())
        limits = {
            ("black", "white"): (24, 828),
            ("black", "cream"): (24, 776),
            ("black", "groundwood"): (24, 812),
            ("standard-color", "white"): (72, 600),
            ("premium-color", "white"): (24, 828),
        }
        if key not in limits:
            raise ValueError(
                f"Unsupported KDP paperback ink and paper combination: {ink}/{paper}"
            )
        return limits[key]

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
            raise ValueError(
                f"Unsupported KDP paperback ink and paper combination: {ink}/{paper}"
            )
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
