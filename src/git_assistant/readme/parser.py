from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(slots=True)
class ReadmeUpdateResult:
    should_update: bool
    reason: str
    updated_sections: list[str]
    updated_readme: str


@dataclass(slots=True)
class ReadmeGenerateResult:
    readme: str


def _sanitize_json_response(raw: str) -> str:
    """
    Clean common LLM JSON output issues before parsing:
    - Strip markdown code fences (```json ... ```)
    - Fix unescaped control characters inside JSON string values
    """
    # Strip markdown code fences
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    # Fix unescaped control characters inside string values.
    # Strategy: find every JSON string value and re-escape any
    # raw control characters (tabs, newlines, carriage returns, etc.)
    # that the model left unescaped.
    def escape_string_content(m: re.Match) -> str:
        inner = m.group(1)
        # Replace raw control characters with their JSON escape sequences
        inner = inner.replace("\r\n", "\\n")
        inner = inner.replace("\r", "\\n")
        inner = inner.replace("\n", "\\n")
        inner = inner.replace("\t", "\\t")
        # Remove other control characters (0x00–0x1f except already escaped)
        inner = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", inner)
        return f'"{inner}"'

    # Match JSON strings: "..." handling escaped quotes inside
    raw = re.sub(r'"((?:[^"\\]|\\.)*)"', escape_string_content, raw)

    return raw


def _parse_json_robust(raw_response: str) -> dict:
    """
    Parse JSON from an LLM response, applying sanitization if the
    first parse attempt fails.
    """
    raw = raw_response.strip()

    # First attempt: direct parse (handles well-formed responses)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Second attempt: sanitize then parse
    sanitized = _sanitize_json_response(raw)
    try:
        return json.loads(sanitized)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Could not parse JSON after sanitization: {exc}") from exc


def parse_readme_update_response(raw_response: str) -> ReadmeUpdateResult:
    try:
        data = _parse_json_robust(raw_response)
    except ValueError as exc:
        raise ValueError("README updater did not return valid JSON.") from exc

    should_update = data.get("should_update")
    reason = data.get("reason")
    updated_sections = data.get("updated_sections")
    updated_readme = data.get("updated_readme")

    if not isinstance(should_update, bool):
        raise ValueError("Invalid 'should_update' value.")

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Invalid 'reason' value.")

    if not isinstance(updated_sections, list) or not all(
        isinstance(item, str) for item in updated_sections
    ):
        raise ValueError("Invalid 'updated_sections' value.")

    if not isinstance(updated_readme, str) or not updated_readme.strip():
        raise ValueError("Invalid 'updated_readme' value.")

    return ReadmeUpdateResult(
        should_update=should_update,
        reason=reason.strip(),
        updated_sections=[item.strip() for item in updated_sections if item.strip()],
        updated_readme=updated_readme,
    )


def parse_readme_generate_response(raw_response: str) -> ReadmeGenerateResult:
    try:
        data = _parse_json_robust(raw_response)
    except ValueError as exc:
        raise ValueError("README generator did not return valid JSON.") from exc

    readme = data.get("readme")

    if not isinstance(readme, str) or not readme.strip():
        raise ValueError("Invalid 'readme' value.")

    return ReadmeGenerateResult(readme=readme.strip())