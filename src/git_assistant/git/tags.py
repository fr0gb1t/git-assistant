from __future__ import annotations

from pathlib import Path

from git_assistant.git.ops import GitError, run_git_command


def git_tag_exists(tag: str, cwd: Path | None = None) -> bool:
    """
    Return True if a Git tag already exists.
    """
    try:
        output = run_git_command(["tag", "--list", tag], cwd=cwd)
    except GitError:
        return False

    return tag in output.split()


def get_latest_git_tag(cwd: Path | None = None) -> str | None:
    """
    Return the latest reachable Git tag, or None if no tags exist.
    """
    try:
        output = run_git_command(["describe", "--tags", "--abbrev=0"], cwd=cwd)
    except GitError:
        return None

    tag = output.strip()
    return tag or None


def create_git_tag(tag: str, cwd: Path | None = None) -> None:
    """
    Create a lightweight Git tag.

    Raises:
        GitError if the tag already exists or creation fails.
    """
    if git_tag_exists(tag, cwd=cwd):
        raise GitError(f"Tag already exists: {tag}")

    run_git_command(["tag", tag], cwd=cwd)


def push_git_tag(tag: str, cwd: Path | None = None) -> None:
    """
    Push a Git tag to origin.
    """
    run_git_command(["push", "origin", tag], cwd=cwd)