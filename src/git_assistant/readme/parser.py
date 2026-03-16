from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(slots=True)
class ReadmeUpdateResult:
    should_update: bool
    reason: str
    updated_sections: list[str]
    updated_readme: str


def parse_readme_update_response(raw_response: str) -> ReadmeUpdateResult:
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError as exc:
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