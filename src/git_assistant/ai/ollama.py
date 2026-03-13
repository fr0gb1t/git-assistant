from __future__ import annotations

import requests

from git_assistant.ai.base import AIConfig, AIProvider, AIProviderError


class OllamaProvider(AIProvider):
    """
    Ollama implementation of the AI provider interface.
    """

    def __init__(self, config: AIConfig) -> None:
        self.config = config

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        """
        Send a request to Ollama and return the generated response.
        """
        url = f"{self.config.host.rstrip('/')}/api/generate"

        payload = {
            "model": self.config.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.config.timeout,
            )
        except requests.RequestException as exc:
            raise AIProviderError(f"Failed to connect to Ollama: {exc}") from exc

        if response.status_code != 200:
            raise AIProviderError(
                f"Ollama returned HTTP {response.status_code}: {response.text}"
            )

        data = response.json()
        result = data.get("response", "").strip()

        if not result:
            raise AIProviderError("Ollama returned an empty response")

        return result