# Maintainer release process

Scriber publishes the `scriber-books` distribution and installs the `scriber` command.

1. Confirm the version in `pyproject.toml` and `src/scriber/__init__.py` matches the changelog.
2. Confirm GitHub CI passes formatting, lint, type checks, tests, coverage, and package builds on every supported boundary version.
3. Complete an installed-command smoke test and run EPUBCheck on a generated sample.
4. Build the source distribution and wheel with `uv build` and inspect their metadata and contents.
5. Merge the focused release pull request into `main`.
6. Create a signed `vX.Y.Z` tag from the reviewed merge commit and publish the matching GitHub release notes.
7. Publish through PyPI Trusted Publishing after the protected `pypi` environment is configured.
8. Verify the PyPI project page, install the released version in a clean environment, and complete a sample build.

Package publishing automation remains intentionally deferred to a focused follow-up. Do not create a release tag until PyPI Trusted Publishing and the protected environment are configured. Never store a PyPI API token in the repository.
