from __future__ import annotations

from pathlib import Path

README_FILE = "README.md"


def get_readme_path(cwd: Path) -> Path:
    return cwd / README_FILE


def write_updated_readme(cwd: Path, updated_readme: str) -> Path:
    readme_path = get_readme_path(cwd)
    readme_path.write_text(updated_readme.rstrip() + "\n", encoding="utf-8")
    return readme_path