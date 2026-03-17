from __future__ import annotations

import unittest

from git_assistant.release.ai_evaluator import (
    AIReleaseSuggestion,
    apply_ai_release_guardrails,
    build_first_stable_hint_prompt,
    build_release_evaluation_prompt,
    generate_first_stable_hint_reason,
)
from git_assistant.ai.base import AIConfig
from git_assistant.release.evaluator import StableReleaseHint


class AIReleaseEvaluatorTests(unittest.TestCase):
    def test_prompt_emphasizes_patch_for_internal_tooling(self) -> None:
        unreleased_block = """## [Unreleased]

### Added
- automate version number synchronization across pyproject.toml and package init file
"""
        prompt = build_release_evaluation_prompt("0.5.0", unreleased_block)

        self.assertIn("Prefer PATCH unless a new capability is clearly user-facing.", prompt)
        self.assertIn("Added entries that look internal/tooling-oriented:", prompt)
        self.assertIn(
            "- automate version number synchronization across pyproject.toml and package init file",
            prompt,
        )

    def test_guardrails_downgrade_internal_single_added_minor_to_patch(self) -> None:
        unreleased_block = """## [Unreleased]

### Added
- automate version number synchronization across pyproject.toml and package init file
"""
        suggestion = AIReleaseSuggestion(
            should_release=True,
            release_type="minor",
            next_version="0.6.0",
            reason="New capability introduced.",
        )

        adjusted = apply_ai_release_guardrails(suggestion, "0.5.0", unreleased_block)

        self.assertTrue(adjusted.should_release)
        self.assertEqual(adjusted.release_type, "patch")
        self.assertEqual(adjusted.next_version, "0.5.1")

    def test_guardrails_keep_minor_for_multiple_added_entries(self) -> None:
        unreleased_block = """## [Unreleased]

### Added
- add new interactive CLI mode
- generate initial README.md when none exists in a project
"""
        suggestion = AIReleaseSuggestion(
            should_release=True,
            release_type="minor",
            next_version="0.6.0",
            reason="Multiple user-facing features.",
        )

        adjusted = apply_ai_release_guardrails(suggestion, "0.5.0", unreleased_block)

        self.assertEqual(adjusted.release_type, "minor")
        self.assertEqual(adjusted.next_version, "0.6.0")

    def test_first_stable_hint_prompt_includes_history_context(self) -> None:
        hint = StableReleaseHint(
            should_suggest=True,
            version="1.0.0",
            reason="Heuristic says project may be ready.",
            current_version="0.8.5",
            released_versions=5,
            released_entries=20,
        )

        prompt = build_first_stable_hint_prompt(hint)

        self.assertIn("Current version: 0.8.5", prompt)
        self.assertIn("Suggested stable version: 1.0.0", prompt)
        self.assertIn("Zero.x releases found in changelog history: 5", prompt)
        self.assertIn("Released changelog entries found in zero.x history: 20", prompt)

    def test_generate_first_stable_hint_reason_normalizes_multiline_ai_output(self) -> None:
        hint = StableReleaseHint(
            should_suggest=True,
            version="1.0.0",
            reason="Heuristic says project may be ready.",
            current_version="0.8.5",
            released_versions=5,
            released_entries=20,
        )

        class FakeProvider:
            def generate(self, *, system_prompt: str, user_prompt: str) -> str:
                return "This project already has a meaningful 0.x release history.\nA 1.0.0 release now would mainly signal stability and product maturity."

        from unittest.mock import patch

        with patch("git_assistant.release.ai_evaluator.get_ai_provider", return_value=FakeProvider()):
            reason = generate_first_stable_hint_reason(hint, AIConfig())

        self.assertEqual(
            reason,
            "This project already has a meaningful 0.x release history. A 1.0.0 release now would mainly signal stability and product maturity.",
        )


if __name__ == "__main__":
    unittest.main()
