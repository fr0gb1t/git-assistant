from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_assistant.ai.base import AIConfig
from git_assistant.readme.service import evaluate_readme_update, normalize_readme_text


class ReadmeServiceTests(unittest.TestCase):
    def test_normalize_readme_text_ignores_trailing_blank_lines(self) -> None:
        self.assertEqual(normalize_readme_text("# Title\n"), normalize_readme_text("# Title\n\n"))

    def test_evaluate_readme_update_returns_no_update_for_unchanged_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            (cwd / "README.md").write_text("# Title\n\nBody\n", encoding="utf-8")
            (cwd / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n", encoding="utf-8")

            class FakeProvider:
                def generate(self, *, system_prompt: str, user_prompt: str) -> str:
                    return (
                        '{"should_update": true, '
                        '"reason": "Recent features added", '
                        '"updated_sections": ["Features"], '
                        '"updated_readme": "# Title\\n\\nBody\\n"}'
                    )

            with patch("git_assistant.readme.service.get_ai_provider", return_value=FakeProvider()):
                result = evaluate_readme_update(cwd, AIConfig())

            self.assertFalse(result.should_update)
            self.assertEqual(result.reason, "Proposed README content is unchanged.")
            self.assertEqual(result.updated_sections, [])


if __name__ == "__main__":
    unittest.main()
