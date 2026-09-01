# Command reference

## Global option

All commands accept the workspace through the global option:

```bash
scriber --workspace /path/to/library <command>
```

The default workspace is the current directory. Put `--workspace` before the command name.

Print the installed version with `scriber --version` and command help with `scriber --help`.

## `scriber init`

Creates `scriber.toml` and `books/` without creating a book:

```bash
scriber init
```

Running it again is safe and reports that the workspace is already initialized.

## `scriber new`

Creates the workspace when needed and generates a complete book skeleton:

```bash
scriber new <slug> --title <title> --author <author> [options]
```

Options:

| Option | Required | Default |
| --- | --- | --- |
| `--title` | yes | none |
| `--author` | yes | none |
| `--subtitle` | no | empty |
| `--language` | no | `en-US` |

The slug becomes the book directory and output filename prefix. It must contain lowercase letters, digits, and single hyphens, such as `winter-road`. Scriber refuses to overwrite an existing book.

## `scriber list`

Lists every discovered book:

```bash
scriber list
```

Output contains the slug and full title separated by a tab.

## `scriber build`

Builds all books:

```bash
scriber build
```

Builds selected books:

```bash
scriber build winter-road second-novel
```

Draft mode creates all configured artifacts and reports retailer limits such as a short page count as warnings.

Strict release mode is also available:

```bash
scriber build --release
```

Each output line is JSON with:

| Key | Meaning |
| --- | --- |
| `book` | Book slug |
| `pages` | Stabilized even print page count |
| `mode` | `draft` or `release` |
| `output` | Workspace-relative build directory |
| `proof` | Author-readable HTML proof report |
| `metadata` | Copy-friendly retailer metadata sheet |
| `valid` | Whether errors are empty |
| `checks` | Completed validation stages |
| `errors` | Blocking problems |
| `warnings` | Non-blocking review items |

## `scriber release`

Builds and strictly validates all or selected books:

```bash
scriber release [slugs...]
```

This is the author-facing equivalent of `scriber build --release`. It enforces the verified trim and ink/paper page limits, promotes cover-resolution risks to errors, and requires EPUBCheck. Ace by DAISY runs when installed. Open the generated `proof_report.html` for the complete result.

## `scriber validate`

Validates existing outputs without rebuilding:

```bash
scriber validate [slugs...]
```

Retailer page limits are strict. Add `--release` to run external EPUB and accessibility validators:

```bash
scriber validate --release winter-road
```

Use `build` when source files changed. Use `validate` to recheck artifacts that have not changed.

## `scriber cover-template`

Builds one book and writes its final-size cover guide:

```bash
scriber cover-template winter-road
```

The command prints the workspace-relative PNG path. Run it again after changes to page count, trim, ink, or paper.

## `scriber doctor`

Reports release-tool availability as JSON:

```bash
scriber doctor
```

`release_ready` is true when Scriber can run EPUBCheck. Ace is optional. A missing EPUBCheck produces exit status 1.

## `scriber upgrade`

Previews schema changes for all or selected books:

```bash
scriber upgrade --dry-run [slugs...]
```

Applies them:

```bash
scriber upgrade [slugs...]
```

The command changes `book.toml` only. It does not rewrite manuscript files or cover artwork.

## Exit statuses

| Status | Meaning |
| --- | --- |
| `0` | Command completed and requested validations passed |
| `1` | A build or validation failed, or `doctor` found no EPUBCheck |
| `2` | Invalid input, missing files, unsupported configuration, or build-system error |
