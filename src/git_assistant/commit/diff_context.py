from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git_assistant.git.ops import GitError, get_staged_diff, get_unstaged_diff


@dataclass(slots=True)
class DiffContextResult:
    """
    Prepared diff context ready to be sent to the LLM.
    """

    text: str
    was_truncated: bool
    staged_included: bool
    unstaged_included: bool


class DiffContextBuilder:
    """
    Build a bounded diff context for commit message generation.
    """

    def __init__(
        self,
        *,
        max_chars: int = 12000,
        section_max_chars: int = 6000,
    ) -> None:
        self.max_chars = max_chars
        self.section_max_chars = section_max_chars

    def build(self, cwd: Path, file_paths: list[str] | None = None,) -> DiffContextResult:
        """
        Build combined diff context from staged and unstaged changes.
        """
        try:
            staged = get_staged_diff(cwd, file_paths=file_paths)
            unstaged = get_unstaged_diff(cwd, file_paths=file_paths)
        except GitError:
            raise

        staged_text, staged_truncated = self._truncate_section(
            "STAGED CHANGES",
            staged,
        )
        unstaged_text, unstaged_truncated = self._truncate_section(
            "UNSTAGED CHANGES",
            unstaged,
        )

        parts: list[str] = []

        if staged_text:
            parts.append(staged_text)

        if unstaged_text:
            parts.append(unstaged_text)

        combined = "\n\n".join(parts)

        was_truncated = staged_truncated or unstaged_truncated

        if len(combined) > self.max_chars:
            combined = (
                combined[: self.max_chars].rstrip()
                + "\n\n[TRUNCATED: total diff context exceeded maximum size]\n"
            )
            was_truncated = True

        return DiffContextResult(
            text=combined,
            was_truncated=was_truncated,
            staged_included=bool(staged.strip()),
            unstaged_included=bool(unstaged.strip()),
        )

    def _truncate_section(self, title: str, diff_text: str) -> tuple[str, bool]:
        """
        Format and truncate an individual diff section.
        """
        if not diff_text.strip():
            return "", False

        body = diff_text
        truncated = False

        if len(body) > self.section_max_chars:
            omitted = len(body) - self.section_max_chars
            body = (
                body[: self.section_max_chars].rstrip()
                + f"\n\n[TRUNCATED: omitted {omitted} characters from this section]\n"
            )
            truncated = True

        section = f"{title}:\n{body}"
        return section, truncated