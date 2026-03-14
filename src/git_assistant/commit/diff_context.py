from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git_assistant.git.ops import (
    GitError,
    get_staged_diff,
    get_unstaged_diff,
    get_untracked_files,
    read_file_contents,
)


@dataclass(slots=True)
class DiffContextResult:
    """
    Prepared diff context ready to be sent to the LLM.
    """

    text: str
    was_truncated: bool
    staged_included: bool
    unstaged_included: bool
    untracked_included: bool


class DiffContextBuilder:
    """
    Build a bounded diff context for commit message generation.
    """

    def __init__(
        self,
        *,
        max_chars: int = 12000,
        section_max_chars: int = 6000,
        untracked_file_max_chars: int = 3000,
    ) -> None:
        self.max_chars = max_chars
        self.section_max_chars = section_max_chars
        self.untracked_file_max_chars = untracked_file_max_chars

    def build(
        self,
        cwd: Path,
        file_paths: list[str] | None = None,
    ) -> DiffContextResult:
        """
        Build combined diff context from staged, unstaged, and untracked changes.
        """
        try:
            staged = get_staged_diff(cwd, file_paths=file_paths)
            unstaged = get_unstaged_diff(cwd, file_paths=file_paths)
            untracked_files = self._get_relevant_untracked_files(cwd, file_paths)
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
        untracked_text, untracked_truncated = self._build_untracked_section(
            cwd,
            untracked_files,
        )

        parts: list[str] = []

        if staged_text:
            parts.append(staged_text)

        if unstaged_text:
            parts.append(unstaged_text)

        if untracked_text:
            parts.append(untracked_text)

        combined = "\n\n".join(parts)

        was_truncated = staged_truncated or unstaged_truncated or untracked_truncated

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
            untracked_included=bool(untracked_files),
        )

    def _get_relevant_untracked_files(
        self,
        cwd: Path,
        file_paths: list[str] | None,
    ) -> list[str]:
        """
        Return only the untracked files relevant to the current selection.
        """
        untracked_files = get_untracked_files(cwd)

        if file_paths is None:
            return untracked_files

        selected = set(file_paths)
        return [path for path in untracked_files if path in selected]

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

    def _build_untracked_section(
        self,
        cwd: Path,
        untracked_files: list[str],
    ) -> tuple[str, bool]:
        """
        Build a synthetic section for untracked files using their file contents.
        """
        if not untracked_files:
            return "", False

        entries: list[str] = []
        truncated = False

        for file_path in untracked_files:
            contents = read_file_contents(file_path, cwd)

            file_body = contents
            if len(file_body) > self.untracked_file_max_chars:
                omitted = len(file_body) - self.untracked_file_max_chars
                file_body = (
                    file_body[: self.untracked_file_max_chars].rstrip()
                    + f"\n\n[TRUNCATED: omitted {omitted} characters from this file]\n"
                )
                truncated = True

            entries.append(
                f"FILE: {file_path}\n"
                f"STATUS: untracked\n"
                f"CONTENT:\n{file_body}"
            )

        section = "UNTRACKED FILES:\n" + "\n\n".join(entries)
        return section, truncated