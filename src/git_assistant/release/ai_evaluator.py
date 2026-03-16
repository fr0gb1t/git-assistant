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
You are a release evaluation assistant.

Your task is to analyze the Unreleased changelog section and decide whether a new release should be suggested.

You must return ONLY valid JSON with this exact schema:

{
  "should_release": true,
  "release_type": "patch|minor|major|null",
  "reason": "short explanation"
}

Rules:
- Output JSON only.
- No markdown.
- No explanation outside JSON.

Reason rules:
- The reason must be one short sentence.
- Maximum 20 words.

Release decision rules:
- If there are meaningful changes listed in the Unreleased section, a release is usually expected.
- If the section contains only documentation, formatting, or extremely small maintenance changes, a release may be unnecessary.
- When in doubt between releasing or not releasing, prefer releasing with "patch".

Release type rules:
- Use "major" ONLY if the changelog clearly indicates breaking changes, incompatible behavior changes, explicit migration-required changes, or API-breaking changes.
- Do NOT choose "major" for normal feature additions, internal tooling changes, refactors, maintenance, or accumulated work.

- Use "minor" for meaningful new features or capabilities.
- If there are multiple Added entries or a clearly important new capability, prefer "minor" over "patch".

- Use "patch" for fixes, small refactors, maintenance work, documentation updates, tests, or small non-breaking improvements.

Changelog interpretation hints:
- Entries under "Added" usually indicate new functionality.
- Entries under "Fixed" usually indicate bug fixes.
- Entries under "Changed", "Improved", or "Refactored" usually indicate internal improvements.
- Entries under "Removed" or "Deprecated" may indicate breaking changes depending on context.

Examples:
- New release automation workflow added -> minor
- New CLI capability added -> minor
- Internal refactor only -> patch
- Bug fixes only -> patch
- Only documentation updates -> patch
- Breaking API change -> major
"""

def build_release_evaluation_prompt(
    current_version: str,
    unreleased_block: str,
) -> str:
    return f"""
Current version:
{current_version}

Repository context:
This is a software project under active development.
Evaluate release readiness based on the changelog entries and the meaning of the accumulated changes.

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