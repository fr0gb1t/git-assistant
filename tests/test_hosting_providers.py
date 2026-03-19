from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from git_assistant.hosting.providers import (
    HostingProviderError,
    RemoteRepositoryRequest,
    create_remote_repository,
)


class HostingProvidersTests(unittest.TestCase):
    def test_create_github_repository_for_user_adds_origin(self) -> None:
        owner_response = Mock(status_code=200)
        owner_response.json.return_value = {"type": "User"}

        create_response = Mock(status_code=201)
        create_response.json.return_value = {
            "clone_url": "https://github.com/frogbit/sample.git"
        }

        with patch("git_assistant.hosting.providers.requests.get", return_value=owner_response):
            with patch("git_assistant.hosting.providers.requests.post", return_value=create_response) as mock_post:
                with patch("git_assistant.hosting.providers.run_git_command") as mock_git:
                    remote_url = create_remote_repository(
                        "github",
                        Path("/repo"),
                        RemoteRepositoryRequest(
                            owner="frogbit",
                            name="sample",
                            visibility="private",
                        ),
                        token="secret",
                    )

        self.assertEqual(remote_url, "https://github.com/frogbit/sample.git")
        mock_post.assert_called_once()
        self.assertEqual(
            mock_post.call_args.kwargs["json"],
            {"name": "sample", "private": True},
        )
        mock_git.assert_called_once_with(
            ["remote", "add", "origin", "https://github.com/frogbit/sample.git"],
            cwd=Path("/repo"),
        )

    def test_create_github_repository_for_org_uses_org_endpoint(self) -> None:
        owner_response = Mock(status_code=200)
        owner_response.json.return_value = {"type": "Organization"}

        create_response = Mock(status_code=201)
        create_response.json.return_value = {
            "clone_url": "https://github.com/acme/sample.git"
        }

        with patch("git_assistant.hosting.providers.requests.get", return_value=owner_response):
            with patch("git_assistant.hosting.providers.requests.post", return_value=create_response) as mock_post:
                with patch("git_assistant.hosting.providers.run_git_command"):
                    create_remote_repository(
                        "github",
                        Path("/repo"),
                        RemoteRepositoryRequest(
                            owner="acme",
                            name="sample",
                            visibility="public",
                        ),
                        token="secret",
                    )

        self.assertEqual(
            mock_post.call_args.args[0],
            "https://api.github.com/orgs/acme/repos",
        )
        self.assertEqual(
            mock_post.call_args.kwargs["json"],
            {"name": "sample", "private": False},
        )

    def test_create_github_repository_raises_on_api_error(self) -> None:
        owner_response = Mock(status_code=404, text="not found")
        owner_response.json.return_value = {"message": "Not Found"}

        with patch("git_assistant.hosting.providers.requests.get", return_value=owner_response):
            with self.assertRaises(HostingProviderError):
                create_remote_repository(
                    "github",
                    Path("/repo"),
                    RemoteRepositoryRequest(owner="missing", name="sample"),
                    token="secret",
                )


if __name__ == "__main__":
    unittest.main()
