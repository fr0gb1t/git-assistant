from __future__ import annotations

from pathlib import Path

from git_assistant.ai.ollama import generate
from git_assistant.commit.diff_context import DiffContextBuilder
from git_assistant.commit.message import (
    SYSTEM_PROMPT,
    build_prompt,
    clean_message,
)
from git_assistant.git.ops import GitError, get_changed_files


class CommitMessageGenerationError(RuntimeError):
    """Raised when the commit message could not be generated."""


def generate_commit_message(
    cwd: Path,
    model: str = "qwen2.5:14b",
    host: str = "http://127.0.0.1:11434",
) -> str:
    """
    Generate a commit message for the current repository state.
    """
    try:
        changed_files = get_changed_files(cwd)
        diff_context = DiffContextBuilder().build(cwd)
    except GitError as exc:
        raise CommitMessageGenerationError(f"Git error: {exc}") from exc

    if not changed_files:
        raise CommitMessageGenerationError("No changed files detected.")

    if not diff_context.text.strip():
        raise CommitMessageGenerationError(
            "Diff is empty (no staged or unstaged content detected)."
        )

    prompt = build_prompt(changed_files, diff_context.text)

    try:
        raw_response = generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            model=model,
            host=host,
        )
        return clean_message(raw_response)
    except Exception as exc:
        raise CommitMessageGenerationError(
            f"Failed to generate commit message: {exc}"
        ) from exc