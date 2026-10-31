
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b-instruct"


class LLMClientError(Exception):
    """Raised when the local LLM request fails."""


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    total_duration_ns: int | None = None
    eval_count: int | None = None


class OllamaClient:
    """Minimal HTTP client for Ollama's local chat API."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL)
        ).rstrip("/")

        self.model = (
            model
            or os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        )

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.timeout = timeout

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> LLMResponse:
        if not messages:
            raise ValueError("messages must not be empty")

        for message in messages:
            if (
                message.get("role") not in
                {"system", "user", "assistant"}
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError("Invalid chat message")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        encoded_payload = json.dumps(payload).encode("utf-8")

        http_request = request.Request(
            url=f"{self.base_url}/api/chat",
            data=encoded_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(
                http_request,
                timeout=self.timeout,
            ) as response:
                result = json.load(response)

        except error.HTTPError as exc:
            raise LLMClientError(
                f"Ollama HTTP error: {exc.code}"
            ) from exc

        except error.URLError as exc:
            raise LLMClientError(
                f"Cannot connect to Ollama: {exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise LLMClientError(
                "Ollama request timed out"
            ) from exc

        except (ValueError, UnicodeError) as exc:
            raise LLMClientError(
                "Invalid JSON response from Ollama"
            ) from exc

        try:
            content = result["message"]["content"]
            response_model = result["model"]

            if not isinstance(content, str):
                raise TypeError("Response content must be text")

            if not isinstance(response_model, str):
                raise TypeError("Response model must be text")

            return LLMResponse(
                content=content,
                model=response_model,
                total_duration_ns=result.get("total_duration"),
                eval_count=result.get("eval_count"),
            )

        except (KeyError, TypeError) as exc:
            raise LLMClientError(
                "Unexpected Ollama response structure"
            ) from exc
