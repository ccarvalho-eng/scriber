"""Scriber command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scriber.build import build_book
from scriber.config import discover_books
from scriber.scaffold import create_book, initialize_workspace
from scriber.validate import validate_book


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    workspace = Path(arguments.workspace).resolve()
    try:
        if arguments.command == "init":
            created = initialize_workspace(workspace)
            _print_created(created, workspace)
            return 0
        if arguments.command == "new":
            created = create_book(
                workspace=workspace,
                slug=arguments.slug,
                title=arguments.title,
                subtitle=arguments.subtitle,
                author=arguments.author,
                language=arguments.language,
            )
            _print_created(created, workspace)
            return 0
        if arguments.command == "list":
            books = discover_books(workspace)
            for config in books:
                print(f"{config.slug}\t{config.book.full_title}")
            return 0
        if arguments.command == "build":
            books = discover_books(workspace, arguments.slugs or None)
            failed = False
            for config in books:
                result = build_book(config)
                print(
                    json.dumps(
                        {
                            "book": result.slug,
                            "pages": result.pdf.page_count,
                            "output": str(result.output_dir),
                            "valid": result.validation.valid,
                            "warnings": result.validation.warnings,
                        }
                    )
                )
                failed = failed or not result.validation.valid
            return 1 if failed else 0
        if arguments.command == "validate":
            books = discover_books(workspace, arguments.slugs or None)
            failed = False
            for config in books:
                result = validate_book(config, strict_retailer=True)
                print(
                    json.dumps(
                        {
                            "book": config.slug,
                            "valid": result.valid,
                            "errors": result.errors,
                            "warnings": result.warnings,
                        }
                    )
                )
                failed = failed or not result.valid
            return 1 if failed else 0
    except (
        FileExistsError,
        FileNotFoundError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    parser.error("a command is required")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scriber",
        description="Compile one or more Markdown books into PDF and EPUB formats.",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Scriber workspace containing scriber.toml and books/",
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("init", help="Create an empty Scriber workspace")

    new = commands.add_parser("new", help="Generate a complete book skeleton")
    new.add_argument("slug")
    new.add_argument("--title", required=True)
    new.add_argument("--subtitle", default="")
    new.add_argument("--author", required=True)
    new.add_argument("--language", default="en-US")

    commands.add_parser("list", help="List books in the workspace")
    build = commands.add_parser("build", help="Build selected books or all books")
    build.add_argument("slugs", nargs="*")
    validate = commands.add_parser(
        "validate", help="Validate selected books or all books"
    )
    validate.add_argument("slugs", nargs="*")
    return parser


def _print_created(paths: list[Path], workspace: Path) -> None:
    if not paths:
        print(f"Workspace already initialized: {workspace}")
        return
    for path in paths:
        print(path.relative_to(workspace))
