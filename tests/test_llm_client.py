
import io
import json
from urllib import error
from unittest.mock import patch

import pytest

from app.backend.llm_client import (
    LLMClientError,
    OllamaClient,
)


class MockHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, *args, **kwargs):
        return json.dumps(self.payload).encode("utf-8")


def test_client_defaults():
    client = OllamaClient()

    assert client.base_url.startswith("http")
    assert client.model
    assert client.timeout > 0


def test_invalid_timeout():
    with pytest.raises(ValueError):
        OllamaClient(timeout=0)


def test_empty_messages():
    client = OllamaClient()

    with pytest.raises(ValueError):
        client.chat([])


def test_invalid_message():
    client = OllamaClient()

    with pytest.raises(ValueError):
        client.chat([{"role": "invalid", "content": "hello"}])


@patch("app.backend.llm_client.request.urlopen")
def test_successful_chat(mock_urlopen):
    mock_urlopen.return_value = MockHTTPResponse(
        {
            "model": "qwen2.5-coder:7b-instruct",
            "message": {
                "role": "assistant",
                "content": "CONNECTION_OK",
            },
            "total_duration": 2_000_000_000,
            "eval_count": 4,
        }
    )

    client = OllamaClient()

    response = client.chat(
        [{"role": "user", "content": "test"}]
    )

    assert response.content == "CONNECTION_OK"
    assert response.model == "qwen2.5-coder:7b-instruct"
    assert response.total_duration_ns == 2_000_000_000
    assert response.eval_count == 4

    request_object = mock_urlopen.call_args.args[0]
    payload = json.loads(request_object.data.decode("utf-8"))

    assert payload["stream"] is False
    assert payload["options"]["temperature"] == 0.0


@patch("app.backend.llm_client.request.urlopen")
def test_connection_failure(mock_urlopen):
    mock_urlopen.side_effect = error.URLError(
        "Connection refused"
    )

    client = OllamaClient()

    with pytest.raises(
        LLMClientError,
        match="Cannot connect",
    ):
        client.chat(
            [{"role": "user", "content": "test"}]
        )


@patch("app.backend.llm_client.request.urlopen")
def test_http_error(mock_urlopen):
    mock_urlopen.side_effect = error.HTTPError(
        url="http://127.0.0.1:11434/api/chat",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=io.BytesIO(b""),
    )

    client = OllamaClient()

    with pytest.raises(
        LLMClientError,
        match="404",
    ):
        client.chat(
            [{"role": "user", "content": "test"}]
        )


@patch("app.backend.llm_client.request.urlopen")
def test_invalid_response_structure(mock_urlopen):
    mock_urlopen.return_value = MockHTTPResponse(
        {"unexpected": "response"}
    )

    client = OllamaClient()

    with pytest.raises(
        LLMClientError,
        match="Unexpected Ollama response structure",
    ):
        client.chat(
            [{"role": "user", "content": "test"}]
        )
