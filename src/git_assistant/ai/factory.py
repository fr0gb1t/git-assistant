from __future__ import annotations

from git_assistant.ai.base import AIConfig, AIProvider, AIProviderError
from git_assistant.ai.ollama import OllamaProvider


def get_ai_provider(config: AIConfig) -> AIProvider:
    """
    Return the configured AI provider implementation.
    """
    provider_name = config.provider.strip().lower()

    if provider_name == "ollama":
        return OllamaProvider(config)

    raise AIProviderError(f"Unsupported AI provider: {config.provider}")