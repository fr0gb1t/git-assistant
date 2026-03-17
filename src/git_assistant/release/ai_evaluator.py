from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from git_assistant.ai.base import AIConfig, debug_print
from git_assistant.ai.factory import get_ai_provider
from git_assistant.release.evaluator import extract_unreleased_block, get_current_version
from git_assistant.release.versioning import bump_version


@dataclass(slots=True)
class AIReleaseSuggestion:
    should_release: bool
    release_type: str | None
    next_version: str | None
    reason: str


RELEASE_EVALUATION_SYSTEM_PROMPT = """
You are a semantic versioning release evaluator.

Your task is to analyze the "Unreleased" section of a changelog that follows the Keep a Changelog format.

You must decide whether a release should be created and what type.

Return ONLY valid JSON:

{
  "should_release": true,
  "release_type": "patch|minor|major|null",
  "reason": "short explanation"
}

Guidelines:

MAJOR
Use only when:
- breaking API changes
- incompatible CLI behavior
- removed features
- explicit migration requirements

MINOR
Use only when:
- a clearly user-facing feature appears under "Added"
- a new CLI command, flag, mode, or directly usable workflow was introduced
- users can do something meaningfully new after this release

Do not use MINOR for:
- internal release automation
- version or metadata synchronization
- changelog maintenance
- test additions
- documentation changes
- refactors
- internal tooling improvements that do not change user-facing behavior

Multiple "Added" entries can support MINOR, but a single "Added" entry is not enough by itself.

PATCH
Use when:
- bug fixes
- refactors
- performance improvements
- documentation updates
- tests
- internal tooling improvements
- release workflow improvements
- version synchronization
- changelog or repository maintenance

If the Unreleased section contains mostly "Changed", "Fixed", "Refactor", or "Docs", prefer PATCH.

No Release
If the section contains only trivial maintenance or formatting.

Important rules:

- Prefer PATCH unless the added change is clearly user-facing.
- Documentation alone does not justify MINOR.
- Internal repository automation is usually PATCH.

Output JSON only.
"""

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

def build_unreleased_summary(unreleased_block: str) -> str:
    """
    Build a compact summary of the Unreleased changelog section.
    """
    section_names = [
        "Added",
        "Fixed",
        "Changed",
        "Documentation",
        "Testing",
        "Maintenance",
    ]

    counts: dict[str, int] = {name: 0 for name in section_names}
    current_section: str | None = None

    for raw_line in unreleased_block.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("### "):
            section_name = line[4:].strip()
            current_section = section_name if section_name in counts else None
            continue

        if line.startswith("- ") and current_section is not None:
            counts[current_section] += 1

    total_entries = sum(counts.values())

    lines = [f"- total entries: {total_entries}"]
    for section_name in section_names:
        lines.append(f"- {section_name}: {counts[section_name]}")

    return "\n".join(lines)


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


def build_release_evaluation_prompt(
    current_version: str,
    unreleased_block: str,
) -> str:
    summary = build_unreleased_summary(unreleased_block)
    section_entries = extract_section_entries(unreleased_block)
    added_entries = section_entries.get("Added", [])
    internal_added_entries = [
        entry for entry in added_entries if looks_like_internal_tooling_change(entry)
    ]

    return f"""
Current version:
{current_version}

Repository context:
This is a software project under active development.
Evaluate release readiness based on the changelog entries and the meaning of the accumulated changes.

Important interpretation hint:
Prefer PATCH unless a new capability is clearly user-facing.
Internal release automation, version sync, changelog maintenance, tests, docs, and refactors are usually PATCH.
A single "Added" entry does not justify MINOR by itself.

Unreleased summary:
{summary}

Added entries:
{format_entries_for_prompt(added_entries)}

Added entries that look internal/tooling-oriented:
{format_entries_for_prompt(internal_added_entries)}

Unreleased changelog section:
{unreleased_block}
"""


def format_entries_for_prompt(entries: list[str]) -> str:
    if not entries:
        return "- none"
    return "\n".join(f"- {entry}" for entry in entries)


def looks_like_internal_tooling_change(entry: str) -> bool:
    normalized = re.sub(r"[^a-z0-9_./ -]+", " ", entry.lower())
    return any(keyword in normalized for keyword in INTERNAL_CHANGE_KEYWORDS)


def parse_ai_release_response(raw_response: str, current_version: str) -> AIReleaseSuggestion:
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"AI release evaluator did not return valid JSON: {raw_response}"
        ) from exc

    should_release = data.get("should_release")
    release_type = data.get("release_type")
    reason = data.get("reason")

    if not isinstance(should_release, bool):
        raise ValueError("AI release evaluator returned invalid 'should_release' value.")

    if release_type is not None and release_type not in {"patch", "minor", "major"}:
        raise ValueError("AI release evaluator returned invalid 'release_type' value.")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("AI release evaluator returned invalid 'reason' value.")

    next_version = None
    if should_release and release_type is not None:
        next_version = bump_version(current_version, release_type)

    return AIReleaseSuggestion(
        should_release=should_release,
        release_type=release_type,
        next_version=next_version,
        reason=reason.strip().strip('"').strip("'"),
    )


def apply_ai_release_guardrails(
    suggestion: AIReleaseSuggestion,
    current_version: str,
    unreleased_block: str,
) -> AIReleaseSuggestion:
    """
    Downgrade over-eager minor suggestions when the changelog only shows
    internal/tooling-oriented additions.
    """
    if not suggestion.should_release or suggestion.release_type != "minor":
        return suggestion

    section_entries = extract_section_entries(unreleased_block)
    added_entries = section_entries.get("Added", [])
    if len(added_entries) != 1:
        return suggestion

    added_entry = added_entries[0]
    if not looks_like_internal_tooling_change(added_entry):
        return suggestion

    return AIReleaseSuggestion(
        should_release=True,
        release_type="patch",
        next_version=bump_version(current_version, "patch"),
        reason=(
            "Downgraded from minor to patch because the only Added entry appears "
            "to be internal release/tooling work."
        ),
    )

def evaluate_release_with_ai(
    changelog_path: Path,
    ai_config: AIConfig,
) -> AIReleaseSuggestion:
    if not changelog_path.exists():
        return AIReleaseSuggestion(
            should_release=False,
            release_type=None,
            next_version=None,
            reason="CHANGELOG.md does not exist yet.",
        )

    changelog_text = changelog_path.read_text(encoding="utf-8")
    unreleased_block = extract_unreleased_block(changelog_text)

    if not unreleased_block.strip():
        return AIReleaseSuggestion(
            should_release=False,
            release_type=None,
            next_version=None,
            reason="No [Unreleased] section found.",
        )

    current_version = get_current_version(changelog_path.parent, changelog_text)
    prompt = build_release_evaluation_prompt(current_version, unreleased_block)

    debug_print(
        ai_config,
        f"release_ai_prompt_size={len(RELEASE_EVALUATION_SYSTEM_PROMPT) + len(prompt)}",
    )

    provider = get_ai_provider(ai_config)
    raw_response = provider.generate(
        system_prompt=RELEASE_EVALUATION_SYSTEM_PROMPT,
        user_prompt=prompt,
    )

    debug_print(ai_config, f"release_ai_response={repr(raw_response[:300])}")

    suggestion = parse_ai_release_response(raw_response, current_version)
    return apply_ai_release_guardrails(suggestion, current_version, unreleased_block)
