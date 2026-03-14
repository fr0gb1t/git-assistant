from __future__ import annotations

import requests

from git_assistant.ai.base import AIConfig, AIProvider, AIProviderError, debug_print


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

        raw_response = data.get("response", "")
        done_reason = data.get("done_reason", "unknown")
        has_context = "context" in data

        debug_print(self.config, f"provider={self.__class__.__name__}")
        debug_print(self.config, f"done_reason={done_reason}")
        debug_print(self.config, f"has_context={has_context}")

        if not isinstance(raw_response, str):
            raise AIProviderError(
                f"Ollama returned non-text response for model '{self.config.model}'. "
                f"Response field type: {type(raw_response).__name__}"
            )

        debug_print(self.config, f"response_length={len(raw_response)}")
        debug_print(
            self.config,
            f"response_preview={repr(raw_response[:200])}",
        )

        result = raw_response.strip()

        if not result:
            raise AIProviderError(
                f"Ollama returned no usable text for model '{self.config.model}' "
                f"(done_reason={done_reason}). "
                "This model may be incompatible with this text-only commit workflow. "
                "Try a text-oriented model like qwen2.5:14b or qwen2.5-coder."
            )

        return result