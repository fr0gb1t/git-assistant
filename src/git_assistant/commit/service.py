from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git_assistant.ai.base import AIConfig, AIProviderError, debug_print
from git_assistant.ai.factory import get_ai_provider
from git_assistant.context.diff_context import DiffContextBuilder
from git_assistant.context.repo_context import build_repo_tree
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
    untracked_included: bool


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
    selected_files: list[str] | None = None,
) -> CommitMessageResult:
    """
    Generate a commit message for the current repository state.
    """
    config = ai_config or AIConfig()

    try:
        changed_files = selected_files if selected_files is not None else get_changed_files(cwd)
        diff_context = DiffContextBuilder().build(cwd, file_paths=selected_files)
    except GitError as exc:
        raise CommitMessageGenerationError(f"Git error: {exc}") from exc

    if not changed_files:
        raise CommitMessageGenerationError("No changed files detected.")

    if not diff_context.text.strip():
        raise CommitMessageGenerationError(
            "Diff is empty (no staged or unstaged content detected)."
        )

    repo_tree = build_repo_tree(cwd)

    prompt = build_prompt(
        changed_files=changed_files,
        diff=diff_context.text,
        repo_tree=repo_tree,
    )

    debug_print(config, "\n----- SYSTEM PROMPT BEGIN -----")
    debug_print(config, SYSTEM_PROMPT[:4000])
    debug_print(config, "\n----- SYSTEM PROMPT END -----")

    debug_print(config, "\n----- AI PROMPT BEGIN -----")
    debug_print(config, prompt[:4000])
    debug_print(config, "----- AI PROMPT END -----\n")

    debug_print(config, f"files_analyzed={len(changed_files)}")
    debug_print(config, f"diff_truncated={diff_context.was_truncated}")
    debug_print(config, f"prompt_size={len(SYSTEM_PROMPT) + len(prompt)}")


    try:
        provider = get_ai_provider(config)

        raw_response = provider.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        try:
            cleaned_message = clean_message(raw_response)
        except ValueError:
            debug_print(
                config,
                "initial_output_invalid=True, retrying_with_repair_prompt=True",
            )

            repair_prompt = REPAIR_PROMPT_TEMPLATE.format(
                invalid_response=raw_response
            )

            repaired_response = provider.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=repair_prompt,
            )

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
        untracked_included=diff_context.untracked_included,
    )