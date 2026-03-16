from __future__ import annotations

from dataclasses import dataclass

from git_assistant.release.ai_evaluator import AIReleaseSuggestion
from git_assistant.release.evaluator import ReleaseSuggestion


@dataclass(slots=True)
class ReleaseDecision:
    should_apply: bool
    release_type: str | None
    next_version: str | None
    reason: str


def decide_auto_release(
    heuristic: ReleaseSuggestion,
    ai: AIReleaseSuggestion | None,
) -> ReleaseDecision:
    """
    Auto-apply a release only when both evaluators agree on the same release type.
    """
    if not heuristic.should_release:
        return ReleaseDecision(
            should_apply=False,
            release_type=None,
            next_version=None,
            reason="Heuristic evaluator does not suggest a release.",
        )

    if ai is None:
        return ReleaseDecision(
            should_apply=False,
            release_type=None,
            next_version=None,
            reason="AI evaluator is unavailable.",
        )

    if not ai.should_release:
        return ReleaseDecision(
            should_apply=False,
            release_type=None,
            next_version=None,
            reason="AI evaluator does not suggest a release.",
        )

    if heuristic.release_type != ai.release_type:
        return ReleaseDecision(
            should_apply=False,
            release_type=None,
            next_version=None,
            reason=(
                f"Evaluators disagree: heuristic={heuristic.release_type}, "
                f"ai={ai.release_type}"
            ),
        )

    return ReleaseDecision(
        should_apply=True,
        release_type=heuristic.release_type,
        next_version=heuristic.next_version,
        reason=f"Both evaluators agreed on a {heuristic.release_type} release.",
    )