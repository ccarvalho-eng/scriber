# Getting started

## 1. Install Scriber

Install Python 3.11 or newer, then install Scriber:

```bash
uv tool install git+https://github.com/ccarvalho-eng/scriber.git
```

Run `scriber --help` to confirm the command is available.

## 2. Create a library and book

```bash
mkdir my-library
cd my-library
scriber new first-novel --title "First Novel" --author "Author Name"
```

The command creates the workspace marker, configuration, manuscript folders, and starter matter. It is safe to keep several books in the same workspace.

## 3. Write

Edit Markdown files under:

- `manuscript/front_matter/`
- `manuscript/chapters/`
- `manuscript/back_matter/`

Files are read in lexical filename order. Prefix them with numbers to make the order explicit. Every content file requires one `# Title` heading.

## 4. Build drafts

```bash
scriber build
```

Open the interior PDF and EPUB under the book's `dist/`. Short drafts build successfully but produce a retailer page-count warning.

## 5. Add cover artwork

Run `scriber cover-template first-novel`, design against the generated guide, then save the front and back panels as:

```text
assets/cover/front.png
assets/cover/back.png
```

The next build detects them automatically.

## 6. Validate the release

Install EPUBCheck, run `scriber doctor`, then:

```bash
scriber release first-novel
```

Resolve every error. Review warnings, the print PDF, cover preview, EPUB, manifest, and retailer preview before submission.
