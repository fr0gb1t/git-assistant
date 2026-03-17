from __future__ import annotations

import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from git_assistant.ai.base import AIConfig
from git_assistant.cli import main, maybe_handle_readme_update
from git_assistant.commit.service import CommitMessageResult
from git_assistant.readme.parser import ReadmeUpdateResult
from git_assistant.release.decision import ReleaseDecision
from git_assistant.release.evaluator import ReleaseSuggestion


class ReadmeDryRunTests(unittest.TestCase):
    def test_maybe_handle_readme_update_dry_run_does_not_write_readme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            readme_path = cwd / "README.md"
            readme_path.write_text("# Original\n", encoding="utf-8")

            result = ReadmeUpdateResult(
                should_update=True,
                reason="Recent user-facing changes",
                updated_sections=["Features"],
                updated_readme="# Updated\n",
            )

            with patch("git_assistant.cli.evaluate_readme_update", return_value=result):
                with patch("builtins.input", return_value="1"):
                    applied = maybe_handle_readme_update(cwd, AIConfig(), dry_run=True)

            self.assertTrue(applied)
            self.assertEqual(readme_path.read_text(encoding="utf-8"), "# Original\n")

    def test_main_dry_run_restores_state_before_exit(self) -> None:
        args = Namespace(
            provider=None,
            model=None,
            host=None,
            timeout=None,
            debug=False,
            dry_run=True,
            all_files=True,
        )
        result = CommitMessageResult(
            message="fix(cli): preview dry run cleanup",
            was_truncated=False,
            staged_included=False,
            unstaged_included=True,
            untracked_included=False,
        )
        heuristic = ReleaseSuggestion(
            should_release=False,
            release_type=None,
            next_version=None,
            reason="No release",
        )
        decision = ReleaseDecision(
            should_apply=False,
            release_type=None,
            next_version=None,
            reason="No release",
        )

        with patch("git_assistant.cli.parse_args", return_value=args):
            with patch("git_assistant.cli.is_git_repo", return_value=True):
                with patch("git_assistant.cli.get_repo_root", return_value=Path("/repo")):
                    with patch("git_assistant.cli.get_status_short", return_value=" M cli.py"):
                        with patch("git_assistant.cli.get_changed_files", return_value=["src/git_assistant/cli.py"]):
                            with patch("git_assistant.cli.build_ai_config", return_value=AIConfig()):
                                with patch("git_assistant.cli.generate_and_display_commit_message", return_value=result):
                                    with patch("git_assistant.cli.prompt_user_action", return_value="1"):
                                        with patch("git_assistant.cli.update_changelog"):
                                            with patch("git_assistant.cli.maybe_handle_readme_update", return_value=False):
                                                with patch(
                                                    "git_assistant.cli.evaluate_release_suggestions",
                                                    return_value=(heuristic, None, decision),
                                                ):
                                                    with patch("git_assistant.cli.restore_dry_run_state") as mock_restore:
                                                        with self.assertRaises(SystemExit):
                                                            main()

        mock_restore.assert_called_once()


if __name__ == "__main__":
    unittest.main()
