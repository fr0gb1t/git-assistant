from __future__ import annotations

import unittest

from git_assistant.release.ai_evaluator import (
    AIReleaseSuggestion,
    apply_ai_release_guardrails,
    build_release_evaluation_prompt,
)


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


if __name__ == "__main__":
    unittest.main()
