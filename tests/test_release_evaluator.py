from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_assistant.release.evaluator import evaluate_release


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

    def _evaluate(self, changelog_text: str):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            changelog_path = cwd / "CHANGELOG.md"
            changelog_path.write_text(changelog_text, encoding="utf-8")

            with patch("git_assistant.release.evaluator.get_latest_git_tag", return_value="0.5.0"):
                return evaluate_release(cwd, changelog_path)


if __name__ == "__main__":
    unittest.main()
