from __future__ import annotations

import difflib
import os
import platform
import shutil
import subprocess
import webbrowser
from os import environ
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


def read_preview_readme(cwd: Path) -> str:
    preview_path = get_preview_dir(cwd) / README_PREVIEW_FILE
    return preview_path.read_text(encoding="utf-8")


def cleanup_preview_files(cwd: Path) -> None:
    preview_dir = get_preview_dir(cwd)
    if preview_dir.exists():
        shutil.rmtree(preview_dir)


def open_preview_file(path: Path) -> None:
    webbrowser.open(path.resolve().as_uri())


def open_preview_pair(preview_path: Path, diff_path: Path) -> None:
    open_preview_file(preview_path)
    open_diff_file(diff_path)


def open_diff_file(path: Path) -> None:
    command = _resolve_opener_command(path)
    if command is None:
        return

    with open(os.devnull, "wb") as devnull:
        subprocess.Popen(
            command,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
        )


def open_preview_in_editor(path: Path) -> None:
    editor = _resolve_editor()
    if editor is None:
        raise RuntimeError("No terminal editor available. Set $EDITOR to enable README editing.")

    subprocess.run([editor, str(path)], check=False)


def _resolve_editor() -> str | None:
    configured = environ.get("EDITOR")
    if configured:
        return configured

    for candidate in ("nano", "vim", "vi"):
        if shutil.which(candidate):
            return candidate

    return None


def _resolve_opener_command(path: Path) -> list[str] | None:
    system = platform.system()

    if system == "Darwin":
        return ["open", str(path)]

    if system == "Windows":
        return ["cmd", "/c", "start", "", str(path)]

    if shutil.which("xdg-open"):
        return ["xdg-open", str(path)]

    return None
