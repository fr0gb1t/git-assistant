from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_assistant.git.ops import get_changed_files, get_untracked_files, get_upstream_status


class GitOpsStatusParsingTests(unittest.TestCase):
    def test_get_untracked_files_preserves_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            self._git(repo, "init")

            target = repo / "file with spaces.txt"
            target.write_text("hello", encoding="utf-8")

            self.assertEqual(get_untracked_files(repo), ["file with spaces.txt"])
            self.assertIn("file with spaces.txt", get_changed_files(repo))

    def test_get_changed_files_returns_new_name_for_renames_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            self._git(repo, "init")
            self._git(repo, "config", "user.name", "Test User")
            self._git(repo, "config", "user.email", "test@example.com")

            original = repo / "old name.txt"
            original.write_text("hello", encoding="utf-8")
            self._git(repo, "add", "old name.txt")
            self._git(repo, "commit", "-m", "feat: add fixture")

            renamed = repo / "new name.txt"
            original.rename(renamed)
            self._git(repo, "add", "-A")

            self.assertIn("new name.txt", get_changed_files(repo))

    def test_get_upstream_status_parses_ahead_and_behind_counts(self) -> None:
        def fake_run_git_command(args: list[str], cwd: Path | None = None) -> str:
            if args == ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]:
                return "origin/main"
            if args == ["rev-list", "--left-right", "--count", "origin/main...HEAD"]:
                return "2 1"
            raise AssertionError(f"Unexpected git command: {args}")

        with patch("git_assistant.git.ops.run_git_command", side_effect=fake_run_git_command):
            status = get_upstream_status(Path("."))

        self.assertTrue(status.has_upstream)
        self.assertEqual(status.behind, 2)
        self.assertEqual(status.ahead, 1)
        self.assertEqual(status.upstream_ref, "origin/main")

    def _git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout


if __name__ == "__main__":
    unittest.main()
