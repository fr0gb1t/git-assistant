from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    """Raised when a git command fails."""


def run_git_command(args: list[str], cwd: Path | None = None) -> str:
    """
    Run a git command and return stdout as text.

    Args:
        args: Git arguments, without the leading 'git'.
        cwd: Directory where the command should run. Defaults to current working directory.

    Raises:
        GitError: If the git command exits with a non-zero status.
    """
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown git error"
        raise GitError(stderr)

    return result.stdout.rstrip("\n")


def is_git_repo(cwd: Path | None = None) -> bool:
    """
    Return True if cwd is inside a git working tree.
    """
    try:
        output = run_git_command(["rev-parse", "--is-inside-work-tree"], cwd=cwd)
        return output == "true"
    except GitError:
        return False


def get_repo_root(cwd: Path | None = None) -> Path:
    """
    Return the root path of the current git repository.

    Raises:
        GitError: If cwd is not inside a git repository.
    """
    output = run_git_command(["rev-parse", "--show-toplevel"], cwd=cwd)
    return Path(output)


def get_status_short(cwd: Path | None = None) -> str:
    """
    Return the raw output of `git status --porcelain`.
    """
    return run_git_command(["status", "--porcelain"], cwd=cwd)


def get_changed_files(cwd: Path | None = None) -> list[str]:
    """
    Return changed file paths parsed from `git status --porcelain`.
    """
    status = get_status_short(cwd=cwd)

    if not status:
        return []

    files: list[str] = []

    for raw_line in status.splitlines():
        line = raw_line.rstrip()

        if not line:
            continue

        if len(line) < 4:
            continue

        path_part = line[3:]

        if " -> " in path_part:
            _, new_path = path_part.split(" -> ", 1)
            files.append(new_path.strip())
        else:
            files.append(path_part.strip())

    return files

def get_unstaged_diff(cwd=None) -> str:
    """
    Return current git diff (unstaged changes).
    """
    return run_git_command(["diff"], cwd=cwd)

def git_add_all(cwd: Path | None = None) -> None:
    """
    Stage all changes in the current repository.
    """
    run_git_command(["add", "."], cwd=cwd)


def git_commit(message: str, cwd: Path | None = None) -> str:
    """
    Create a git commit with the provided message.
    """
    return run_git_command(["commit", "-m", message], cwd=cwd)
