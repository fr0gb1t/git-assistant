from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from git_assistant.cli import prompt_release_choice
from git_assistant.release.ai_evaluator import AIReleaseSuggestion
from git_assistant.release.evaluator import ReleaseSuggestion, StableReleaseHint


class ReleasePromptTests(unittest.TestCase):
    def test_prompt_release_choice_includes_first_stable_option(self) -> None:
        heuristic = ReleaseSuggestion(
            should_release=True,
            release_type="minor",
            next_version="0.8.0",
            reason="user-facing feature",
        )
        ai = AIReleaseSuggestion(
            should_release=True,
            release_type="minor",
            next_version="0.8.0",
            reason="user-facing feature",
        )
        hint = StableReleaseHint(
            should_suggest=True,
            version="1.0.0",
            reason="stable project",
            current_version="0.7.9",
            released_versions=5,
            released_entries=20,
        )

        with patch("builtins.input", return_value="2"):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                selected = prompt_release_choice(heuristic, ai, hint)
                output = buffer.getvalue()

        self.assertEqual(selected, "1.0.0")
        self.assertIn("[1] Release 0.8.0", output)
        self.assertIn("[2] Release 1.0.0 (first stable)", output)

    def test_prompt_release_choice_does_not_duplicate_existing_version(self) -> None:
        heuristic = ReleaseSuggestion(
            should_release=True,
            release_type="major",
            next_version="1.0.0",
            reason="breaking change",
        )
        ai = AIReleaseSuggestion(
            should_release=True,
            release_type="major",
            next_version="1.0.0",
            reason="breaking change",
        )
        hint = StableReleaseHint(
            should_suggest=True,
            version="1.0.0",
            reason="stable project",
            current_version="0.9.0",
            released_versions=6,
            released_entries=24,
        )

        with patch("builtins.input", return_value="1"):
            with io.StringIO() as buffer, redirect_stdout(buffer):
                selected = prompt_release_choice(heuristic, ai, hint)
                output = buffer.getvalue()

        self.assertEqual(selected, "1.0.0")
        self.assertEqual(output.count("Release 1.0.0"), 1)


if __name__ == "__main__":
    unittest.main()
