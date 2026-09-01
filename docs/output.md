# Output reference

Scriber writes each book beneath `books/<slug>/dist/`.

```text
dist/
  pdf/
    <slug>_kdp_interior.pdf
  epub/
    <slug>.epub
  cover/
    <slug>_cover_template.png
    <slug>_paperback_cover.pdf
    <slug>_paperback_cover_preview.jpg
    <slug>_ebook_cover.jpg
  dimensions.json
  proof_report.html
  retailer_metadata.md
  publication_manifest.json
```

Cover files other than the template exist only when cover compilation is enabled.

## `proof_report.html`

Open this file first. It is a self-contained author report with the build status, edition settings, blocking errors, warnings, section start pages, validation checks, EPUB identifier, and links to the generated artifacts. `READY` means there are no current validation errors or warnings, `REVIEW` means the build completed with warnings, and `BLOCKED` means at least one error must be corrected.

Draft validation deliberately reports retailer minimums as warnings so an unfinished manuscript remains buildable. `scriber release` promotes retailer compatibility problems to errors.

## `retailer_metadata.md`

This copy-friendly sheet contains the title, contributors, identifiers, description, subjects, edition settings, final page count, allowed page range, and expected upload filenames. Use it when filling the retailer listing so the entered details match the interior and cover.

## Print interior PDF

The interior uses the configured trim size, mirrored margins, page-count-dependent inside margin, embedded fonts, recto body starts, print contents page, and even final page count. Upload this file as the paperback manuscript.

## EPUB

The EPUB is a deterministic EPUB 3 archive with reflowable XHTML, semantic matter types, navigation, language, rights, accessibility metadata, optional publication metadata, and optional ebook cover. Upload it for the ebook edition after release validation.

## Cover files

See the [Cover guide](covers.md). The print cover PDF is the full paperback wrap; the ebook JPEG is front artwork only. The preview is for review and should not be uploaded in place of the PDF.

## `dimensions.json`

This machine-readable summary records:

- profile and page count;
- profile version and primary source;
- trim dimensions;
- resolved inside margin;
- bleed, spine, wrap width, and wrap height.

Use it to communicate exact geometry to a cover designer or verify that two builds target the same physical format.

## `publication_manifest.json`

The manifest is the edition record. It contains:

- schema and canonical build timestamp;
- book and format metadata;
- publishing profile version;
- page count, layout pass count, resolved gutter, and section page map;
- EPUB identifier and section count;
- validation errors and warnings;
- every deliverable's relative path, byte size, and SHA-256 checksum.

Archive the manifest with files submitted to a retailer. A later checksum difference proves that a deliverable changed even when its filename did not.

## Temporary files

Pagination passes and EPUB staging directories are internal and removed automatically. A failed process can leave hidden pass files in a format subdirectory; they are not publication artifacts and can be removed after confirming no build is running.
