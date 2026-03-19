from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from git_assistant.changelog.writer import finalize_unreleased_release
from git_assistant.config.loader import ReleaseConfig, ReleaseVersionTarget
from git_assistant.git.tags import create_git_tag

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


def prepare_release_changelog(
    cwd: Path,
    version: str,
    release_config: ReleaseConfig | None = None,
) -> PreparedRelease:
    """
    Convert [Unreleased] into a released changelog section and sync project
    version files before commit.
    """
    normalized_version = normalize_release_version(version)
    release_date = date.today().isoformat()
    sync_project_version_files(cwd, version=normalized_version, release_config=release_config)
    finalize_unreleased_release(cwd, version=normalized_version, release_date=release_date)

    return PreparedRelease(
        version=normalized_version,
        tag=f"v{normalized_version}",
        release_date=release_date,
    )


def get_release_managed_files(
    cwd: Path,
    release_config: ReleaseConfig | None = None,
) -> list[str]:
    """
    Return only the release-managed files that actually exist in this repository.
    CHANGELOG.md is always included because release preparation depends on it.
    """
    config = release_config or ReleaseConfig()
    configured_files = list(config.managed_files)

    for target in config.version_targets:
        if target.path not in configured_files:
            configured_files.append(target.path)

    managed_files: list[str] = []

    for file_path in configured_files:
        if file_path == "CHANGELOG.md" or (cwd / file_path).exists():
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


def sync_project_version_files(
    cwd: Path,
    version: str,
    release_config: ReleaseConfig | None = None,
) -> None:
    """
    Update version declarations that should match the released Git tag.
    """
    normalized_version = normalize_release_version(version)
    config = release_config or ReleaseConfig()

    for target in config.version_targets:
        target_path = cwd / target.path
        if not target_path.exists():
            continue

        _update_version_target(target_path, target, normalized_version)

def _update_version_target(
    target_path: Path,
    target: ReleaseVersionTarget,
    version: str,
) -> None:
    content = target_path.read_text(encoding="utf-8")
    pattern = re.compile(target.pattern, re.MULTILINE)
    replacement = target.replacement.format(version=version)
    updated, count = pattern.subn(replacement, content, count=1)
    if count != 1:
        raise ValueError(
            f"Could not update configured release version target: {target.path}"
        )
    target_path.write_text(updated, encoding="utf-8")
