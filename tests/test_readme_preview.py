from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from git_assistant.readme.parser import ReadmeGenerateResult, ReadmeUpdateResult
from git_assistant.readme.preview import write_readme_preview_files
from git_assistant.readme.service import clear_readme_preview, edit_generated_readme, edit_readme_update


class ReadmePreviewTests(unittest.TestCase):
    def test_write_readme_preview_files_works_without_git_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)

            preview_path, diff_path = write_readme_preview_files(
                cwd,
                original_readme="# Title\nold\n",
                updated_readme="# Title\nnew\n",
            )

            self.assertTrue(preview_path.exists())
            self.assertTrue(diff_path.exists())
            self.assertIn("--- README.md", diff_path.read_text(encoding="utf-8"))

    def test_clear_readme_preview_removes_preview_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            write_readme_preview_files(cwd, original_readme="", updated_readme="# Title\n")

            clear_readme_preview(cwd)

            self.assertFalse((cwd / ".git-assistant-preview").exists())

    def test_edit_readme_update_applies_edited_preview_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            (cwd / "README.md").write_text("# Old\n", encoding="utf-8")
            result = ReadmeUpdateResult(
                should_update=True,
                reason="update",
                updated_sections=["Features"],
                updated_readme="# Proposed\n",
            )

            def fake_editor(path: Path) -> None:
                path.write_text("# Edited\n", encoding="utf-8")

            with patch("git_assistant.readme.service.open_preview_in_editor", side_effect=fake_editor):
                edit_readme_update(cwd, result)

            self.assertEqual((cwd / "README.md").read_text(encoding="utf-8"), "# Edited\n")

    def test_edit_generated_readme_applies_edited_preview_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            result = ReadmeGenerateResult(readme="# Proposed\n")

            def fake_editor(path: Path) -> None:
                path.write_text("# Edited Generated\n", encoding="utf-8")

            with patch("git_assistant.readme.service.open_preview_in_editor", side_effect=fake_editor):
                edit_generated_readme(cwd, result)

            self.assertEqual(
                (cwd / "README.md").read_text(encoding="utf-8"),
                "# Edited Generated\n",
            )


if __name__ == "__main__":
    unittest.main()
