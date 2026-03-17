from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_assistant.release.evaluator import evaluate_first_stable_hint, evaluate_release


class ReleaseEvaluatorTests(unittest.TestCase):
    def test_internal_added_entry_is_patch(self) -> None:
        changelog_text = """# Changelog

## [Unreleased]

### Added
- automate version number synchronization across pyproject.toml and package init file

## [0.5.0] - 2026-03-17
"""
        suggestion = self._evaluate(changelog_text)

        self.assertTrue(suggestion.should_release)
        self.assertEqual(suggestion.release_type, "patch")
        self.assertEqual(suggestion.next_version, "0.5.1")

    def test_user_facing_added_entry_is_minor(self) -> None:
        changelog_text = """# Changelog

## [Unreleased]

### Added
- add new interactive CLI mode for release review

## [0.5.0] - 2026-03-17
"""
        suggestion = self._evaluate(changelog_text)

        self.assertTrue(suggestion.should_release)
        self.assertEqual(suggestion.release_type, "minor")
        self.assertEqual(suggestion.next_version, "0.6.0")

    def test_breaking_change_is_major(self) -> None:
        changelog_text = """# Changelog

## [Unreleased]

### Changed
- breaking: remove legacy release workflow and require migration

## [0.5.0] - 2026-03-17
"""
        suggestion = self._evaluate(changelog_text)

        self.assertTrue(suggestion.should_release)
        self.assertEqual(suggestion.release_type, "major")
        self.assertEqual(suggestion.next_version, "1.0.0")

    def test_first_stable_hint_requires_mature_zero_x_history(self) -> None:
        changelog_text = """# Changelog

## [Unreleased]

### Fixed
- improve dry-run cleanup

## [0.8.5] - 2026-03-17

### Added
- add README preview editing
- add manual release flag

### Fixed
- fix dry-run cleanup
- fix release prompt handling

## [0.8.0] - 2026-03-10

### Added
- add release preview flow
- add version sync automation

### Fixed
- fix changelog parsing
- fix README preview opening

## [0.7.5] - 2026-03-05

### Added
- add AI release evaluator guardrails
- add heuristics for internal tooling changes

### Fixed
- fix selected files output
- fix commit message editing

## [0.7.2] - 2026-02-27

### Added
- add release executor version sync
- add dry-run README handling

### Fixed
- fix README no-op updates
- fix release consensus menu

## [0.7.0] - 2026-02-20

### Added
- add README preview workflow
- add safer restore logic

### Fixed
- fix git status parsing
- fix preview cleanup
"""
        hint = self._evaluate_first_stable_hint(changelog_text, current_version="0.8.5")

        self.assertTrue(hint.should_suggest)
        self.assertEqual(hint.version, "1.0.0")

    def test_first_stable_hint_is_suppressed_for_early_zero_x_versions(self) -> None:
        changelog_text = """# Changelog

## [Unreleased]

### Fixed
- improve parser

## [0.3.2] - 2026-03-17

### Added
- add initial changelog support

### Fixed
- fix git add flow
"""
        hint = self._evaluate_first_stable_hint(changelog_text, current_version="0.3.2")

        self.assertFalse(hint.should_suggest)

    def _evaluate(self, changelog_text: str):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            changelog_path = cwd / "CHANGELOG.md"
            changelog_path.write_text(changelog_text, encoding="utf-8")

            with patch("git_assistant.release.evaluator.get_latest_git_tag", return_value="0.5.0"):
                return evaluate_release(cwd, changelog_path)

    def _evaluate_first_stable_hint(self, changelog_text: str, current_version: str):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            changelog_path = cwd / "CHANGELOG.md"
            changelog_path.write_text(changelog_text, encoding="utf-8")

            with patch(
                "git_assistant.release.evaluator.get_latest_git_tag",
                return_value=current_version,
            ):
                return evaluate_first_stable_hint(cwd, changelog_path)


if __name__ == "__main__":
    unittest.main()
