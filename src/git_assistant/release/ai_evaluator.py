from __future__ import annotations

import json
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
Use when:
- new features appear under "Added"
- new capabilities or workflows were introduced
- significant internal tooling capability was added

If multiple entries appear under "Added", prefer MINOR.

PATCH
Use when:
- bug fixes
- refactors
- performance improvements
- documentation updates
- tests

If the Unreleased section contains mostly "Changed", "Fixed", "Refactor", or "Docs", prefer PATCH.

No Release
If the section contains only trivial maintenance or formatting.

Important rules:

- Prefer MINOR when new capabilities are introduced.
- Documentation alone does not justify MINOR.
- Multiple Added entries strongly suggest MINOR.

Output JSON only.
"""

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

def build_release_evaluation_prompt(
    current_version: str,
    unreleased_block: str,
) -> str:
    summary = build_unreleased_summary(unreleased_block)

    return f"""
Current version:
{current_version}

Repository context:
This is a software project under active development.
Evaluate release readiness based on the changelog entries and the meaning of the accumulated changes.

Important interpretation hint:
Entries under "Added" usually indicate new functionality and often justify a minor release.

Unreleased summary:
{summary}

Unreleased changelog section:
{unreleased_block}
"""


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

    return parse_ai_release_response(raw_response, current_version)