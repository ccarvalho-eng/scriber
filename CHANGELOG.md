# Changelog

All notable changes are documented here. Scriber follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Author-readable HTML proof reports and copy-friendly retailer metadata sheets.
- Versioned source attribution for publishing rules in dimensions and manifests.
- Least-privilege, SHA-pinned GitHub CI across the oldest and newest supported Python versions.

### Changed

- KDP paperback page limits now follow the selected ink and paper combination.
- Release validation now blocks unverified trim sizes and checks minimum text size, opening metadata, blank-page runs, and cover file size.
- New book configurations rely on the retailer profile instead of exposing a redundant maximum-page setting.

## [0.2.0] - 2026-08-31

### Added

- Convention-based front matter, chapter, and back matter discovery.
- Organized PDF, EPUB, and cover outputs under each book's `dist/`.
- Automatic cover activation, page-count-aware cover templates, and source preflight.
- Strict release builds with EPUBCheck and optional Ace accessibility validation.
- Versioned configuration, migration command, publication metadata, and ISBN checks.
- Configurable embedded typography, language-aware hyphenation, and recto chapter starts.
- Reproducible EPUB archives, stable PDF generation, and checksum manifests.
- Public documentation, packaging metadata, security policy, and release foundations.

## [0.1.0] - 2026-08-31

### Added

- Multi-book Markdown scaffolding.
- Iterative KDP paperback layout and page-count-dependent cover compilation.
- Reflowable EPUB 3 output and internal publication validation.

[Unreleased]: https://github.com/ccarvalho-eng/scriber/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ccarvalho-eng/scriber/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ccarvalho-eng/scriber/releases/tag/v0.1.0
