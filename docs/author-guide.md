# Author guide

This guide covers the manuscript patterns Scriber formats consistently in both print and EPUB. Start every content file with one level-one heading.

## Organize a novel

Files are assembled in filename order:

```text
manuscript/
  front_matter/
    00_title.md
    01_copyright.md
    02_dedication.md
    03_epigraph.md
    04_contents.md
  chapters/
    00_prologue.md
    01_chapter.md
    02_chapter.md
    99_epilogue.md
  back_matter/
    01_author_note.md
    02_acknowledgements.md
    03_notes.md
    04_glossary.md
    05_about_the_author.md
```

Only include matter the book needs. Rename files freely while preserving a numeric ordering prefix. Recognized names add EPUB semantics for title pages, copyright, dedications, epigraphs, forewords, prefaces, prologues, interludes, epilogues, afterwords, contents, author notes, endnotes, glossaries, bibliographies, acknowledgements, and author biographies.

## Paragraphs and dialogue

Separate paragraphs with a blank line:

```markdown
The door opened before Mara could knock.

“You came,” Tomas said.

“You asked me to.”
```

Write ordinary spoken dialogue with the quotation marks appropriate for the book's language. Do not prefix dialogue with `>`; that syntax is reserved for displayed quotations.

The first paragraph after a chapter heading, section heading, scene break, quotation, or document insert is not indented. Later paragraphs receive the configured first-line indent automatically.

## Italics and bold

Use single asterisks for italics:

```markdown
The word *home* no longer meant what it once had.
```

Use double asterisks for bold only when the book genuinely requires it:

```markdown
The sign read **KEEP OUT**.
```

Italics are commonly used for emphasis, internalized words, titles of long works, and isolated foreign terms. Follow one editorial convention consistently. Avoid using italics for every internal thought unless that is an intentional style choice.

Do not use raw HTML for typography. Scriber escapes manuscript text and handles supported emphasis itself.

## Scene breaks

Put either marker on a line by itself:

```markdown
* * *
```

or:

```markdown
---
```

Both produce Scriber’s centered scene-break ornament and reset the next paragraph's indent. Use scene breaks for a meaningful change in time, location, or point of view within a chapter.

## Section headings inside a chapter

Use a level-two heading:

```markdown
## Three Days Earlier
```

Do not use another level-one heading inside the same file. A new `#` heading belongs in a new ordered content file.

## Epigraphs

### Book epigraph

Create an ordered front-matter file such as `03_epigraph.md`:

```markdown
# Epigraph

> We tell ourselves stories in order to live.
>
> — Joan Didion, *The White Album*
```

### Chapter epigraph

Place a displayed quotation immediately below the chapter title:

```markdown
# Chapter Seven

> Every map begins as an argument with distance.
>
> — *The Surveyor's Almanac*

Snow had covered the eastern road by dawn.
```

The attribution belongs inside the same quote block. Verify the wording, attribution, public-domain status, or permission for every quotation. A short quotation is not automatically safe to publish merely because it is used as an epigraph.

## Displayed quotations

Use `>` for a quotation that should be visually separated from the surrounding prose:

```markdown
The final paragraph had been underlined twice:

> No vessel may pass the northern marker after sunset. The harbor authority accepts no liability for loss beyond that point.

Mara read it again.
```

Use ordinary quotation marks for dialogue and brief quotations that remain part of a paragraph.

## Notes, letters, and documents read by characters

Scriber provides fenced document blocks for physical text inside the story. These render as inset, bordered, italic document panels in print and EPUB.

### A short note

```markdown
::: note
Meet me at the north gate after midnight.

Come alone.

— Elin
:::
```

### A letter

```markdown
::: letter
Dear Mara,

By the time you read this, the winter road will be closed. Do not follow us.

Your brother,
Tomas
:::
```

### A notice, journal page, report, or other document

```markdown
::: document
HARBOR AUTHORITY

Northern passage suspended until further notice.

Issued on the ninth day of winter.
:::
```

The closing `:::` is required. Blank lines and line breaks inside the block are preserved. Supported labels are `note`, `letter`, and `document`.

Use these blocks only when the typography represents an object a character sees or reads. Use a block quote for quoted speech or a passage cited by the narrator.

## Lists

Use hyphens for unordered material:

```markdown
- lamp oil
- two blankets
- the brass key
```

Use numbered Markdown for ordered steps or endnotes:

```markdown
1. Archive ledger, winter register, page 14.
2. Harbor Authority circular 7B.
```

Scriber emits semantic unordered and ordered lists in EPUB.

## Author's notes and notes to the reader

An author's note is book matter, not an in-story character note. Put it in back matter:

```markdown
# Author's Note

This novel is fictional, but its winter navigation practices were inspired by...
```

A note that readers must see before the story belongs in front matter and can be named `note_to_reader.md`:

```markdown
# Note to the Reader

This edition retains the historical spelling used in quoted documents.
```

## Endnotes

Scriber does not currently implement linked footnotes. Use an ordered `notes.md` or `endnotes.md` file in back matter:

```markdown
# Notes

1. Chapter Two: description of the harbor chain.
2. Chapter Nine: translation of the northern inscription.
```

Do not use unsupported `[^1]` footnote syntax; it will remain literal text.

## Prologues, interludes, and epilogues

Place story sections in `manuscript/chapters/` so they participate in body pagination:

```markdown
# Prologue

The bell began ringing before the snow reached the valley.
```

Use descriptive filenames such as `00_prologue.md`, `10_interlude.md`, and `99_epilogue.md`. These names receive matching EPUB structural semantics and follow the configured recto-start rule.

## Common back matter

### Acknowledgements

```markdown
# Acknowledgements

Thank the people and institutions that contributed to the book.
```

### Glossary

```markdown
# Glossary

## Frostroad

The marked winter route between northern settlements.
```

### About the author

```markdown
# About the Author

Author Name writes...
```

## Unsupported constructs

Scriber 0.2 intentionally keeps the manuscript language small. It does not yet support linked footnotes, tables, embedded manuscript images, raw HTML, fenced code blocks, task lists, or nested lists. Release validation cannot correct quotation permissions, factual errors, or editorial consistency.

When a needed construct is unsupported, prefer a clear prose or endnote alternative rather than relying on Markdown that may render as literal text.
