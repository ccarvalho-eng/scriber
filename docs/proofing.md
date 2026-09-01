# Proof and metadata reports

Every build creates two human-readable files at the root of the book's `dist/` directory. They are generated from the same stabilized pagination, configuration, and validation result as the publication artifacts.

## Start with `proof_report.html`

Open the report in a browser after `scriber build` or `scriber release`. Its status has three possible values:

- `READY`: validation completed without errors or warnings.
- `REVIEW`: the build is usable, but one or more warnings require author judgment.
- `BLOCKED`: at least one problem must be corrected before publication.

The report records the publishing profile, trim, ink, paper, final page count, completed checks, section start pages, EPUB identifier, and links to the generated files. It does not replace reading the interior PDF, checking the EPUB in a Kindle-compatible previewer, or reviewing the retailer's online preview.

Draft builds keep short manuscripts and unverified custom trims buildable by reporting retailer compatibility as warnings. Release builds treat those conditions as errors. A release also checks the selected ink/paper page range, minimum text size, embedded fonts, title and author presence in the opening pages, excessive consecutive blank pages, cover size and geometry, EPUB structure, and external EPUB validation.

## Use `retailer_metadata.md` during title setup

The metadata sheet prevents subtle differences between the retailer listing and the publication files. Copy values from it instead of retyping from memory. Empty optional values are marked `Not set` so missing descriptions, identifiers, publisher details, or subjects are visible before submission.

The sheet also records the final page count and expected upload filenames. Generate it again after any manuscript, layout, paper, ink, metadata, or cover change.

## What still requires judgment

Automated checks cannot approve prose, factual accuracy, quotation permissions, cover rights, pricing, categories, keywords, or visual taste. Always inspect the final PDF and EPUB and order a physical proof before a first print publication or a material layout change.
