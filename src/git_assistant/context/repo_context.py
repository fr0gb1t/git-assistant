from __future__ import annotations

from pathlib import Path


IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
    "git_assistant.egg-info",
}


def build_repo_tree(cwd: Path, max_depth: int = 3) -> str:
    """
    Build a simplified repository tree for AI context.
    """
    lines: list[str] = []

    for path in sorted(cwd.rglob("*")):
        rel = path.relative_to(cwd)

        if any(part in IGNORED_PARTS for part in rel.parts):
            continue

        depth = len(rel.parts)
        if depth > max_depth:
            continue

        suffix = "/" if path.is_dir() else ""
        lines.append(f"{rel}{suffix}")

    return "\n".join(lines)