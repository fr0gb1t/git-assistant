from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from git_assistant.cli import main


class ManualReleaseCliTests(unittest.TestCase):
    def test_main_applies_manual_release_with_prefixed_version(self) -> None:
        args = Namespace(
            provider=None,
            model=None,
            host=None,
            timeout=None,
            debug=False,
            dry_run=False,
            all_files=False,
            release="v0.7.2",
        )

        with patch("git_assistant.cli.parse_args", return_value=args):
            with patch("git_assistant.cli.is_git_repo", return_value=True):
                with patch("git_assistant.cli.get_repo_root", return_value=Path("/repo")):
                    with patch("git_assistant.cli.apply_release") as mock_apply_release:
                        with self.assertRaises(SystemExit) as exit_ctx:
                            main()

        self.assertEqual(exit_ctx.exception.code, 0)
        mock_apply_release.assert_called_once_with(Path.cwd(), "0.7.2")

    def test_main_rejects_invalid_manual_release_version(self) -> None:
        args = Namespace(
            provider=None,
            model=None,
            host=None,
            timeout=None,
            debug=False,
            dry_run=False,
            all_files=False,
            release="release-0.7.2",
        )

        with patch("git_assistant.cli.parse_args", return_value=args):
            with patch("git_assistant.cli.is_git_repo", return_value=True):
                with self.assertRaises(SystemExit) as exit_ctx:
                    main()

        self.assertEqual(exit_ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
