from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_assistant.cli import (
    CHANGELOG_FILE,
    README_FILE,
    restore_dry_run_state,
    restore_managed_files,
    restore_workflow_state,
)
from git_assistant.git.ops import GitError


class RestoreManagedFilesTests(unittest.TestCase):
    def test_does_not_delete_tracked_file_when_checkout_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            readme_path = cwd / README_FILE
            readme_path.write_text("current content", encoding="utf-8")

            def fake_run_git_command(args: list[str], cwd: Path | None = None) -> str:
                if args[:2] == ["cat-file", "-e"]:
                    if args[2] == f"HEAD:{README_FILE}":
                        return ""
                    raise GitError("missing")

                if args == ["checkout", "--", README_FILE]:
                    raise GitError("checkout failed")

                raise AssertionError(f"Unexpected git command: {args}")

            with patch("git_assistant.cli.run_git_command", side_effect=fake_run_git_command):
                with self.assertRaises(GitError):
                    restore_managed_files(cwd)

            self.assertTrue(readme_path.exists())

    def test_deletes_generated_file_missing_from_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            changelog_path = cwd / CHANGELOG_FILE
            changelog_path.write_text("generated", encoding="utf-8")

            def fake_run_git_command(args: list[str], cwd: Path | None = None) -> str:
                if args[:2] == ["cat-file", "-e"]:
                    raise GitError("missing")
                raise AssertionError(f"Unexpected git command: {args}")

            with patch("git_assistant.cli.run_git_command", side_effect=fake_run_git_command):
                restore_managed_files(cwd)

            self.assertFalse(changelog_path.exists())

    def test_restore_workflow_state_clears_preview_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            preview_dir = cwd / ".git-assistant-preview"
            preview_dir.mkdir()
            (preview_dir / "README.preview.md").write_text("# Preview\n", encoding="utf-8")

            with patch("git_assistant.cli.restore_managed_files") as mock_restore:
                restore_workflow_state(cwd)

            mock_restore.assert_called_once_with(cwd)
            self.assertFalse(preview_dir.exists())

    def test_restore_dry_run_state_swallow_restore_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)

            with patch(
                "git_assistant.cli.restore_workflow_state",
                side_effect=GitError("checkout failed"),
            ):
                restore_dry_run_state(cwd)


if __name__ == "__main__":
    unittest.main()
