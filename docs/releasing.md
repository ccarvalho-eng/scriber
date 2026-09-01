# Maintainer release process

Scriber publishes the `scriber-books` distribution and installs the `scriber` command.

1. Confirm the version in `pyproject.toml` and `src/scriber/__init__.py` matches the changelog.
2. Run formatting, lint, type checks, tests, coverage, package builds, an installed-command smoke test, and EPUBCheck on a generated sample.
3. Build the source distribution and wheel with `uv build` and inspect their metadata and contents.
4. Merge the focused release pull request into `main`.
5. Create a signed `vX.Y.Z` tag from the reviewed merge commit and publish the matching GitHub release notes.
6. Publish through PyPI Trusted Publishing after repository automation and the protected `pypi` environment are configured.
7. Verify the PyPI project page, install the released version in a clean environment, and complete a sample build.

GitHub CI and publishing automation are intentionally deferred to a focused follow-up. Do not create a release tag until those controls and the PyPI Trusted Publisher are configured. Never store a PyPI API token in the repository.
