from __future__ import annotations

from pathlib import Path

from git_assistant.changelog.entry import ChangelogEntry


CHANGELOG_FILE = "CHANGELOG.md"
CHANGELOG_HEADER = "# Changelog\n\n## [Unreleased]\n"


def get_changelog_path(cwd: Path) -> Path:
    """
    Return the path to the changelog file in the repository root.
    """
    return cwd / CHANGELOG_FILE


def ensure_changelog_exists(changelog_path: Path) -> None:
    """
    Create CHANGELOG.md with a basic structure if it does not exist.
    """
    if changelog_path.exists():
        return

    changelog_path.write_text(CHANGELOG_HEADER, encoding="utf-8")


def extract_unreleased_and_rest(content: str) -> tuple[str, str, str]:
    """
    Split changelog content into:
    - content before [Unreleased]
    - [Unreleased] block
    - content after [Unreleased]
    """
    unreleased_header = "## [Unreleased]"

    if unreleased_header not in content:
        before = content.rstrip()
        if before:
            before += "\n\n"
        return before, "## [Unreleased]\n", ""

    start = content.index(unreleased_header)
    before = content[:start]

    tail = content[start:]
    next_release_index = tail.find("\n## [", len(unreleased_header))
    if next_release_index == -1:
        unreleased_block = tail
        after = ""
    else:
        unreleased_block = tail[:next_release_index]
        after = tail[next_release_index:].lstrip("\n")

    return before, unreleased_block, after


def parse_unreleased_sections(unreleased_block: str) -> tuple[list[str], dict[str, list[str]]]:
    """
    Parse the [Unreleased] block into an ordered section map.

    Returns:
        section_order: list of section names in their original order
        sections: dict of section name -> bullet entries
    """
    lines = unreleased_block.splitlines()

    section_order: list[str] = []
    sections: dict[str, list[str]] = {}
    current_section: str | None = None

    for line in lines[1:]:  # skip "## [Unreleased]"
        stripped = line.strip()

        if not stripped:
            continue

        if stripped.startswith("### "):
            current_section = stripped[4:].strip()
            if current_section not in sections:
                sections[current_section] = []
                section_order.append(current_section)
            continue

        if stripped.startswith("- ") and current_section is not None:
            sections[current_section].append(stripped[2:].strip())

    return section_order, sections


def render_unreleased_block(section_order: list[str], sections: dict[str, list[str]]) -> str:
    """
    Render a normalized [Unreleased] block from section data.
    """
    lines: list[str] = ["## [Unreleased]"]

    for section in section_order:
        entries = sections.get(section, [])
        if not entries:
            continue

        lines.append("")
        lines.append(f"### {section}")
        for entry in entries:
            lines.append(f"- {entry}")

    return "\n".join(lines).rstrip() + "\n"


def insert_entry_into_unreleased(content: str, entry: ChangelogEntry) -> str:
    """
    Insert a changelog entry into the appropriate section inside [Unreleased].
    Creates the section if it does not already exist.
    """
    before, unreleased_block, after = extract_unreleased_and_rest(content)
    section_order, sections = parse_unreleased_sections(unreleased_block)

    if entry.section not in sections:
        sections[entry.section] = []
        section_order.append(entry.section)

    if entry.description not in sections[entry.section]:
        sections[entry.section].append(entry.description)

    updated_unreleased = render_unreleased_block(section_order, sections)

    result_parts = [before.rstrip(), updated_unreleased.rstrip()]
    if after.strip():
        result_parts.append(after.rstrip())

    return "\n\n".join(part for part in result_parts if part) + "\n"


def append_to_unreleased(cwd: Path, entry: ChangelogEntry) -> Path:
    """
    Ensure CHANGELOG.md exists and append a changelog entry to [Unreleased].
    Returns the path to the changelog file.
    """
    changelog_path = get_changelog_path(cwd)
    ensure_changelog_exists(changelog_path)

    content = changelog_path.read_text(encoding="utf-8")
    updated = insert_entry_into_unreleased(content, entry)

    changelog_path.write_text(updated, encoding="utf-8")
    return changelog_path