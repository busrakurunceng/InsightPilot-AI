
"""Pure helpers for Conversational BI chat history."""

from dataclasses import dataclass
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
    """Return a new history containing the user's question."""

    if not isinstance(history, list):
        raise TypeError("History must be a list.")

    return [
        *history,
        ChatMessage(
            role="user",
            content=question,
        ),
    ]


def add_assistant_message(
    history: list[ChatMessage],
    content: str,
    response: AnalyticsResponse | None = None,
) -> list[ChatMessage]:
    """Return a new history containing an assistant message."""

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
