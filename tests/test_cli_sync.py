from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from git_assistant.cli import maybe_handle_upstream_sync
from git_assistant.git.ops import UpstreamStatus


class UpstreamSyncTests(unittest.TestCase):
    def test_clean_worktree_can_pull_latest_changes(self) -> None:
        upstream = UpstreamStatus(
            has_upstream=True,
            ahead=0,
            behind=2,
            upstream_ref="origin/main",
        )

        with patch("git_assistant.cli.get_upstream_status", return_value=upstream):
            with patch("git_assistant.cli.prompt_sync_action", return_value="1"):
                with patch("git_assistant.cli.git_pull_ff_only") as mock_pull:
                    maybe_handle_upstream_sync(Path("."), clean_worktree=True)

        mock_pull.assert_called_once_with(Path("."))

    def test_dirty_worktree_skips_pull_for_safety(self) -> None:
        upstream = UpstreamStatus(
            has_upstream=True,
            ahead=0,
            behind=2,
            upstream_ref="origin/main",
        )

        with patch("git_assistant.cli.get_upstream_status", return_value=upstream):
            with patch("git_assistant.cli.prompt_sync_action", return_value="1"):
                with patch("git_assistant.cli.git_pull_ff_only") as mock_pull:
                    maybe_handle_upstream_sync(Path("."), clean_worktree=False)

        mock_pull.assert_not_called()


if __name__ == "__main__":
    unittest.main()
