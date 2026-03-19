from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from git_assistant.release.executor import (
    PACKAGE_INIT_FILE,
    PYPROJECT_FILE,
    get_release_managed_files,
    normalize_release_version,
    sync_project_version_files,
)


class ReleaseExecutorVersionSyncTests(unittest.TestCase):
    def test_normalize_release_version_accepts_plain_and_prefixed_versions(self) -> None:
        self.assertEqual(normalize_release_version("0.5.0"), "0.5.0")
        self.assertEqual(normalize_release_version("v0.5.0"), "0.5.0")

    def test_normalize_release_version_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            normalize_release_version("release-0.5.0")

    def test_sync_project_version_files_updates_pyproject_and_package_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            pyproject_path = cwd / PYPROJECT_FILE
            package_init_path = cwd / PACKAGE_INIT_FILE
            package_init_path.parent.mkdir(parents=True, exist_ok=True)

            pyproject_path.write_text(
                '[project]\nname = "git-assistant"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )
            package_init_path.write_text('__version__ = "0.1.0"\n', encoding="utf-8")

            sync_project_version_files(cwd, version="0.5.0")

            self.assertIn('version = "0.5.0"', pyproject_path.read_text(encoding="utf-8"))
            self.assertEqual(
                package_init_path.read_text(encoding="utf-8"),
                '__version__ = "0.5.0"\n',
            )

    def test_sync_project_version_files_skips_missing_optional_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)

            sync_project_version_files(cwd, version="0.5.0")

            self.assertFalse((cwd / PYPROJECT_FILE).exists())
            self.assertFalse((cwd / PACKAGE_INIT_FILE).exists())

    def test_get_release_managed_files_only_includes_existing_optional_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cwd = Path(tmp_dir)
            (cwd / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
            (cwd / PYPROJECT_FILE).write_text(
                '[project]\nname = "sample"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

            managed_files = get_release_managed_files(cwd)

            self.assertEqual(
                managed_files,
                ["CHANGELOG.md", PYPROJECT_FILE],
            )


if __name__ == "__main__":
    unittest.main()
