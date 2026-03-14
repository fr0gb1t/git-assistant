from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git_assistant.ai.base import AIConfig, AIProviderError
from git_assistant.ai.factory import get_ai_provider
from git_assistant.commit.diff_context import DiffContextBuilder
from git_assistant.commit.message import (
    SYSTEM_PROMPT,
    build_prompt,
    clean_message,
)
from git_assistant.git.ops import GitError, get_changed_files


class CommitMessageGenerationError(RuntimeError):
    """Raised when the commit message could not be generated."""


@dataclass(slots=True)
class CommitMessageResult:
    """
    Result of commit message generation.
    """

    message: str
    was_truncated: bool
    staged_included: bool
    unstaged_included: bool

REPAIR_PROMPT_TEMPLATE = """
The previous response did not follow the required format.

You must now output exactly ONE valid Conventional Commit message.

Rules:
- Output one single line only
- No explanation
- No markdown
- No bullets
- No quotes
- Must start with one of:
  feat, fix, refactor, docs, test, chore

Previous invalid response:
{invalid_response}
"""

def generate_commit_message(
    cwd: Path,
    ai_config: AIConfig | None = None,
) -> CommitMessageResult:
    """
    Generate a commit message for the current repository state.
    """
    config = ai_config or AIConfig()

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
        provider = get_ai_provider(config)

        raw_response = provider.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        if config.debug:
            print("\n[DEBUG] Initial provider output:")
            print(repr(raw_response))

        try:
            cleaned_message = clean_message(raw_response)
        except ValueError:
            if config.debug:
                print("[DEBUG] Initial output did not match Conventional Commit format.")
                print("[DEBUG] Retrying with repair prompt...")

            repair_prompt = REPAIR_PROMPT_TEMPLATE.format(
                invalid_response=raw_response
            )

            repaired_response = provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=repair_prompt,
            )

            if config.debug:
                print("\n[DEBUG] Repaired provider output:")
                print(repr(repaired_response))

            cleaned_message = clean_message(repaired_response)

    except (AIProviderError, ValueError) as exc:
        raise CommitMessageGenerationError(
            f"Failed to generate commit message: {exc}"
        ) from exc

    return CommitMessageResult(
        message=cleaned_message,
        was_truncated=diff_context.was_truncated,
        staged_included=diff_context.staged_included,
        unstaged_included=diff_context.unstaged_included,
    )