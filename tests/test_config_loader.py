from __future__ import annotations

import unittest

from git_assistant.config.loader import ConfigError, parse_config_dict


class ConfigLoaderTests(unittest.TestCase):
    def test_parse_config_dict_includes_release_version_targets(self) -> None:
        config = parse_config_dict(
            {
                "ai": {
                    "provider": "ollama",
                    "model": "qwen2.5:14b",
                    "host": "http://127.0.0.1:11434",
                    "timeout": 120,
                },
                "release": {
                    "managed_files": ["CHANGELOG.md", "pyproject.toml"],
                    "version_targets": [
                        {
                            "path": "pyproject.toml",
                            "pattern": '^(version = )"[^"]+"$',
                            "replacement": '\\g<1>"{version}"',
                        }
                    ],
                },
            }
        )

        self.assertEqual(config.release.managed_files, ["CHANGELOG.md", "pyproject.toml"])
        self.assertEqual(len(config.release.version_targets), 1)
        self.assertEqual(config.release.version_targets[0].path, "pyproject.toml")

    def test_parse_config_dict_defaults_release_to_changelog_only(self) -> None:
        config = parse_config_dict({})

        self.assertEqual(config.release.managed_files, ["CHANGELOG.md"])
        self.assertEqual(config.release.version_targets, [])

    def test_parse_config_dict_rejects_invalid_release_targets(self) -> None:
        with self.assertRaises(ConfigError):
            parse_config_dict(
                {
                    "release": {
                        "version_targets": [
                            {
                                "path": "pyproject.toml",
                                "pattern": '^(version = )"[^"]+"$',
                            }
                        ]
                    }
                }
            )


if __name__ == "__main__":
    unittest.main()
