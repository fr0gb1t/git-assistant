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
SEMVER_RE = re.compile(r"^v?(\d+\.\d+\.\d+)$")


@dataclass(slots=True)
class PreparedRelease:
    version: str
    tag: str
    release_date: str


def normalize_release_version(version: str) -> str:
    """
    Accept `0.1.0` and `v0.1.0`, returning the normalized plain version.
    """
    match = SEMVER_RE.fullmatch(version.strip())
    if match is None:
        raise ValueError(
            "Invalid release version. Use semantic version format like 0.7.2 or v0.7.2."
        )
    return match.group(1)


def prepare_release_changelog(cwd: Path, version: str) -> PreparedRelease:
    """
    Convert [Unreleased] into a released changelog section and sync project
    version files before commit.
    """
    normalized_version = normalize_release_version(version)
    release_date = date.today().isoformat()
    sync_project_version_files(cwd, version=normalized_version)
    finalize_unreleased_release(cwd, version=normalized_version, release_date=release_date)

    return PreparedRelease(
        version=normalized_version,
        tag=f"v{normalized_version}",
        release_date=release_date,
    )


def get_release_managed_files(cwd: Path) -> list[str]:
    """
    Return only the release-managed files that actually exist in this repository.
    CHANGELOG.md is always included because release preparation depends on it.
    """
    managed_files = ["CHANGELOG.md"]

    for file_path in (PYPROJECT_FILE, PACKAGE_INIT_FILE):
        if (cwd / file_path).exists():
            managed_files.append(file_path)

    return managed_files


def create_release_tag(cwd: Path, version: str) -> str:
    """
    Create a Git tag for the released version after a successful commit.
    """
    normalized_version = normalize_release_version(version)
    tag = f"v{normalized_version}"
    create_git_tag(tag, cwd=cwd)
    return tag


def sync_project_version_files(cwd: Path, version: str) -> None:
    """
    Update version declarations that should match the released Git tag.
    """
    normalized_version = normalize_release_version(version)
    pyproject_path = cwd / PYPROJECT_FILE
    package_init_path = cwd / PACKAGE_INIT_FILE

    if pyproject_path.exists():
        _update_pyproject_version(pyproject_path, normalized_version)

    if package_init_path.exists():
        _update_package_init_version(package_init_path, normalized_version)


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
