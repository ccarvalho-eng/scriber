from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scriber.cli import main
from scriber.scaffold import create_book


class CliTest(unittest.TestCase):
    def test_version_is_available_without_a_workspace(self) -> None:
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("scriber 0.2.0", output.getvalue())

    def test_upgrade_supports_dry_run_and_apply(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            create_book(
                workspace=workspace,
                slug="old-book",
                title="Old Book",
                author="Author Name",
            )
            source = workspace / "books/old-book/book.toml"
            content = source.read_text(encoding="utf-8")
            source.write_text(
                content.replace("schema_version = 2\n\n", ""),
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(
                        [
                            "--workspace",
                            raw,
                            "upgrade",
                            "--dry-run",
                        ]
                    ),
                    0,
                )
            self.assertFalse(
                source.read_text(encoding="utf-8").startswith("schema_version")
            )

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    main(["--workspace", raw, "upgrade"]),
                    0,
                )
            self.assertTrue(
                source.read_text(encoding="utf-8").startswith("schema_version = 2")
            )

    def test_doctor_reports_release_tool_state(self) -> None:
        output = StringIO()
        with (
            patch(
                "scriber.cli.available_release_tools",
                return_value={"epubcheck": "/bin/epubcheck", "ace": None},
            ),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["doctor"]), 0)
        values = json.loads(output.getvalue())
        self.assertTrue(values["release_ready"])
        self.assertEqual(values["schema_version"], 2)


if __name__ == "__main__":
    unittest.main()
