from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests

from git_assistant.git.ops import GitError, run_git_command


class HostingProviderError(RuntimeError):
    """Raised when a hosting provider operation fails."""


@dataclass(frozen=True, slots=True)
class RemoteRepositoryRequest:
    owner: str
    name: str
    visibility: str = "private"
    remote_protocol: str = "https"


@dataclass(frozen=True, slots=True)
class RemoteHostingProvider:
    key: str
    label: str


def list_remote_providers() -> list[RemoteHostingProvider]:
    return [
        RemoteHostingProvider(
            key="github",
            label="GitHub",
        )
    ]


def get_remote_provider(key: str) -> RemoteHostingProvider:
    for provider in list_remote_providers():
        if provider.key == key:
            return provider
    raise HostingProviderError(f"Unsupported remote hosting provider: {key}")


def create_remote_repository(
    provider_key: str,
    cwd: Path,
    request: RemoteRepositoryRequest,
    *,
    token: str,
) -> str:
    provider = get_remote_provider(provider_key)

    if provider.key == "github":
        return _create_github_repository(cwd, request, token=token)

    raise HostingProviderError(f"Unsupported remote hosting provider: {provider.key}")


def _create_github_repository(
    cwd: Path,
    request: RemoteRepositoryRequest,
    *,
    token: str,
) -> str:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    owner_response = requests.get(
        f"https://api.github.com/users/{request.owner}",
        headers=headers,
        timeout=30,
    )
    if owner_response.status_code != 200:
        raise HostingProviderError(_build_github_error(owner_response))

    owner_payload = owner_response.json()
    owner_type = owner_payload.get("type")

    if owner_type == "Organization":
        create_url = f"https://api.github.com/orgs/{request.owner}/repos"
    else:
        create_url = "https://api.github.com/user/repos"

    payload = {
        "name": request.name,
        "private": request.visibility == "private",
    }
    create_response = requests.post(
        create_url,
        headers=headers,
        json=payload,
        timeout=30,
    )
    if create_response.status_code not in {200, 201}:
        raise HostingProviderError(_build_github_error(create_response))

    payload = create_response.json()
    remote_url = _select_remote_url(payload, request.remote_protocol)

    try:
        run_git_command(["remote", "add", "origin", remote_url], cwd=cwd)
    except GitError as exc:
        raise HostingProviderError(f"Remote repository created but origin could not be added: {exc}") from exc

    return remote_url


def _select_remote_url(payload: dict, protocol: str) -> str:
    if protocol == "ssh":
        remote_url = payload.get("ssh_url")
        if not remote_url:
            raise HostingProviderError("GitHub API response did not include ssh_url.")
        return remote_url

    remote_url = payload.get("clone_url")
    if not remote_url:
        raise HostingProviderError("GitHub API response did not include clone_url.")
    return remote_url


def _build_github_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    message = payload.get("message")
    if message:
        return f"GitHub API error ({response.status_code}): {message}"

    text = response.text.strip()
    if text:
        return f"GitHub API error ({response.status_code}): {text}"

    return f"GitHub API error ({response.status_code})"
