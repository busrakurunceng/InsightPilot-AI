
import pytest

from app.backend.sql_prompt_builder import build_sql_messages


def make_chunk(chunk_id, chunk_type, content):
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_type,
        "content": content,
        "metadata": {},
    }


def test_build_messages_success():
    selected = [
        make_chunk(
            "metric:total_orders",
            "metric",
            "Total number of orders",
        )
    ]

    dependencies = [
        make_chunk(
            "table:orders",
            "table",
            "Table orders with column order_id",
        )
    ]

    messages = build_sql_messages(
        "Toplam kaç sipariş var?",
        selected,
        dependencies,
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    assert "Toplam kaç sipariş var?" in messages[1]["content"]
    assert "metric:total_orders" in messages[1]["content"]
    assert "table:orders" in messages[1]["content"]


def test_duplicate_chunks_are_removed():
    chunk = make_chunk(
        "table:orders",
        "table",
        "Orders table",
    )

    messages = build_sql_messages(
        "Kaç sipariş var?",
        [chunk],
        [chunk],
    )

    assert messages[1]["content"].count(
        '"chunk_id": "table:orders"'
    ) == 1


def test_empty_question_rejected():
    with pytest.raises(ValueError):
        build_sql_messages(
            "   ",
            [make_chunk("table:orders", "table", "Orders")],
            [],
        )


def test_empty_context_rejected():
    with pytest.raises(ValueError):
        build_sql_messages(
            "Toplam kaç sipariş var?",
            [],
            [],
        )


def test_context_contains_business_rules():
    selected = [
        make_chunk(
            "metric:delivered_orders",
            "metric",
            "Count orders where order_status = delivered",
        )
    ]

    messages = build_sql_messages(
        "Teslim edilen sipariş sayısı kaç?",
        selected,
        [],
    )

    assert "order_status = delivered" in messages[1]["content"]


def test_system_prompt_restricts_modifications():
    messages = build_sql_messages(
        "Kaç sipariş var?",
        [make_chunk("table:orders", "table", "Orders")],
        [],
    )

    system_prompt = messages[0]["content"]

    assert "SELECT" in system_prompt
    assert "DELETE" in system_prompt
    assert "INSUFFICIENT_CONTEXT" in system_prompt
