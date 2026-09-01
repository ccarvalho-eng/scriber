from __future__ import annotations

import unittest

from scriber.profiles import KdpPaperbackProfile


class KdpPaperbackProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = KdpPaperbackProfile()

    def test_gutter_bands_follow_page_count(self) -> None:
        cases = {
            24: 0.375,
            150: 0.375,
            151: 0.5,
            300: 0.5,
            301: 0.625,
            500: 0.625,
            501: 0.75,
            700: 0.75,
            701: 0.875,
            828: 0.875,
        }
        for pages, expected in cases.items():
            with self.subTest(pages=pages):
                self.assertEqual(
                    self.profile.minimum_inside_margin(pages),
                    expected,
                )

    def test_cream_spine_and_cover_dimensions(self) -> None:
        dimensions = self.profile.cover_dimensions(
            page_count=400,
            trim_width_inches=6,
            trim_height_inches=9,
            ink="black",
            paper="cream",
        )
        self.assertEqual(dimensions.spine_inches, 1.0)
        self.assertEqual(dimensions.width_inches, 13.25)
        self.assertEqual(dimensions.height_inches, 9.25)

    def test_spine_text_requires_eighty_pages(self) -> None:
        self.assertFalse(self.profile.spine_text_allowed(79))
        self.assertTrue(self.profile.spine_text_allowed(80))


if __name__ == "__main__":
    unittest.main()
