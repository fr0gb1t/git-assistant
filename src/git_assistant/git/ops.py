from __future__ import annotations

from dataclasses import dataclass
import subprocess
from pathlib import Path


class GitError(RuntimeError):
    """Raised when a git command fails."""


@dataclass(slots=True)
class UpstreamStatus:
    has_upstream: bool
    ahead: int
    behind: int
    upstream_ref: str | None = None


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


def get_upstream_status(cwd: Path | None = None) -> UpstreamStatus:
    """
    Return ahead/behind information against the current branch upstream.
    """
    try:
        upstream_ref = run_git_command(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=cwd,
        )
    except GitError:
        return UpstreamStatus(has_upstream=False, ahead=0, behind=0, upstream_ref=None)

    counts = run_git_command(
        ["rev-list", "--left-right", "--count", f"{upstream_ref}...HEAD"],
        cwd=cwd,
    )
    parts = counts.split()
    if len(parts) != 2:
        raise GitError(f"Unexpected upstream status output: {counts}")

    behind, ahead = (int(part) for part in parts)
    return UpstreamStatus(
        has_upstream=True,
        ahead=ahead,
        behind=behind,
        upstream_ref=upstream_ref,
    )


def get_status_short(cwd: Path | None = None) -> str:
    """
    Return the raw output of `git status --porcelain --untracked-files=all`.
    """
    return run_git_command(["status", "--porcelain", "--untracked-files=all"], cwd=cwd)


def get_status_entries(cwd: Path | None = None) -> list[tuple[str, str]]:
    """
    Return parsed `(status_code, path)` entries from `git status --porcelain -z`.

    The `-z` format avoids shell-style quoting, so paths with spaces or other
    special characters are returned exactly as Git stores them.
    """
    output = run_git_command(
        ["status", "--porcelain", "-z", "--untracked-files=all"],
        cwd=cwd,
    )
    if not output:
        return []

    parts = output.split("\0")
    entries: list[tuple[str, str]] = []
    index = 0

    while index < len(parts):
        entry = parts[index]
        if not entry:
            index += 1
            continue

        status_code = entry[:2]
        path = entry[3:]

        # In porcelain -z mode, renames/copies use an extra NUL-terminated
        # path entry. The first path is the current path we want to expose;
        # the second one is the source path and should be skipped.
        if status_code[0] in {"R", "C"} and index + 1 < len(parts):
            index += 1

        entries.append((status_code, path))
        index += 1

    return entries


def get_changed_files(cwd: Path | None = None) -> list[str]:
    """
    Return changed file paths parsed from `git status --porcelain`.
    """
    return [path for _, path in get_status_entries(cwd=cwd)]

def git_add_all(cwd: Path | None = None) -> None:
    """
    Stage all changes in the current repository.
    """
    run_git_command(["add", "."], cwd=cwd)

def get_ignored_files(file_paths: list[str], cwd: Path | None = None) -> set[str]:
    """
    Return the subset of file_paths that are ignored by .gitignore.
    Uses `git check-ignore` — returns empty set if none are ignored.
    """
    if not file_paths:
        return set()

    try:
        output = run_git_command(
            ["check-ignore", "--", *file_paths],
            cwd=cwd,
        )
        return set(output.splitlines())
    except GitError:
        # git check-ignore exits with code 1 when no files are ignored — not a real error
        return set()


def git_add_files(file_paths: list[str], cwd: Path | None = None) -> None:
    """
    Stage only the provided files, silently skipping any that are gitignored.
    """
    if not file_paths:
        raise GitError("No files were provided to git_add_files().")

    ignored = get_ignored_files(file_paths, cwd=cwd)
    stageable = [f for f in file_paths if f not in ignored]

    if not stageable:
        raise GitError("All provided files are ignored by .gitignore — nothing to stage.")

    run_git_command(["add", "--", *stageable], cwd=cwd)


def git_commit(message: str, cwd: Path | None = None) -> str:
    """
    Create a git commit with the provided message.
    """
    return run_git_command(["commit", "-m", message], cwd=cwd)

def get_unstaged_diff(
    cwd: Path | None = None,
    file_paths: list[str] | None = None,
) -> str:
    """
    Return unstaged diff, optionally limited to specific file paths.
    """
    args = ["diff"]

    if file_paths:
        args.extend(["--", *file_paths])

    return run_git_command(args, cwd=cwd)


def get_staged_diff(
    cwd: Path | None = None,
    file_paths: list[str] | None = None,
) -> str:
    """
    Return staged diff, optionally limited to specific file paths.
    """
    args = ["diff", "--cached"]

    if file_paths:
        args.extend(["--", *file_paths])

    return run_git_command(args, cwd=cwd)


def get_combined_diff(cwd: Path | None = None) -> str:
    """
    Return a combined diff including staged and unstaged changes.
    """

    unstaged = get_unstaged_diff(cwd)
    staged = get_staged_diff(cwd)

    parts: list[str] = []

    if staged.strip():
        parts.append("STAGED CHANGES:\n" + staged)

    if unstaged.strip():
        parts.append("UNSTAGED CHANGES:\n" + unstaged)

    return "\n\n".join(parts)

def get_untracked_files(cwd: Path | None = None) -> list[str]:
    """
    Return untracked files from `git status --porcelain`.
    """
    return [
        path
        for status_code, path in get_status_entries(cwd=cwd)
        if status_code == "??"
    ]


def read_file_contents(
    file_path: str,
    cwd: Path | None = None,
    max_chars: int = 4000,
) -> str:
    """
    Read a text file from disk and return truncated content.

    Raises:
        GitError: If the file cannot be read as text.
    """
    base_dir = cwd or Path.cwd()
    abs_path = base_dir / file_path

    try:
        content = abs_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise GitError(f"File is not valid UTF-8 text: {file_path}") from exc
    except OSError as exc:
        raise GitError(f"Could not read file: {file_path}") from exc

    if len(content) > max_chars:
        omitted = len(content) - max_chars
        content = (
            content[:max_chars].rstrip()
            + f"\n\n[TRUNCATED: omitted {omitted} characters from untracked file]\n"
        )

    return content
    
def is_text_file(file_path: str, cwd: Path | None = None) -> bool:
    """
    Return True if the file can be read as UTF-8 text.
    """
    base_dir = cwd or Path.cwd()
    abs_path = base_dir / file_path

    try:
        abs_path.read_text(encoding="utf-8")
        return True
    except (UnicodeDecodeError, OSError):
        return False

def git_push(cwd: Path) -> None:
    run_git_command(["push", "origin", "HEAD"], cwd)


def git_push_tag(cwd: Path, tag: str) -> None:
    run_git_command(["push", "origin", tag], cwd)


def git_pull_ff_only(cwd: Path) -> None:
    run_git_command(["pull", "--ff-only"], cwd)
