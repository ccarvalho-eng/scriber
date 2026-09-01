# Migration guide

## Configuration versions

Scriber 0.2 writes `schema_version = 2`. It continues to read version 1 configurations so an existing library can build before migration.

Preview:

```bash
scriber upgrade --dry-run
```

Apply:

```bash
scriber upgrade
```

Commit or back up configuration files before a workspace-wide upgrade.

## Version 1 content paths

Version 1 books commonly define explicit patterns:

```toml
[contents]
front = ["front/*.md"]
body = ["manuscript/*.md"]
back = ["back/*.md"]
```

Those patterns continue to work. The upgrade command does not move files.

New books use convention discovery:

```text
manuscript/front_matter/
manuscript/chapters/
manuscript/back_matter/
```

To adopt the new tree, move files deliberately and then remove the old `[contents]` table. Check the order with `scriber build <slug>`.

## Output changes

Version 2 organizes outputs beneath `dist/pdf`, `dist/epub`, and `dist/cover` and uses slug-based filenames. Update archival or upload scripts that referenced flat version 1 names.

The version 2 manifest is named `publication_manifest.json` and records relative artifact paths.

## Cover activation

New configurations use `enabled = "auto"`. Existing `true` and `false` values remain valid. Change to `"auto"` if cover compilation should follow the presence of both panel files.

## Verification after migration

1. Run `scriber list`.
2. Build one migrated book.
3. Compare section order, page count, trim, and contents.
4. Generate a new cover template.
5. Rebuild cover artwork if geometry changed.
6. Run strict release validation before submitting a migrated edition.
