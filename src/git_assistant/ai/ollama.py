from __future__ import annotations

import requests


class OllamaError(RuntimeError):
    """Raised when the Ollama API fails."""


def generate(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str = "qwen2.5:14b",
    host: str = "http://127.0.0.1:11434",
    timeout: int = 120,
) -> str:
    """
    Send a request to Ollama and return the generated response.
    """

    url = f"{host}/api/generate"

    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise OllamaError(f"Failed to connect to Ollama: {exc}") from exc

    if response.status_code != 200:
        raise OllamaError(
            f"Ollama returned HTTP {response.status_code}: {response.text}"
        )

    data = response.json()

    result = data.get("response", "").strip()

    if not result:
        raise OllamaError("Ollama returned an empty response")

    return result
