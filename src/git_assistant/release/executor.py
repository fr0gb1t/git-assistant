from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from git_assistant.changelog.writer import finalize_unreleased_release
from git_assistant.git.tags import create_git_tag

PYPROJECT_FILE = "pyproject.toml"
PACKAGE_INIT_FILE = "src/git_assistant/__init__.py"
RELEASE_MANAGED_FILES = [
    "CHANGELOG.md",
    PYPROJECT_FILE,
    PACKAGE_INIT_FILE,
]

PYPROJECT_VERSION_RE = re.compile(r'(?m)^(version = )"[^"]+"$')
PACKAGE_VERSION_RE = re.compile(r'(?m)^__version__ = "[^"]+"$')


@dataclass(slots=True)
class PreparedRelease:
    version: str
    tag: str
    release_date: str


def prepare_release_changelog(cwd: Path, version: str) -> PreparedRelease:
    """
    Convert [Unreleased] into a released changelog section and sync project
    version files before commit.
    """
    release_date = date.today().isoformat()
    sync_project_version_files(cwd, version=version)
    finalize_unreleased_release(cwd, version=version, release_date=release_date)

    return PreparedRelease(
        version=version,
        tag=f"v{version}",
        release_date=release_date,
    )


def create_release_tag(cwd: Path, version: str) -> str:
    """
    Create a Git tag for the released version after a successful commit.
    """
    tag = f"v{version}"
    create_git_tag(tag, cwd=cwd)
    return tag


def sync_project_version_files(cwd: Path, version: str) -> None:
    """
    Update version declarations that should match the released Git tag.
    """
    _update_pyproject_version(cwd / PYPROJECT_FILE, version)
    _update_package_init_version(cwd / PACKAGE_INIT_FILE, version)


def _update_pyproject_version(pyproject_path: Path, version: str) -> None:
    content = pyproject_path.read_text(encoding="utf-8")
    updated, count = PYPROJECT_VERSION_RE.subn(rf'\1"{version}"', content, count=1)
    if count != 1:
        raise ValueError("Could not find [project].version in pyproject.toml.")
    pyproject_path.write_text(updated, encoding="utf-8")


def _update_package_init_version(init_path: Path, version: str) -> None:
    if init_path.exists():
        content = init_path.read_text(encoding="utf-8")
    else:
        content = ""

    version_line = f'__version__ = "{version}"'
    if PACKAGE_VERSION_RE.search(content):
        updated = PACKAGE_VERSION_RE.sub(version_line, content, count=1)
    else:
        updated = content.rstrip()
        if updated:
            updated += "\n\n"
        updated += version_line + "\n"

    init_path.write_text(updated, encoding="utf-8")
