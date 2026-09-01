# Configuration reference

Each book has a `book.toml`. New configurations use `schema_version = 2`.

## Book metadata

The `[book]` table supports:

| Field | Required | Purpose |
| --- | --- | --- |
| `title` | yes | Primary title |
| `subtitle` | no | Subtitle appended to the full title |
| `author` | yes | Primary creator |
| `language` | yes | BCP 47 language tag used for EPUB and hyphenation |
| `copyright_year` | yes | Rights statement year |
| `edition_date` | yes | ISO date used for EPUB metadata and reproducible timestamps |
| `description` | no | Retailer description embedded in EPUB metadata |
| `publisher` / `imprint` | no | Publishing identity |
| `series` / `series_number` | no | EPUB series metadata |
| `isbn_print` / `isbn_epub` | no | Format-specific identifiers |
| `subjects` | no | Subject strings embedded in EPUB metadata |

## Content discovery

No `[contents]` table is needed for the standard structure. Scriber discovers:

```toml
[contents]
front = ["manuscript/front_matter/*.md"]
body = ["manuscript/chapters/*.md"]
back = ["manuscript/back_matter/*.md"]
```

Add the table only to override these patterns. Paths must remain inside the book directory and cannot select the same file twice.

## Layout

```toml
[layout]
trim_width_inches = 6.0
trim_height_inches = 9.0
inside_margin_inches = "auto"
outside_margin_inches = 0.5
top_margin_inches = 0.7
bottom_margin_inches = 0.7
gutter_safety_inches = 0.125
body_font_size = 10.5
body_leading = 14.5
chapter_font_size = 20
paragraph_indent_inches = 0.22
chapter_start_recto = true
```

The automatic inside margin is resolved from the final page count and current publishing profile. A numeric value acts as a floor; Scriber still raises it when the profile requires more space.

## Typography

```toml
[typography]
hyphenation = true
```

To use a custom family, provide `regular`, `bold`, `italic`, and `bold_italic` paths. Font paths must stay within the book directory. Verify that the license permits embedding and commercial publication.

## Publishing profile

```toml
[publish]
profile = "kdp-paperback"
format = "paperback"
ink = "black"
paper = "cream"
interior_bleed = false
max_pages = 828
dpi = 300
```

Scriber 0.2 supports text-led, no-bleed paperback interiors. Unsupported options are rejected instead of silently producing incorrect geometry.

## Cover

```toml
[cover]
enabled = "auto"
front = "assets/cover/front.png"
back = "assets/cover/back.png"
background = "#20242a"
spine_title = true
spine_author = true
text_color = "#ffffff"
```

`enabled = "auto"` compiles the cover when both panels exist. Use `false` to ignore artwork or `true` to require both panels.
