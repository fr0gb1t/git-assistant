from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from git_assistant.git.tags import get_latest_git_tag
from git_assistant.release.versioning import bump_version, parse_version

UNRELEASED_HEADER = "## [Unreleased]"
VERSION_HEADER_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
INTERNAL_CHANGE_KEYWORDS = {
    "release",
    "version",
    "sync",
    "synchronization",
    "metadata",
    "pyproject",
    "package init",
    "__version__",
    "changelog",
    "test",
    "tests",
    "internal",
    "tooling",
    "automation",
    "repo",
    "repository",
}
USER_FACING_KEYWORDS = {
    "cli",
    "command",
    "flag",
    "option",
    "interactive",
    "mode",
    "support",
    "provider",
    "integration",
    "generate",
    "preview",
    "readme",
}
MAJOR_CHANGE_KEYWORDS = {
    "breaking",
    "incompatible",
    "removed",
    "remove",
    "migration",
}
FIRST_STABLE_VERSION = "1.0.0"
FIRST_STABLE_MIN_MINOR = 7
FIRST_STABLE_MIN_RELEASES = 5
FIRST_STABLE_MIN_ENTRIES = 20


@dataclass(slots=True)
class ReleaseSuggestion:
    should_release: bool
    release_type: str | None
    next_version: str | None
    reason: str


@dataclass(slots=True)
class StableReleaseHint:
    should_suggest: bool
    version: str | None
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

def get_current_version(cwd: Path, changelog_text: str) -> str:
    """
    Return the current version using this priority:
    1. latest Git tag
    2. latest version found in CHANGELOG.md
    3. default 0.0.0
    """
    latest_tag = get_latest_git_tag(cwd)
    if latest_tag is not None:
        return latest_tag

    matches = VERSION_HEADER_RE.findall(changelog_text)
    if matches:
        return matches[0]

    return "0.0.0"

def get_current_version_from_changelog(changelog_text: str) -> str:
    """
    Return the most recent released version found in the changelog.
    Defaults to 0.0.0 if none is found.
    """
    matches = VERSION_HEADER_RE.findall(changelog_text)
    if not matches:
        return "0.0.0"

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


def count_released_history(changelog_text: str) -> tuple[int, int]:
    """
    Count released version blocks and bullet entries outside [Unreleased].
    """
    released_versions = 0
    released_entries = 0
    inside_released_block = False

    for raw_line in changelog_text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line == UNRELEASED_HEADER:
            inside_released_block = False
            continue

        version_match = VERSION_HEADER_RE.match(line)
        if version_match:
            version = parse_version(version_match.group(1))
            inside_released_block = version.major == 0
            if inside_released_block:
                released_versions += 1
            continue

        if inside_released_block and line.startswith("- "):
            released_entries += 1

    return released_versions, released_entries


def extract_section_entries(unreleased_block: str) -> dict[str, list[str]]:
    """
    Parse bullet entries from the changelog by section name.
    """
    entries: dict[str, list[str]] = {}
    current_section: str | None = None

    for raw_line in unreleased_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("### "):
            current_section = line[4:].strip()
            entries.setdefault(current_section, [])
            continue

        if line.startswith("- ") and current_section is not None:
            entries[current_section].append(line[2:].strip())

    return entries


def _normalize_entry(entry: str) -> str:
    return re.sub(r"[^a-z0-9_./ -]+", " ", entry.lower())


def looks_like_internal_tooling_change(entry: str) -> bool:
    normalized = _normalize_entry(entry)
    return any(keyword in normalized for keyword in INTERNAL_CHANGE_KEYWORDS)


def looks_like_user_facing_change(entry: str) -> bool:
    normalized = _normalize_entry(entry)
    has_user_facing_signal = any(keyword in normalized for keyword in USER_FACING_KEYWORDS)
    if not has_user_facing_signal:
        return False
    if "interactive" in normalized or "cli" in normalized or "command" in normalized:
        return True
    return not looks_like_internal_tooling_change(entry)


def looks_like_major_change(entry: str) -> bool:
    normalized = _normalize_entry(entry)
    return any(keyword in normalized for keyword in MAJOR_CHANGE_KEYWORDS)


def evaluate_first_stable_hint(cwd: Path, changelog_path: Path) -> StableReleaseHint:
    """
    Suggest considering 1.0.0 when a pre-1.0 project shows enough release history.
    """
    if not changelog_path.exists():
        return StableReleaseHint(
            should_suggest=False,
            version=None,
            reason="CHANGELOG.md does not exist yet.",
        )

    changelog_text = changelog_path.read_text(encoding="utf-8")
    current_version = parse_version(get_current_version(cwd, changelog_text))

    if current_version.major != 0:
        return StableReleaseHint(
            should_suggest=False,
            version=None,
            reason="Project is already on a stable major version.",
        )

    if current_version.minor < FIRST_STABLE_MIN_MINOR:
        return StableReleaseHint(
            should_suggest=False,
            version=None,
            reason=(
                f"Current version is below 0.{FIRST_STABLE_MIN_MINOR}.0, "
                "so a first stable release hint would be premature."
            ),
        )

    released_versions, released_entries = count_released_history(changelog_text)

    if released_versions < FIRST_STABLE_MIN_RELEASES:
        return StableReleaseHint(
            should_suggest=False,
            version=None,
            reason="Release history is still too short for a first stable release hint.",
        )

    if released_entries < FIRST_STABLE_MIN_ENTRIES:
        return StableReleaseHint(
            should_suggest=False,
            version=None,
            reason="Changelog history is still too small for a first stable release hint.",
        )

    return StableReleaseHint(
        should_suggest=True,
        version=FIRST_STABLE_VERSION,
        reason=(
            "Project is still on 0.x, but accumulated release history suggests it may be "
            "ready for a first stable 1.0.0 release."
        ),
    )


def evaluate_release(cwd: Path, changelog_path: Path) -> ReleaseSuggestion:
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

    current_version = get_current_version(cwd, changelog_text)
    section_entries = extract_section_entries(unreleased)
    all_entries = [
        entry
        for entries in section_entries.values()
        for entry in entries
    ]

    if not all_entries:
        return ReleaseSuggestion(
            should_release=False,
            release_type=None,
            next_version=None,
            reason="No unreleased changelog entries found.",
        )

    if any(looks_like_major_change(entry) for entry in all_entries):
        release_type = "major"
        reason = "Unreleased changes contain a likely breaking or migration-related change."
    else:
        added_entries = section_entries.get("Added", [])
        user_facing_added_entries = [
            entry for entry in added_entries if looks_like_user_facing_change(entry)
        ]
        internal_added_entries = [
            entry for entry in added_entries if looks_like_internal_tooling_change(entry)
        ]

        if user_facing_added_entries:
            release_type = "minor"
            reason = "Unreleased changes include at least one clearly user-facing added feature."
        elif any(
            section_entries.get(section_name)
            for section_name in ("Added", "Fixed", "Changed", "Documentation", "Testing", "Maintenance")
        ):
            release_type = "patch"
            if internal_added_entries:
                reason = "Added entries appear internal/tooling-oriented, so patch is more appropriate."
            else:
                reason = "Unreleased changes include non-breaking fixes, maintenance, or internal improvements."
        else:
            return ReleaseSuggestion(
                should_release=False,
                release_type=None,
                next_version=None,
                reason="No releasable changelog entries found.",
            )

    return ReleaseSuggestion(
        should_release=True,
        release_type=release_type,
        next_version=bump_version(current_version, release_type),
        reason=reason,
    )
