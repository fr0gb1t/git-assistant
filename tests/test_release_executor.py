from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from git_assistant.release.executor import (
    PACKAGE_INIT_FILE,
    PYPROJECT_FILE,
    sync_project_version_files,
)


class ReleaseExecutorVersionSyncTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
