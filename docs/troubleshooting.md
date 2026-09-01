# Troubleshooting

## Command not found

Confirm the tool installation:

```bash
uv tool list
```

Reinstall with `uv tool install git+https://github.com/ccarvalho-eng/scriber.git` and ensure the tool bin directory reported by uv is on `PATH`.

## No books found

Run from a workspace containing `books/<slug>/book.toml`, or pass:

```bash
scriber --workspace /path/to/library list
```

## Invalid book slug

Use lowercase letters, digits, and single hyphens: `winter-road`. Spaces, underscores, uppercase letters, leading hyphens, and repeated hyphens are invalid.

## Content pattern matched no files

An explicit `[contents]` pattern selects nothing. Correct the path, add the missing Markdown file, or remove the override to use convention discovery.

## Content file must begin with an H1 title

Add one `# Heading` to the file. Keep later headings at `##`.

## Empty or unclosed document block

Every character note, letter, or document needs content and a closing `:::`:

```markdown
::: note
The note text.
:::
```

## Pagination did not stabilize

The contents page and margin calculation did not converge within the bounded pass count. Check extremely long section titles, unusually narrow trim or margins, and oversized font settings. Restore normal layout values and build again.

## Margins leave less than one inch for text

The trim is too narrow for the configured inside and outside margins. Increase trim width or reduce custom margins without going below the publishing profile minimum.

## Paperback is below the profile minimum

Draft builds warn; release builds fail. Continue writing or choose a retailer format that accepts the final length. Do not add meaningless blank pages solely to bypass a retailer minimum.

## Trim size is not verified

Draft builds can render a custom trim, but release builds require a size covered by the active versioned retailer profile. For a typical novel, use 5 × 8, 5.25 × 8, 5.5 × 8.5, or 6 × 9 inches. If the retailer has changed its options, open an issue with the current primary documentation rather than bypassing the release check.

## Unsupported ink and paper combination

Black ink supports white, cream, or groundwood paper. Standard and premium color use white paper. Change `publish.ink` or `publish.paper` to a valid pair; Scriber will not guess because the selection affects page limits and spine width.

## Interior contains unembedded fonts

Provide all four custom TTF faces and verify that ReportLab can embed them. Do not use a system-only font or a font whose embedding rights are unclear.

## Cover resolution or crop warning

Export the affected panel at the template's pixel dimensions and aspect ratio. Do not rely on DPI metadata or automatic upscaling.

## Cover files are not generated

With `enabled = "auto"`, both `assets/cover/front.png` and `assets/cover/back.png` must exist when configuration is loaded. Check names and case, then build again.

## EPUBCheck is required

Install the official EPUBCheck command, or download its official distribution, install Java, and set:

```bash
export EPUBCHECK_JAR=/path/to/epubcheck.jar
```

Run `scriber doctor` before retrying `scriber release`.

## Ace was skipped

Ace by DAISY is optional. Install its `ace` command and run release validation again to include the accessibility audit.

## Invalid ISBN

Enter the ISBN exactly as assigned for that format. Spaces and hyphens are accepted, but the ISBN-10 or ISBN-13 check digit must be valid. Leave the field empty when no ISBN has been assigned.

## Output changed between releases

Compare `publication_manifest.json` files. Inputs, rendering dependency versions, profile versions, and configuration can affect checksums. Use the lockfile and manifest retained with the released edition.

## Report a bug safely

Do not publish an unpublished manuscript in an issue. Create a minimal replacement text that reproduces the failure and include the Scriber version, sanitized configuration, command, and error.
