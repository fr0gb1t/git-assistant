from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from git_assistant.ai.base import AIConfig
from git_assistant.commit.service import CommitMessageResult
from git_assistant.config.loader import AppConfig
from git_assistant.release.decision import ReleaseDecision
from git_assistant.release.evaluator import ReleaseSuggestion, StableReleaseHint
from git_assistant.cli import main


class PushFlowTests(unittest.TestCase):
    def test_main_offers_push_when_no_release_is_applied(self) -> None:
        args = Namespace(
            provider=None,
            model=None,
            host=None,
            timeout=None,
            debug=False,
            dry_run=False,
            all_files=True,
            release=None,
        )
        result = CommitMessageResult(
            message="fix(cli): add push prompt after commit",
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
        hint = StableReleaseHint(
            should_suggest=False,
            version=None,
            reason="",
        )

        with patch("git_assistant.cli.parse_args", return_value=args):
            with patch("git_assistant.cli.is_git_repo", return_value=True):
                with patch("git_assistant.cli.get_repo_root", return_value=Path("/repo")):
                    with patch("git_assistant.cli.get_status_short", return_value=" M cli.py"):
                        with patch("git_assistant.cli.get_changed_files", return_value=["src/git_assistant/cli.py"]):
                            with patch("git_assistant.cli.maybe_handle_upstream_sync"):
                                with patch("git_assistant.cli.build_app_config", return_value=AppConfig(ai=AIConfig())):
                                    with patch("git_assistant.cli.generate_and_display_commit_message", return_value=result):
                                        with patch("git_assistant.cli.prompt_user_action", return_value="1"):
                                            with patch("git_assistant.cli.update_changelog"):
                                                with patch("git_assistant.cli.maybe_handle_readme_update", return_value=False):
                                                    with patch(
                                                        "git_assistant.cli.evaluate_release_suggestions",
                                                        return_value=(heuristic, None, decision),
                                                    ):
                                                        with patch(
                                                            "git_assistant.cli.evaluate_first_stable_hint",
                                                            return_value=hint,
                                                        ):
                                                            with patch("git_assistant.cli.git_add_files"):
                                                                with patch("git_assistant.cli.git_commit", return_value="[main abc123] msg"):
                                                                    with patch("git_assistant.cli.prompt_push_after_commit", return_value="1"):
                                                                        with patch("git_assistant.cli.git_push") as mock_push:
                                                                            main()

        mock_push.assert_called_once_with(Path.cwd())


if __name__ == "__main__":
    unittest.main()
