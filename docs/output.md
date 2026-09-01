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
  publication_manifest.json
```

Cover files other than the template exist only when cover compilation is enabled.

## Print interior PDF

The interior uses the configured trim size, mirrored margins, page-count-dependent inside margin, embedded fonts, recto body starts, print contents page, and even final page count. Upload this file as the paperback manuscript.

## EPUB

The EPUB is a deterministic EPUB 3 archive with reflowable XHTML, semantic matter types, navigation, language, rights, accessibility metadata, optional publication metadata, and optional ebook cover. Upload it for the ebook edition after release validation.

## Cover files

See the [Cover guide](covers.md). The print cover PDF is the full paperback wrap; the ebook JPEG is front artwork only. The preview is for review and should not be uploaded in place of the PDF.

## `dimensions.json`

This machine-readable summary records:

- profile and page count;
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
