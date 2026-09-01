# Scriber

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Status: Beta](https://img.shields.io/badge/Status-Beta-orange.svg)](CHANGELOG.md)

Scriber turns Markdown manuscripts into print-ready paperback interiors, reflowable EPUB 3 ebooks, cover templates, compiled covers, and publication manifests. It is designed for authors who want to write chapters and front or back matter without maintaining a publishing toolchain.

One workspace can contain any number of books. Each book is built and validated independently.

## Install

Scriber requires Python 3.11 or newer. Install the current public source with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/ccarvalho-eng/scriber.git
```

Or use pipx:

```bash
pipx install git+https://github.com/ccarvalho-eng/scriber.git
```

To install the current source version instead:

```bash
git clone https://github.com/ccarvalho-eng/scriber.git
cd scriber
uv tool install .
```

After the first PyPI release, the distribution can be installed and upgraded by name:

```bash
uv tool install scriber-books
uv tool upgrade scriber-books
```

### Update or reinstall Scriber

To replace an existing uv installation with the latest version from GitHub, use `--force`:

```bash
uv tool install --force git+https://github.com/ccarvalho-eng/scriber.git
scriber --version
```

For pipx installations:

```bash
pipx install --force git+https://github.com/ccarvalho-eng/scriber.git
scriber --version
```

You can also install a specific Git branch, tag, or commit by appending its ref to the repository URL:

```bash
uv tool install --force "git+https://github.com/ccarvalho-eng/scriber.git@v0.2.0"
```

Replace `v0.2.0` with the branch name, tag, or commit you need. The `scriber upgrade` command upgrades book configuration files to the current schema; it does not update the installed Scriber program.

## Create your first book

Run one command in the directory that will hold your library:

```bash
scriber new winter-road \
  --title "The Winter Road" \
  --subtitle "A Novel" \
  --author "Author Name"
```

Scriber creates a fill-in-ready skeleton:

```text
scriber.toml
books/
  winter-road/
    book.toml
    manuscript/
      front_matter/
        00_title.md
        01_copyright.md
        02_dedication.md
        03_contents.md
      chapters/
        01_chapter.md
      back_matter/
        01_acknowledgements.md
        02_about_the_author.md
    assets/
      cover/
      fonts/
```

Write in the generated Markdown files. Add chapters with ordered names such as `02_the_crossing.md` and `03_nightfall.md`. Files are assembled in filename order. Delete optional matter you do not want and add more files whenever needed.

## Build

From the workspace directory, build every book:

```bash
scriber build
```

Build only selected books:

```bash
scriber build winter-road second-novel
```

Every book receives an isolated `dist/` directory:

```text
dist/
  pdf/
    winter-road_kdp_interior.pdf
  epub/
    winter-road.epub
  cover/
    winter-road_cover_template.png
  dimensions.json
  publication_manifest.json
```

The manifest records the publishing profile, stabilized page count, resolved gutter, section pages, identifiers, validation results, file sizes, and SHA-256 checksums.

## Write the manuscript

Each file starts with one level-one heading:

```markdown
# Chapter One

The first paragraph begins without an indent.

Later paragraphs receive the configured first-line indent automatically. Use
*italics* and **bold** where needed.

## A section heading

> Block quotations use Markdown quote syntax.

* * *

A scene break uses three spaced asterisks or three hyphens.
```

Supported authoring elements are headings, paragraphs, emphasis, block quotes, ordered and unordered lists, character document blocks, and scene breaks. Scriber handles mirrored margins, chapter opening pages, running furniture, page numbering, the generated print contents page, ebook navigation, widow and orphan control, and language-aware hyphenation.

Physical notes, letters, and documents read by characters use Scriber document blocks:

```markdown
::: note
Meet me at the north gate after midnight.

— Elin
:::
```

See the [Author guide](docs/author-guide.md) for epigraphs, quotations, document inserts, endnotes, and front or back matter patterns.

## Add a cover

Generate the exact cover guide after the manuscript has been paginated:

```bash
scriber cover-template winter-road
```

The PNG in `dist/cover/` shows the final trim, spine folds, safe areas, bleed, and barcode reservation. Its width accounts for the final interior page count and selected paper stock.

Place finished panels here:

```text
books/winter-road/assets/cover/front.png
books/winter-road/assets/cover/back.png
```

Run `scriber build` again. Cover compilation activates automatically and creates:

```text
dist/cover/
  winter-road_paperback_cover.pdf
  winter-road_paperback_cover_preview.jpg
  winter-road_ebook_cover.jpg
```

Scriber checks panel dimensions, effective resolution, crop risk, compiled PDF size, spine width, and ebook-cover presence. Spine text is omitted automatically below the publishing profile's supported page threshold.

## Prepare a release

Draft builds allow short manuscripts and report retailer issues as warnings. A release build enforces the complete publication gate:

```bash
scriber release
```

The equivalent explicit form is:

```bash
scriber build --release
```

Release mode checks:

- page count, trim size, mirrored gutter, even pagination, and embedded fonts;
- KDP profile limits and page-count-dependent cover geometry;
- ISBN check digits and publication metadata;
- EPUB ZIP structure, XML, navigation, metadata, and reading order;
- cover dimensions, source resolution, and crop risk;
- the finished EPUB with the official EPUBCheck command;
- accessibility with Ace by DAISY when Ace is installed.

Check validator availability before the final build:

```bash
scriber doctor
```

Scriber uses `epubcheck` when it is on `PATH`. A standalone EPUBCheck JAR is also supported:

```bash
export EPUBCHECK_JAR=/path/to/epubcheck.jar
scriber release
```

[EPUBCheck](https://github.com/w3c/epubcheck) is required for release mode. [Ace by DAISY](https://daisy.github.io/ace/) is optional but recommended for an accessibility audit.

## Configure publication metadata

Routine authoring does not require changing `book.toml`. Before publication, fill the metadata used by the EPUB and manifest:

```toml
[book]
title = "The Winter Road"
subtitle = "A Novel"
author = "Author Name"
language = "en-US"
copyright_year = 2026
edition_date = "2026-08-31"
description = "Retailer description for the novel."
publisher = "Example Press"
imprint = "North Line"
series = "Winter Roads"
series_number = "1"
isbn_print = ""
isbn_epub = ""
subjects = ["Fiction / Fantasy / Epic"]
```

Leave ISBN values empty when the retailer will assign them. If supplied, Scriber validates ISBN-10 and ISBN-13 check digits.

The default KDP paperback profile uses a 6 × 9 inch, black-ink, cream-paper, no-bleed interior. Advanced layout and publishing options are documented in [Configuration](docs/configuration.md).

## Use custom fonts

Add a complete licensed font family under `assets/fonts/`, then configure its four faces:

```toml
[typography]
regular = "assets/fonts/Family-Regular.ttf"
bold = "assets/fonts/Family-Bold.ttf"
italic = "assets/fonts/Family-Italic.ttf"
bold_italic = "assets/fonts/Family-BoldItalic.ttf"
hyphenation = true
```

All four files are required so print emphasis remains embedded and predictable. Without custom files, Scriber uses its portable bundled type family.

## Manage several books

Create another skeleton with another slug:

```bash
scriber new second-novel --title "Second Novel" --author "Author Name"
```

List the library:

```bash
scriber list
```

`scriber build` and `scriber release` process all discovered books. Pass one or more slugs to limit either command.

## Upgrade a workspace

Preview configuration migrations:

```bash
scriber upgrade --dry-run
```

Apply them:

```bash
scriber upgrade
```

Scriber continues to read version 1 configurations. New skeletons use the current versioned schema and convention-based content discovery.

## Publish on Amazon KDP

After `scriber release` succeeds:

1. Upload the PDF from `dist/pdf/` as the paperback manuscript.
2. Upload the paperback PDF from `dist/cover/` as the print cover.
3. Upload the EPUB from `dist/epub/` for the Kindle edition.
4. Copy the title, contributor, ISBN, series, and description values into the retailer listing.
5. Inspect every page and cover boundary in the retailer previewers before submitting.

Retailer specifications can change. Scriber versions its built-in profile, but the retailer preview and current KDP guidance remain the final authority.

## More documentation

- [Documentation index](docs/README.md)
- [Getting started](docs/getting-started.md)
- [Author guide](docs/author-guide.md)
- [Command reference](docs/commands.md)
- [Cover guide](docs/covers.md)
- [Configuration reference](docs/configuration.md)
- [Output reference](docs/output.md)
- [Publishing checklist](docs/publishing.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture and reproducibility](docs/architecture.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

Scriber is licensed under the [Apache License 2.0](LICENSE).
