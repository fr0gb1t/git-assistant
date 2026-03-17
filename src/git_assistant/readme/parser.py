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


def _strip_fences(raw: str) -> str:
    """Strip markdown code fences that LLMs sometimes add around JSON."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _fix_control_chars(raw: str) -> str:
    """
    Walk the string character by character.
    When inside a JSON string value, escape any raw control characters
    (newlines, tabs, etc.) that the model left unescaped.
    This handles the most common LLM JSON failure: literal newlines in values.
    """
    result = []
    in_string = False
    escaped = False

    for ch in raw:
        if escaped:
            result.append(ch)
            escaped = False
        elif ch == "\\":
            result.append(ch)
            escaped = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string:
            if ch == "\n":
                result.append("\\n")
            elif ch == "\r":
                result.append("\\r")
            elif ch == "\t":
                result.append("\\t")
            elif ord(ch) < 0x20:
                result.append(f"\\u{ord(ch):04x}")
            else:
                result.append(ch)
        else:
            result.append(ch)

    return "".join(result)


def _extract_large_field(raw: str, field_name: str) -> str | None:
    """
    Last-resort extractor for large text fields (updated_readme, readme).

    Strategy: find the field key, locate the opening quote of its value,
    then take everything up to the last quote in the response — which should
    be the closing quote of the field value if it is the last field in the JSON.

    This handles the case where the value contains unescaped double quotes
    that break structural JSON parsing.
    """
    key = f'"{field_name}"'
    key_idx = raw.rfind(key)
    if key_idx == -1:
        return None

    after_key = raw[key_idx + len(key):]
    # Find `: "` — the colon and opening quote of the value
    m = re.search(r':\s*"', after_key)
    if not m:
        return None

    content_start = key_idx + len(key) + m.end()
    content_tail = raw[content_start:]

    # The value ends at the last `"` in the response
    # (relies on the readme/updated_readme being the last JSON field)
    last_quote = content_tail.rfind('"')
    if last_quote == -1:
        return None

    value = content_tail[:last_quote]

    # Unescape already-escaped sequences so the caller gets clean text
    value = value.replace("\\n", "\n")
    value = value.replace("\\t", "\t")
    value = value.replace("\\r", "\r")
    value = value.replace('\\"', '"')
    value = value.replace("\\\\", "\\")

    return value


def _parse_json_robust(raw: str, large_field: str) -> dict:
    """
    Parse JSON from an LLM response using a progressive fallback strategy:
    1. Direct parse (handles well-formed responses — zero overhead).
    2. Strip markdown fences + direct parse.
    3. Strip fences + fix control characters + parse.
    4. Strip fences + fix control chars + extract large field manually.
    """
    raw = raw.strip()

    # 1. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Strip fences
    cleaned = _strip_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Fix control characters
    fixed = _fix_control_chars(cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 4. Manual field extraction — handles unescaped quotes inside the value
    field_value = _extract_large_field(cleaned, large_field)
    if field_value is None:
        raise ValueError(f"Could not extract '{large_field}' from response.")

    # Re-parse the JSON with the large field replaced by a safe placeholder,
    # then inject the extracted value back in.
    key = f'"{large_field}"'
    key_idx = cleaned.rfind(key)
    after_key = cleaned[key_idx + len(key):]
    m = re.search(r':\s*"', after_key)
    if not m:
        raise ValueError(f"Could not reconstruct JSON after extracting '{large_field}'.")

    val_start = key_idx + len(key) + m.end()
    last_quote = cleaned[val_start:].rfind('"')
    reconstructed = (
        cleaned[:val_start]
        + json.dumps(field_value)[1:-1]  # re-encode as safe JSON string content
        + cleaned[val_start + last_quote:]
    )

    try:
        return json.loads(reconstructed)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON reconstruction failed: {exc}") from exc


def parse_readme_update_response(raw_response: str) -> ReadmeUpdateResult:
    try:
        data = _parse_json_robust(raw_response, large_field="updated_readme")
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
        data = _parse_json_robust(raw_response, large_field="readme")
    except ValueError as exc:
        raise ValueError("README generator did not return valid JSON.") from exc

    readme = data.get("readme")

    if not isinstance(readme, str) or not readme.strip():
        raise ValueError("Invalid 'readme' value.")

    return ReadmeGenerateResult(readme=readme.strip())