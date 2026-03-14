from __future__ import annotations

from pathlib import Path

from git_assistant.changelog.entry import ChangelogEntry


CHANGELOG_HEADER = "# Changelog\n\n## [Unreleased]\n"


def get_changelog_path(cwd: Path) -> Path:
    """
    Return the path to the changelog file in the repository root.
    """
    return cwd / "CHANGELOG.md"


def ensure_changelog_exists(changelog_path: Path) -> None:
    """
    Create CHANGELOG.md with a basic structure if it does not exist.
    """
    if changelog_path.exists():
        return

    changelog_path.write_text(CHANGELOG_HEADER, encoding="utf-8")


def insert_entry_into_unreleased(content: str, entry: ChangelogEntry) -> str:
    """
    Insert a changelog entry into the appropriate section inside [Unreleased].
    Creates the section if it does not already exist.
    """
    unreleased_header = "## [Unreleased]"
    section_header = f"### {entry.section}"
    bullet_line = f"- {entry.description}"

    if unreleased_header not in content:
        content = content.rstrip() + "\n\n## [Unreleased]\n"

    unreleased_index = content.index(unreleased_header)
    after_unreleased = content[unreleased_index:]

    next_section_index = after_unreleased.find("\n## ", len(unreleased_header))
    if next_section_index == -1:
        unreleased_block = after_unreleased
        rest_of_content = ""
    else:
        unreleased_block = after_unreleased[:next_section_index]
        rest_of_content = after_unreleased[next_section_index:]

    before_unreleased = content[:unreleased_index]

    if section_header in unreleased_block:
        lines = unreleased_block.splitlines()
        new_lines: list[str] = []
        inserted = False

        for i, line in enumerate(lines):
            new_lines.append(line)

            if line.strip() == section_header:
                # Skip possible blank lines immediately after header
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    new_lines.append(lines[j])
                    j += 1

                new_lines.append(bullet_line)
                inserted = True

                # copy the remaining lines once and stop outer duplication
                new_lines.extend(lines[j:])
                break

        if not inserted:
            new_lines.append("")
            new_lines.append(section_header)
            new_lines.append(bullet_line)

        updated_unreleased = "\n".join(new_lines).rstrip() + "\n"
    else:
        unreleased_block = unreleased_block.rstrip() + "\n\n"
        updated_unreleased = (
            unreleased_block
            + f"{section_header}\n"
            + f"{bullet_line}\n"
        )

    return before_unreleased + updated_unreleased + rest_of_content.lstrip("\n")


def append_to_unreleased(cwd: Path, entry: ChangelogEntry) -> Path:
    """
    Ensure CHANGELOG.md exists and append a changelog entry to [Unreleased].
    Returns the path to the changelog file.
    """
    changelog_path = get_changelog_path(cwd)
    ensure_changelog_exists(changelog_path)

    content = changelog_path.read_text(encoding="utf-8")
    updated = insert_entry_into_unreleased(content, entry)

    changelog_path.write_text(updated.rstrip() + "\n", encoding="utf-8")
    return changelog_path