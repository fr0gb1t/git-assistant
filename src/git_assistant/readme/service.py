from __future__ import annotations

from pathlib import Path

from git_assistant.ai.base import AIConfig, AIProviderError, debug_print
from git_assistant.ai.factory import get_ai_provider
from git_assistant.context.repo_context import build_repo_tree
from git_assistant.readme.parser import ReadmeUpdateResult, parse_readme_update_response
from git_assistant.readme.prompt import (
    README_UPDATE_SYSTEM_PROMPT,
    build_readme_update_prompt,
)
from git_assistant.readme.preview import open_preview_file, write_readme_preview_files
from git_assistant.readme.writer import get_readme_path, write_updated_readme


class ReadmeUpdateError(RuntimeError):
    """Raised when README evaluation or update fails."""


def evaluate_readme_update(cwd: Path, ai_config: AIConfig) -> ReadmeUpdateResult:
    readme_path = get_readme_path(cwd)
    changelog_path = cwd / "CHANGELOG.md"

    if not readme_path.exists():
        raise ReadmeUpdateError("README.md not found.")

    if not changelog_path.exists():
        raise ReadmeUpdateError("CHANGELOG.md not found.")

    readme_text = readme_path.read_text(encoding="utf-8")
    changelog_text = changelog_path.read_text(encoding="utf-8")
    repo_tree = build_repo_tree(cwd)

    prompt = build_readme_update_prompt(
        readme_text=readme_text,
        changelog_text=changelog_text,
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


def apply_readme_update(cwd: Path, result: ReadmeUpdateResult) -> Path:
    return write_updated_readme(cwd, result.updated_readme)


def preview_readme_update(cwd: Path, result: ReadmeUpdateResult) -> tuple[Path, Path]:
    preview_path, diff_path = prepare_readme_preview(cwd, result)
    open_preview_file(preview_path)
    return preview_path, diff_path