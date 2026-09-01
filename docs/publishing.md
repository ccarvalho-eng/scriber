# Publishing checklist

## Manuscript

- Open `proof_report.html` and resolve every blocking error.
- Confirm title, subtitle, author, copyright year, language, and edition date.
- Remove placeholder text and unwanted starter matter.
- Check chapter order and headings.
- Review scene breaks, emphasis, quotations, and intentional blank pages.
- Fill retailer description, publisher or imprint, series, subjects, and owned ISBNs.

## Print interior

- Run `scriber release <slug>`.
- Confirm the page count is within the active profile.
- Inspect mirrored margins, chapter recto starts, page numbers, running furniture, contents entries, widows, orphans, and final blank pages.
- Confirm all illustrations, if any are added in future versions, meet the intended print resolution and rights requirements.

## Cover

- Design against the latest generated template after final pagination.
- Keep text and essential artwork inside green safe areas.
- Keep the barcode reservation clear unless the final cover intentionally includes an owned barcode.
- Inspect the compiled PDF dimensions and preview.
- Rebuild the cover after any page-count or paper change.

## Ebook

- Require a passing EPUBCheck result.
- Run Ace by DAISY when available and review its report.
- Check navigation, reading order, language, title metadata, cover, paragraph flow, and scene breaks in at least one Kindle-compatible previewer.

## Retailer submission

- Copy listing values from `retailer_metadata.md`.
- Upload the interior, cover, and EPUB from the matching build.
- Match retailer metadata to `book.toml`.
- Use the correct ISBN for each format.
- Review the retailer's current requirements and every page in its previewer.
- Preserve `publication_manifest.json` with the submitted edition so later builds can be compared by checksum.
