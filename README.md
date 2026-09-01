# Scriber

Scriber compiles one or more Markdown book projects into print interiors, EPUBs,
and optional paperback covers assembled from supplied artwork.

## Create a book

From an empty directory, one command creates the workspace and a complete book
skeleton:

```bash
scriber new winter-road \
  --title "The Winter Road" \
  --author "Author Name"
```

The generated project is deliberately small:

```text
scriber.toml
books/
  winter-road/
    book.toml
    front/
      00_title.md
      01_copyright.md
      02_dedication.md
      03_contents.md
    manuscript/
      01_chapter.md
    back/
      01_acknowledgements.md
      02_about_the_author.md
    assets/
      cover/
```

Add as many books as needed by running `scriber new` with another slug.

## Build

Build every book in the workspace:

```bash
scriber build
```

Build selected books:

```bash
scriber build winter-road second-novel
```

Each book receives its own `dist/` directory:

```text
dist/
  paperback-interior.pdf
  book.epub
  dimensions.json
  build-manifest.json
```

When `[cover].enabled` is true and both panel images exist, Scriber also creates:

```text
dist/
  paperback-cover.pdf
  paperback-cover-preview.jpg
  ebook-cover.jpg
```

The interior is rendered before the cover. Scriber uses the stabilized final page
count to select the gutter, calculate the spine, and assemble the print cover.

## Validate

```bash
scriber validate
```

Validation checks the retailer page range, trim size, even pagination, embedded
fonts, EPUB package structure, and compiled cover dimensions. An external
EPUBCheck run and visual review in the retailer previewer remain release gates.

Scriber 0.1 targets text-led, no-bleed paperback interiors. Interior bleed is
rejected explicitly instead of silently producing unsafe page geometry.

## Publishing profile

The built-in `kdp-paperback` profile is versioned. Its margin, bleed, and spine
formulas follow Amazon KDP's official paperback submission and cover guidance:

- <https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6>
- <https://kdp.amazon.com/en_US/help/topic/G201857950>
- <https://kdp.amazon.com/en_US/help/topic/G201953020>

Retailer rules can change. Review and update the profile before a release rather
than treating an old Scriber version as a permanent source of publishing rules.
