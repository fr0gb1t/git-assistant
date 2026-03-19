from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from git_assistant.ai.base import AIConfig

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


CONFIG_FILE_NAMES = [
    ".git-assistant.toml",
    "git-assistant.toml",
]


class ConfigError(RuntimeError):
    """Raised when configuration is invalid."""


@dataclass(slots=True)
class AppConfig:
    """
    Full application configuration.
    """

    ai: AIConfig
    release: "ReleaseConfig" = field(default_factory=lambda: ReleaseConfig())


@dataclass(slots=True)
class ReleaseVersionTarget:
    path: str
    pattern: str
    replacement: str


@dataclass(slots=True)
class ReleaseConfig:
    managed_files: list[str] = field(default_factory=lambda: ["CHANGELOG.md"])
    version_targets: list[ReleaseVersionTarget] = field(default_factory=list)


def find_config_file(start_dir: Path) -> Path | None:
    """
    Search for a config file in the given directory only.
    """
    for file_name in CONFIG_FILE_NAMES:
        candidate = start_dir / file_name
        if candidate.is_file():
            return candidate
    return None


def load_config_from_file(config_path: Path) -> AppConfig:
    """
    Load application config from a TOML file.
    """
    if tomllib is None:
        raise ConfigError("tomllib is not available in this Python version.")

    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except OSError as exc:
        raise ConfigError(f"Could not read config file: {config_path}") from exc
    except Exception as exc:
        raise ConfigError(f"Invalid TOML in config file: {config_path}") from exc

    return parse_config_dict(data)


def parse_config_dict(data: dict[str, Any]) -> AppConfig:
    """
    Parse a raw config dictionary into typed config objects.
    """
    ai_data = data.get("ai", {})

    if not isinstance(ai_data, dict):
        raise ConfigError("[ai] section must be a table/object.")

    provider = ai_data.get("provider", "ollama")
    model = ai_data.get("model", "qwen2.5:14b")
    host = ai_data.get("host", "http://127.0.0.1:11434")
    timeout = ai_data.get("timeout", 120)

    if not isinstance(provider, str):
        raise ConfigError("ai.provider must be a string.")
    if not isinstance(model, str):
        raise ConfigError("ai.model must be a string.")
    if not isinstance(host, str):
        raise ConfigError("ai.host must be a string.")
    if not isinstance(timeout, int):
        raise ConfigError("ai.timeout must be an integer.")

    release_data = data.get("release", {})
    if not isinstance(release_data, dict):
        raise ConfigError("[release] section must be a table/object.")

    managed_files = release_data.get("managed_files", ["CHANGELOG.md"])
    if not isinstance(managed_files, list) or not all(
        isinstance(item, str) for item in managed_files
    ):
        raise ConfigError("release.managed_files must be an array of strings.")

    version_targets_data = release_data.get("version_targets", [])
    if not isinstance(version_targets_data, list):
        raise ConfigError("release.version_targets must be an array of tables.")

    version_targets: list[ReleaseVersionTarget] = []
    for index, item in enumerate(version_targets_data):
        if not isinstance(item, dict):
            raise ConfigError(
                f"release.version_targets[{index}] must be a table/object."
            )

        path = item.get("path")
        pattern = item.get("pattern")
        replacement = item.get("replacement")

        if not isinstance(path, str) or not path:
            raise ConfigError(
                f"release.version_targets[{index}].path must be a non-empty string."
            )
        if not isinstance(pattern, str) or not pattern:
            raise ConfigError(
                f"release.version_targets[{index}].pattern must be a non-empty string."
            )
        if not isinstance(replacement, str) or not replacement:
            raise ConfigError(
                f"release.version_targets[{index}].replacement must be a non-empty string."
            )

        version_targets.append(
            ReleaseVersionTarget(
                path=path,
                pattern=pattern,
                replacement=replacement,
            )
        )

    return AppConfig(
        ai=AIConfig(
            provider=provider,
            model=model,
            host=host,
            timeout=timeout,
        ),
        release=ReleaseConfig(
            managed_files=list(managed_files),
            version_targets=version_targets,
        ),
    )


def load_app_config(start_dir: Path) -> AppConfig:
    """
    Load app config from the current directory if present.
    Otherwise return default config.
    """
    config_path = find_config_file(start_dir)

    if config_path is None:
        return AppConfig(ai=AIConfig())

    return load_config_from_file(config_path)
