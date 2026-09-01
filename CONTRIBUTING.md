# Contributing

Contributions that improve reliable book production are welcome.

## Development setup

1. Fork and clone the repository.
2. Create a short-lived branch from `main`.
3. Install the locked development environment with `uv sync --all-groups`.
4. Add tests for behavioral changes.
5. Run `uv run ruff check .`, `uv run pyright`, and `uv run coverage run -m unittest discover -s tests`.
6. Open a focused pull request describing the user-visible result and compatibility impact.

Use Conventional Commit subjects. Keep generated publication files out of commits. Changes to retailer profiles must cite current primary retailer documentation and include boundary tests.

By contributing, you agree that your contribution is licensed under Apache-2.0.
