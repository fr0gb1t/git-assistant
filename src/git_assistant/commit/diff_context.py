from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from git_assistant.git.ops import (
    GitError,
    get_staged_diff,
    get_unstaged_diff,
    get_untracked_files,
    is_text_file,
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
            untracked_text, had_untracked, untracked_truncated = self._build_untracked_section(
                cwd,
                file_paths=file_paths,
            )
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
            untracked_included=had_untracked,
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
        file_paths: list[str] | None = None,
    ) -> tuple[str, bool, bool]:
        """
        Build a context section for untracked files.

        Text files are included with content.
        Binary / non-text files are listed by filename only.

        Returns:
            section_text, had_untracked_files, was_truncated
        """
        untracked_files = get_untracked_files(cwd)

        if file_paths is not None:
            selected_set = set(file_paths)
            untracked_files = [path for path in untracked_files if path in selected_set]

        if not untracked_files:
            return "", False, False

        text_entries: list[str] = []
        binary_entries: list[str] = []
        was_truncated = False

        for file_path in untracked_files:
            if is_text_file(file_path, cwd=cwd):
                content = read_file_contents(
                    file_path,
                    cwd=cwd,
                    max_chars=self.section_max_chars // 2,
                )

                if "[TRUNCATED:" in content:
                    was_truncated = True

                text_entries.append(
                    f"FILE: {file_path}\n"
                    f"```text\n{content}\n```"
                )
            else:
                binary_entries.append(file_path)

        parts: list[str] = []

        if text_entries:
            parts.append("UNTRACKED TEXT FILES:\n" + "\n\n".join(text_entries))

        if binary_entries:
            binary_lines = "\n".join(f"- {file_path}" for file_path in binary_entries)
            parts.append(
                "UNTRACKED BINARY OR NON-TEXT FILES:\n"
                f"{binary_lines}"
            )

        section = "\n\n".join(parts)

        return section, True, was_truncated