
"""Tests for Conversational BI UX state helpers."""

import json
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.backend.analytics_contract import AnalyticsResponse
from app.frontend.chat_state import (
    ChatMessage,
    add_assistant_message,
    add_user_message,
    build_error_message,
    export_chat_history,
)


def make_response():
    return AnalyticsResponse(
        question="How many orders?",
        sql="SELECT COUNT(*) AS total_orders FROM orders",
        columns=["total_orders"],
        rows=[{"total_orders": 99441}],
        row_count=1,
        truncated=False,
    )


def test_error_message_is_safe():
    message = build_error_message()

    assert "database" in message.lower()
    assert "ollama" in message.lower()
    assert "traceback" not in message.lower()


def test_empty_history_export():
    payload = json.loads(export_chat_history([]))

    assert payload["format_version"] == 1
    assert payload["messages"] == []


def test_user_message_export():
    history = [
        ChatMessage(
            role="user",
            content="How many orders?",
        )
    ]

    payload = json.loads(export_chat_history(history))

    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][0]["content"] == "How many orders?"
    assert payload["messages"][0]["response"] is None


def test_analytics_result_export():
    history = [
        ChatMessage(
            role="assistant",
            content="Analysis complete.",
            response=make_response(),
        )
    ]

    payload = json.loads(export_chat_history(history))

    result = payload["messages"][0]["response"]

    assert result["row_count"] == 1
    assert result["rows"][0]["total_orders"] == 99441
    assert result["columns"] == ["total_orders"]


def test_decimal_and_date_export():
    response = AnalyticsResponse(
        question="Revenue by day?",
        sql="SELECT purchase_date, revenue FROM sales",
        columns=["purchase_date", "revenue"],
        rows=[
            {
                "purchase_date": date(2026, 11, 10),
                "revenue": Decimal("1234.50"),
            }
        ],
        row_count=1,
        truncated=False,
    )

    history = [
        ChatMessage(
            role="assistant",
            content="Done.",
            response=response,
        )
    ]

    payload = json.loads(export_chat_history(history))
    row = payload["messages"][0]["response"]["rows"][0]

    assert row["purchase_date"] == "2026-11-10"
    assert row["revenue"] == "1234.50"


def test_datetime_export():
    response = AnalyticsResponse(
        question="Recent orders?",
        sql="SELECT created_at FROM orders",
        columns=["created_at"],
        rows=[
            {
                "created_at": datetime(2026, 11, 10, 9, 30),
            }
        ],
        row_count=1,
        truncated=False,
    )

    payload = json.loads(
        export_chat_history(
            [
                ChatMessage(
                    role="assistant",
                    content="Done.",
                    response=response,
                )
            ]
        )
    )

    assert (
        payload["messages"][0]["response"]["rows"][0]["created_at"]
        == "2026-11-10T09:30:00"
    )


def test_multiple_turns_preserve_order():
    history = []
    history = add_user_message(history, "Question one")
    history = add_assistant_message(history, "Answer one")
    history = add_user_message(history, "Question two")
    history = add_assistant_message(history, "Answer two")

    payload = json.loads(export_chat_history(history))

    assert [
        message["role"]
        for message in payload["messages"]
    ] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


def test_invalid_history_type():
    with pytest.raises(TypeError):
        export_chat_history("not a list")


def test_invalid_history_item():
    with pytest.raises(TypeError):
        export_chat_history([{"role": "user"}])


def test_error_response_has_no_analytics_data():
    history = add_assistant_message(
        [],
        build_error_message(),
    )

    payload = json.loads(export_chat_history(history))

    assert payload["messages"][0]["response"] is None


def test_export_does_not_mutate_history():
    history = [
        ChatMessage(
            role="assistant",
            content="Done.",
            response=make_response(),
        )
    ]

    original_message = history[0]

    export_chat_history(history)

    assert history[0] is original_message
    assert history[0].response.rows[0]["total_orders"] == 99441
