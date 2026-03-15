from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SemVer:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_version(version: str) -> SemVer:
    """
    Parse a semantic version string like '0.1.0'.
    """
    parts = version.strip().split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semantic version: {version}")

    try:
        major, minor, patch = (int(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"Invalid semantic version: {version}") from exc

    return SemVer(major=major, minor=minor, patch=patch)


def bump_version(current: str, release_type: str) -> str:
    """
    Return the next semantic version for the given release type.
    """
    version = parse_version(current)

    if release_type == "major":
        version.major += 1
        version.minor = 0
        version.patch = 0
    elif release_type == "minor":
        version.minor += 1
        version.patch = 0
    elif release_type == "patch":
        version.patch += 1
    else:
        raise ValueError(f"Unsupported release type: {release_type}")

    return str(version)