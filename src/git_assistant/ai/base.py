from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AIProviderError(RuntimeError):
    """Raised when an AI provider fails."""


class AIProvider(Protocol):
    """
    Common interface for text generation providers.
    """

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """
        Generate text from the given prompts.
        """
        ...


@dataclass(slots=True)
class AIConfig:
    """
    Runtime configuration for the AI provider layer.
    """

    provider: str = "ollama"
    model: str = "qwen2.5:14b"
    host: str = "http://127.0.0.1:11434"
    timeout: int = 120
    debug: bool = False

def debug_print(config: AIConfig, message: str) -> None:
    """
    Print debug information if debug mode is enabled.
    """
    if config.debug:
        print(f"[DEBUG] {message}")