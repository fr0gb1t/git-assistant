from __future__ import annotations

from pathlib import Path

from git_assistant.ai.base import AIConfig, AIProviderError, debug_print
from git_assistant.ai.factory import get_ai_provider
from git_assistant.context.repo_context import build_repo_tree
from git_assistant.release.evaluator import extract_unreleased_block
from git_assistant.readme.parser import (
    ReadmeGenerateResult,
    ReadmeUpdateResult,
    parse_readme_generate_response,
    parse_readme_update_response,
)
from git_assistant.readme.prompt import (
    README_GENERATE_SYSTEM_PROMPT,
    README_UPDATE_SYSTEM_PROMPT,
    build_readme_generate_prompt,
    build_readme_update_prompt,
)
from git_assistant.readme.preview import open_preview_file, write_readme_preview_files
from git_assistant.readme.preview import (
    cleanup_preview_files,
    open_preview_in_editor,
    read_preview_readme,
)
from git_assistant.readme.writer import get_readme_path, write_updated_readme


class ReadmeUpdateError(RuntimeError):
    """Raised when README evaluation or update fails."""


_SOURCE_EXTENSIONS = {".py", ".ts", ".js", ".go", ".rs", ".java", ".rb", ".cs"}
_SOURCE_IGNORED = {"__pycache__", ".venv", "dist", "build", ".git", "node_modules"}
_MAX_FILE_CHARS = 3_000
_MAX_TOTAL_CHARS = 20_000


def _build_source_context(cwd: Path) -> str | None:
    """
    Extract a lightweight source context from the codebase:
    module paths + their content (capped per file and in total).
    """
    parts: list[str] = []
    total_chars = 0

    for path in sorted(cwd.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix not in _SOURCE_EXTENSIONS:
            continue
        if any(ignored in path.parts for ignored in _SOURCE_IGNORED):
            continue

        rel = path.relative_to(cwd)

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        snippet = content[:_MAX_FILE_CHARS]
        if len(content) > _MAX_FILE_CHARS:
            snippet += "\n... [truncated]"

        entry = f"### {rel}\n{snippet}"
        entry_len = len(entry)

        if total_chars + entry_len > _MAX_TOTAL_CHARS:
            break

        parts.append(entry)
        total_chars += entry_len

    return "\n\n".join(parts) if parts else None


def evaluate_readme_update(cwd: Path, ai_config: AIConfig) -> ReadmeUpdateResult:
    readme_path = get_readme_path(cwd)
    changelog_path = cwd / "CHANGELOG.md"

    if not readme_path.exists():
        raise ReadmeUpdateError("README.md not found.")

    if not changelog_path.exists():
        raise ReadmeUpdateError("CHANGELOG.md not found.")

    readme_text = readme_path.read_text(encoding="utf-8")
    changelog_text = changelog_path.read_text(encoding="utf-8")
    unreleased_text = extract_unreleased_block(changelog_text)
    repo_tree = build_repo_tree(cwd)

    prompt = build_readme_update_prompt(
        readme_text=readme_text,
        unreleased_text=unreleased_text,
        full_changelog_text=changelog_text,
        repo_tree=repo_tree,
    )

    debug_print(ai_config, f"readme_update_prompt_size={len(README_UPDATE_SYSTEM_PROMPT) + len(prompt)}")

    provider = get_ai_provider(ai_config)

    try:
        raw_response = provider.generate(
            system_prompt=README_UPDATE_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
    except AIProviderError as exc:
        raise ReadmeUpdateError(f"README updater failed: {exc}") from exc

    result = parse_readme_update_response(raw_response)

    if "# " not in result.updated_readme:
        raise ReadmeUpdateError("Updated README appears invalid: missing top-level heading.")

    return result


def generate_initial_readme(cwd: Path, ai_config: AIConfig) -> ReadmeGenerateResult:
    """
    Generate an initial README.md when none exists.
    Uses the repo tree, changelog, and source code as context.
    """
    changelog_path = cwd / "CHANGELOG.md"

    changelog_text = (
        changelog_path.read_text(encoding="utf-8")
        if changelog_path.exists()
        else "No changelog available yet."
    )

    repo_tree = build_repo_tree(cwd)
    source_context = _build_source_context(cwd)

    prompt = build_readme_generate_prompt(
        changelog_text=changelog_text,
        repo_tree=repo_tree,
        source_context=source_context,
    )

    debug_print(ai_config, f"readme_generate_prompt_size={len(README_GENERATE_SYSTEM_PROMPT) + len(prompt)}")

    provider = get_ai_provider(ai_config)

    try:
        raw_response = provider.generate(
            system_prompt=README_GENERATE_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
    except AIProviderError as exc:
        raise ReadmeUpdateError(f"README generator failed: {exc}") from exc

    result = parse_readme_generate_response(raw_response)

    if "# " not in result.readme:
        raise ReadmeUpdateError("Generated README appears invalid: missing top-level heading.")

    return result


def prepare_readme_preview(
    cwd: Path,
    result: ReadmeUpdateResult,
) -> tuple[Path, Path]:
    readme_path = get_readme_path(cwd)
    original_readme = readme_path.read_text(encoding="utf-8")

    return write_readme_preview_files(
        cwd,
        original_readme=original_readme,
        updated_readme=result.updated_readme,
    )


def prepare_generated_readme_preview(
    cwd: Path,
    result: ReadmeGenerateResult,
) -> tuple[Path, Path]:
    return write_readme_preview_files(
        cwd,
        original_readme="",
        updated_readme=result.readme,
    )


def apply_readme_update(cwd: Path, result: ReadmeUpdateResult) -> Path:
    return write_updated_readme(cwd, result.updated_readme)


def apply_generated_readme(cwd: Path, result: ReadmeGenerateResult) -> Path:
    return write_updated_readme(cwd, result.readme)


def preview_readme_update(cwd: Path, result: ReadmeUpdateResult) -> tuple[Path, Path]:
    preview_path, diff_path = prepare_readme_preview(cwd, result)
    open_preview_file(preview_path)
    return preview_path, diff_path


def preview_generated_readme(cwd: Path, result: ReadmeGenerateResult) -> tuple[Path, Path]:
    preview_path, diff_path = prepare_generated_readme_preview(cwd, result)
    open_preview_file(preview_path)
    return preview_path, diff_path


def edit_readme_update(cwd: Path, result: ReadmeUpdateResult) -> Path:
    preview_path, _ = prepare_readme_preview(cwd, result)
    open_preview_in_editor(preview_path)
    edited_readme = read_preview_readme(cwd)
    return write_updated_readme(cwd, edited_readme)


def edit_generated_readme(cwd: Path, result: ReadmeGenerateResult) -> Path:
    preview_path, _ = prepare_generated_readme_preview(cwd, result)
    open_preview_in_editor(preview_path)
    edited_readme = read_preview_readme(cwd)
    return write_updated_readme(cwd, edited_readme)


def clear_readme_preview(cwd: Path) -> None:
    cleanup_preview_files(cwd)
