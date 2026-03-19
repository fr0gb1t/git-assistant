from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from git_assistant.cli import handle_repository_init, main, maybe_configure_remote_repository


class InitFlowTests(unittest.TestCase):
    def test_handle_repository_init_creates_git_repo_when_missing(self) -> None:
        with patch("git_assistant.cli.is_git_repo", return_value=False):
            with patch("git_assistant.cli.git_init") as mock_git_init:
                with patch("git_assistant.cli.maybe_configure_remote_repository") as mock_remote:
                    handle_repository_init(Path("/repo"))

        mock_git_init.assert_called_once_with(Path("/repo"))
        mock_remote.assert_called_once_with(Path("/repo"), non_interactive=False)

    def test_handle_repository_init_reuses_existing_git_repo(self) -> None:
        with patch("git_assistant.cli.is_git_repo", return_value=True):
            with patch("git_assistant.cli.get_repo_root", return_value=Path("/repo")):
                with patch("git_assistant.cli.git_init") as mock_git_init:
                    with patch("git_assistant.cli.maybe_configure_remote_repository") as mock_remote:
                        handle_repository_init(Path("/repo"), non_interactive=True)

        mock_git_init.assert_not_called()
        mock_remote.assert_called_once_with(Path("/repo"), non_interactive=True)

    def test_maybe_configure_remote_repository_skips_when_origin_exists(self) -> None:
        with patch("git_assistant.cli.has_remote_named", return_value=True):
            with patch("git_assistant.cli.prompt_remote_setup_action") as mock_prompt:
                maybe_configure_remote_repository(Path("/repo"))

        mock_prompt.assert_not_called()

    def test_maybe_configure_remote_repository_creates_github_remote(self) -> None:
        with patch("git_assistant.cli.has_remote_named", return_value=False):
            with patch("git_assistant.cli.prompt_remote_setup_action", return_value="1"):
                with patch("git_assistant.cli.prompt_remote_provider_choice", return_value="1"):
                    with patch("git_assistant.cli.prompt_github_owner", return_value="frogbit"):
                        with patch("git_assistant.cli.prompt_remote_visibility", return_value="1"):
                            with patch("git_assistant.cli.prompt_remote_protocol", return_value="1"):
                                with patch("git_assistant.cli._get_github_token", return_value="secret"):
                                    with patch("git_assistant.cli.create_remote_repository", return_value="git@github.com:frogbit/repo.git") as mock_create:
                                        maybe_configure_remote_repository(Path("/repo"))

        request = mock_create.call_args.args[2]
        self.assertEqual(mock_create.call_args.args[:2], ("github", Path("/repo")))
        self.assertEqual(request.owner, "frogbit")
        self.assertEqual(request.name, "repo")
        self.assertEqual(request.visibility, "private")
        self.assertEqual(request.remote_protocol, "ssh")
        self.assertEqual(mock_create.call_args.kwargs["token"], "secret")

    def test_maybe_configure_remote_repository_can_add_existing_remote_url(self) -> None:
        with patch("git_assistant.cli.has_remote_named", return_value=False):
            with patch("git_assistant.cli.prompt_remote_setup_action", return_value="2"):
                with patch(
                    "git_assistant.cli.prompt_existing_remote_url",
                    return_value="git@github.com:frogbit/repo.git",
                ):
                    with patch("git_assistant.cli.run_git_command") as mock_git:
                        maybe_configure_remote_repository(Path("/repo"))

        mock_git.assert_called_once_with(
            ["remote", "add", "origin", "git@github.com:frogbit/repo.git"],
            cwd=Path("/repo"),
        )

    def test_main_init_mode_exits_after_setup(self) -> None:
        args = Namespace(
            provider=None,
            model=None,
            host=None,
            timeout=None,
            debug=False,
            dry_run=False,
            all_files=False,
            release=None,
            non_interactive=False,
            init=True,
        )

        with patch("git_assistant.cli.parse_args", return_value=args):
            with patch("git_assistant.cli.handle_repository_init") as mock_init:
                with self.assertRaises(SystemExit) as ctx:
                    main()

        self.assertEqual(ctx.exception.code, 0)
        mock_init.assert_called_once_with(Path.cwd(), non_interactive=False)


if __name__ == "__main__":
    unittest.main()
