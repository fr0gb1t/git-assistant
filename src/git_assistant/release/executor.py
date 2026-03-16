from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from git_assistant.changelog.writer import finalize_unreleased_release
from git_assistant.git.tags import create_git_tag


@dataclass(slots=True)
class PreparedRelease:
    version: str
    tag: str
    release_date: str


def prepare_release_changelog(cwd: Path, version: str) -> PreparedRelease:
    """
    Convert [Unreleased] into a released changelog section before commit.
    """
    release_date = date.today().isoformat()
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