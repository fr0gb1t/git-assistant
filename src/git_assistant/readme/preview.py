from __future__ import annotations

import difflib
import webbrowser
from pathlib import Path

PREVIEW_DIR = ".git-assistant-preview"
README_PREVIEW_FILE = "README.preview.md"
README_DIFF_FILE = "README.diff"


def get_preview_dir(cwd: Path) -> Path:
    return cwd / PREVIEW_DIR


def write_readme_preview_files(
    cwd: Path,
    original_readme: str,
    updated_readme: str,
) -> tuple[Path, Path]:
    preview_dir = get_preview_dir(cwd)
    preview_dir.mkdir(parents=True, exist_ok=True)

    preview_path = preview_dir / README_PREVIEW_FILE
    diff_path = preview_dir / README_DIFF_FILE

    preview_path.write_text(updated_readme.rstrip() + "\n", encoding="utf-8")

    diff_text = "".join(
        difflib.unified_diff(
            original_readme.splitlines(keepends=True),
            updated_readme.splitlines(keepends=True),
            fromfile="README.md",
            tofile="README.preview.md",
        )
    )
    diff_path.write_text(diff_text, encoding="utf-8")

    return preview_path, diff_path


def open_preview_file(path: Path) -> None:
    webbrowser.open(path.resolve().as_uri())