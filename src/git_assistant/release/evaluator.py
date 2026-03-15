from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from git_assistant.release.versioning import bump_version


UNRELEASED_HEADER = "## [Unreleased]"
VERSION_HEADER_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)


@dataclass(slots=True)
class ReleaseSuggestion:
    should_release: bool
    release_type: str | None
    next_version: str | None
    reason: str


def extract_unreleased_block(changelog_text: str) -> str:
    """
    Extract the [Unreleased] section from CHANGELOG.md.
    """
    if UNRELEASED_HEADER not in changelog_text:
        return ""

    start = changelog_text.index(UNRELEASED_HEADER)
    tail = changelog_text[start:]

    next_header_match = re.search(r"\n## \[", tail[len(UNRELEASED_HEADER):])
    if next_header_match is None:
        return tail

    end = len(UNRELEASED_HEADER) + next_header_match.start()
    return tail[:end]


def get_current_version_from_changelog(changelog_text: str) -> str:
    """
    Return the most recent released version found in the changelog.
    Defaults to 0.1.0 if none is found.
    """
    matches = VERSION_HEADER_RE.findall(changelog_text)
    if not matches:
        return "0.1.0"

    return matches[0]


def count_section_entries(unreleased_block: str, section_name: str) -> int:
    """
    Count bullet entries under a changelog section inside [Unreleased].
    """
    section_header = f"### {section_name}"
    if section_header not in unreleased_block:
        return 0

    lines = unreleased_block.splitlines()
    inside_section = False
    count = 0

    for line in lines:
        stripped = line.strip()

        if stripped == section_header:
            inside_section = True
            continue

        if inside_section and stripped.startswith("### "):
            break

        if inside_section and stripped.startswith("- "):
            count += 1

    return count


def evaluate_release(changelog_path: Path) -> ReleaseSuggestion:
    """
    Evaluate whether the current Unreleased section suggests a release.
    """
    if not changelog_path.exists():
        return ReleaseSuggestion(
            should_release=False,
            release_type=None,
            next_version=None,
            reason="CHANGELOG.md does not exist yet.",
        )

    changelog_text = changelog_path.read_text(encoding="utf-8")
    unreleased = extract_unreleased_block(changelog_text)

    if not unreleased.strip():
        return ReleaseSuggestion(
            should_release=False,
            release_type=None,
            next_version=None,
            reason="No [Unreleased] section found.",
        )

    added_count = count_section_entries(unreleased, "Added")
    fixed_count = count_section_entries(unreleased, "Fixed")
    changed_count = count_section_entries(unreleased, "Changed")
    docs_count = count_section_entries(unreleased, "Documentation")
    testing_count = count_section_entries(unreleased, "Testing")
    maintenance_count = count_section_entries(unreleased, "Maintenance")

    total_entries = (
        added_count
        + fixed_count
        + changed_count
        + docs_count
        + testing_count
        + maintenance_count
    )

    current_version = get_current_version_from_changelog(changelog_text)

    if total_entries < 3:
        return ReleaseSuggestion(
            should_release=False,
            release_type=None,
            next_version=None,
            reason=f"Only {total_entries} unreleased changelog entr{'y' if total_entries == 1 else 'ies'} so far.",
        )

    if added_count >= 2:
        release_type = "minor"
        reason = "Multiple Added entries accumulated in [Unreleased]."
    elif fixed_count >= 2 or changed_count >= 2:
        release_type = "patch"
        reason = "Multiple Fixed/Changed entries accumulated in [Unreleased]."
    elif added_count >= 1 and total_entries >= 3:
        release_type = "minor"
        reason = "At least one Added entry plus enough accumulated unreleased changes."
    else:
        release_type = "patch"
        reason = "Enough unreleased maintenance-level changes accumulated."

    return ReleaseSuggestion(
        should_release=True,
        release_type=release_type,
        next_version=bump_version(current_version, release_type),
        reason=reason,
    )