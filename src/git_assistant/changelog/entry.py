from __future__ import annotations

import re
from dataclasses import dataclass


CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|refactor|docs|test|chore)(\((?P<scope>[^)]+)\))?: (?P<description>.+)$"
)


@dataclass(slots=True)
class ChangelogEntry:
    """
    Structured changelog entry derived from a commit message.
    """

    section: str
    description: str


def map_commit_type_to_section(commit_type: str) -> str:
    """
    Map a Conventional Commit type to a changelog section.
    """
    mapping = {
        "feat": "Added",
        "fix": "Fixed",
        "refactor": "Changed",
        "docs": "Documentation",
        "test": "Testing",
        "chore": "Maintenance",
    }
    return mapping.get(commit_type, "Changed")


def build_changelog_entry(commit_message: str) -> ChangelogEntry:
    """
    Parse a Conventional Commit message and convert it into a changelog entry.
    """
    match = CONVENTIONAL_COMMIT_RE.match(commit_message.strip())
    if not match:
        raise ValueError(
            f"Commit message is not a valid Conventional Commit: {commit_message}"
        )

    commit_type = match.group(1)
    description = match.group("description").strip()

    return ChangelogEntry(
        section=map_commit_type_to_section(commit_type),
        description=description,
    )