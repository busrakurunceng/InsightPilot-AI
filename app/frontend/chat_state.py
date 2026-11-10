
"""State management for the Conversational BI interface."""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from app.backend.analytics_contract import AnalyticsResponse


MessageRole = Literal["user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str
    response: AnalyticsResponse | None = None

    def __post_init__(self):
        if self.role not in ("user", "assistant"):
            raise ValueError("Invalid chat message role.")

        if not isinstance(self.content, str):
            raise TypeError("Message content must be a string.")

        if not self.content.strip():
            raise ValueError("Message content cannot be empty.")

        if self.response is not None:
            if self.role != "assistant":
                raise ValueError(
                    "Only assistant messages may contain analytics results."
                )

            if not isinstance(self.response, AnalyticsResponse):
                raise TypeError(
                    "Response must be an AnalyticsResponse."
                )


def add_user_message(
    history: list[ChatMessage],
    question: str,
) -> list[ChatMessage]:
    if not isinstance(history, list):
        raise TypeError("History must be a list.")

    return [
        *history,
        ChatMessage(role="user", content=question),
    ]


def add_assistant_message(
    history: list[ChatMessage],
    content: str,
    response: AnalyticsResponse | None = None,
) -> list[ChatMessage]:
    if not isinstance(history, list):
        raise TypeError("History must be a list.")

    return [
        *history,
        ChatMessage(
            role="assistant",
            content=content,
            response=response,
        ),
    ]


def build_error_message() -> str:
    """Return a safe, user-facing error message."""

    return (
        "The analysis could not be completed. "
        "Please check the database connection, "
        "Ollama availability, and application logs."
    )


def _json_default(value):
    """Convert supported non-JSON types for export."""

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    raise TypeError(
        f"Unsupported JSON value: {type(value).__name__}"
    )


def export_chat_history(
    history: list[ChatMessage],
) -> str:
    """Serialize chat history and analytics results to JSON."""

    if not isinstance(history, list):
        raise TypeError("History must be a list.")

    if not all(isinstance(item, ChatMessage) for item in history):
        raise TypeError(
            "History must contain ChatMessage objects."
        )

    payload = {
        "format_version": 1,
        "messages": [
            asdict(message)
            for message in history
        ],
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        default=_json_default,
        allow_nan=False,
    )
