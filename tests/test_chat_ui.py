
"""Tests for Conversational BI chat state."""

import pytest

from app.backend.analytics_contract import AnalyticsResponse
from app.frontend.chat_state import (
    ChatMessage,
    add_assistant_message,
    add_user_message,
)


def make_response():
    return AnalyticsResponse(
        question="How many orders?",
        sql="SELECT COUNT(*) AS total_orders FROM orders",
        columns=["total_orders"],
        rows=[{"total_orders": 100}],
        row_count=1,
        truncated=False,
    )


def test_user_message_creation():
    message = ChatMessage(
        role="user",
        content="How many orders?",
    )

    assert message.role == "user"
    assert message.response is None


def test_assistant_message_creation():
    message = ChatMessage(
        role="assistant",
        content="Analysis complete.",
        response=make_response(),
    )

    assert message.role == "assistant"
    assert message.response is not None


def test_add_user_message():
    history = []

    updated = add_user_message(
        history,
        "How many orders?",
    )

    assert len(updated) == 1
    assert updated[0].role == "user"


def test_add_assistant_message():
    history = [
        ChatMessage(
            role="user",
            content="How many orders?",
        )
    ]

    updated = add_assistant_message(
        history,
        "Analysis complete.",
        response=make_response(),
    )

    assert len(updated) == 2
    assert updated[1].role == "assistant"


def test_history_is_not_mutated():
    history = []

    updated = add_user_message(
        history,
        "Show revenue.",
    )

    assert history == []
    assert len(updated) == 1


def test_multiple_conversation_turns():
    history = []

    history = add_user_message(
        history,
        "Question one",
    )

    history = add_assistant_message(
        history,
        "Answer one",
    )

    history = add_user_message(
        history,
        "Question two",
    )

    history = add_assistant_message(
        history,
        "Answer two",
    )

    assert len(history) == 4

    assert [message.role for message in history] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_empty_message_rejected():
    with pytest.raises(ValueError):
        ChatMessage(
            role="user",
            content="",
        )


def test_whitespace_message_rejected():
    with pytest.raises(ValueError):
        ChatMessage(
            role="assistant",
            content="   ",
        )


def test_invalid_role_rejected():
    with pytest.raises(ValueError):
        ChatMessage(
            role="system",
            content="System message",
        )


def test_user_cannot_attach_analytics_response():
    with pytest.raises(ValueError):
        ChatMessage(
            role="user",
            content="Question",
            response=make_response(),
        )


def test_invalid_response_type_rejected():
    with pytest.raises(TypeError):
        ChatMessage(
            role="assistant",
            content="Answer",
            response={"rows": []},
        )


def test_invalid_history_rejected():
    with pytest.raises(TypeError):
        add_user_message(
            None,
            "Question",
        )


def test_invalid_assistant_history_rejected():
    with pytest.raises(TypeError):
        add_assistant_message(
            None,
            "Answer",
        )


def test_invalid_message_content_type():
    with pytest.raises(TypeError):
        ChatMessage(
            role="user",
            content=123,
        )
