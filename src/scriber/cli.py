"""Scriber command-line interface."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from scriber import __version__
from scriber.build import build_book
from scriber.config import CURRENT_SCHEMA_VERSION, discover_books
from scriber.scaffold import create_book, initialize_workspace
from scriber.validate import available_release_tools, validate_book


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
        if arguments.command in {"build", "release"}:
            books = discover_books(workspace, arguments.slugs or None)
            failed = False
            for config in books:
                release = arguments.command == "release" or arguments.release
                result = build_book(config, release=release)
                print(
                    json.dumps(
                        {
                            "book": result.slug,
                            "pages": result.pdf.page_count,
                            "mode": "release" if release else "draft",
                            "output": _display_path(result.output_dir, workspace),
                            "proof": _display_path(result.proof_report, workspace),
                            "metadata": _display_path(
                                result.metadata_sheet,
                                workspace,
                            ),
                            "valid": result.validation.valid,
                            "checks": result.validation.checks,
                            "errors": result.validation.errors,
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
                result = validate_book(
                    config,
                    strict_retailer=True,
                    release=arguments.release,
                )
                print(
                    json.dumps(
                        {
                            "book": config.slug,
                            "valid": result.valid,
                            "checks": result.checks,
                            "errors": result.errors,
                            "warnings": result.warnings,
                        }
                    )
                )
                failed = failed or not result.valid
            return 1 if failed else 0
        if arguments.command == "cover-template":
            books = discover_books(workspace, [arguments.slug])
            result = build_book(books[0])
            print(_display_path(result.cover_template, workspace))
            return 0
        if arguments.command == "doctor":
            tools = available_release_tools()
            values = {
                "scriber": __version__,
                "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "schema_version": CURRENT_SCHEMA_VERSION,
                "epubcheck": tools["epubcheck"] or "missing",
                "ace": tools["ace"] or "optional/missing",
                "release_ready": tools["epubcheck"] is not None,
            }
            print(json.dumps(values))
            return 0 if tools["epubcheck"] else 1
        if arguments.command == "upgrade":
            books = discover_books(workspace, arguments.slugs or None)
            for config in books:
                changed = _upgrade_config(config.source, arguments.dry_run)
                action = "would upgrade" if arguments.dry_run else "upgraded"
                status = action if changed else "current"
                print(f"{config.slug}\t{status}")
            return 0
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
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
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
    build.add_argument(
        "--release",
        action="store_true",
        help="enforce retailer limits and run external release validators",
    )
    release = commands.add_parser(
        "release",
        help="Build and strictly validate selected books or all books",
    )
    release.add_argument("slugs", nargs="*")
    release.set_defaults(release=True)
    validate = commands.add_parser(
        "validate", help="Validate selected books or all books"
    )
    validate.add_argument("slugs", nargs="*")
    validate.add_argument(
        "--release",
        action="store_true",
        help="run EPUBCheck and optional Ace accessibility audit",
    )
    cover_template = commands.add_parser(
        "cover-template",
        help="Build a book and generate its final-size cover guide",
    )
    cover_template.add_argument("slug")
    commands.add_parser("doctor", help="Check release-validator availability")
    upgrade = commands.add_parser(
        "upgrade",
        help="Upgrade book configurations to the current schema",
    )
    upgrade.add_argument("slugs", nargs="*")
    upgrade.add_argument("--dry-run", action="store_true")
    return parser


def _print_created(paths: list[Path], workspace: Path) -> None:
    if not paths:
        print(f"Workspace already initialized: {workspace}")
        return
    for path in paths:
        print(path.relative_to(workspace))


def _upgrade_config(path: Path, dry_run: bool) -> bool:
    content = path.read_text(encoding="utf-8")
    schema = re.compile(r"(?m)^schema_version\s*=\s*(\d+)\s*$")
    match = schema.search(content)
    if match and int(match.group(1)) == CURRENT_SCHEMA_VERSION:
        return False
    if not dry_run:
        if match:
            updated = schema.sub(
                f"schema_version = {CURRENT_SCHEMA_VERSION}",
                content,
                count=1,
            )
        else:
            updated = f"schema_version = {CURRENT_SCHEMA_VERSION}\n\n{content}"
        path.write_text(updated, encoding="utf-8")
    return True


def _display_path(path: Path, workspace: Path) -> str:
    try:
        return path.relative_to(workspace).as_posix()
    except ValueError:
        return path.name
