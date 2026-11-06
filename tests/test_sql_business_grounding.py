
import json

from app.backend.sql_prompt_builder import (
    build_business_context,
    build_sql_messages,
    SYSTEM_PROMPT,
)


def make_chunk(chunk_id):
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_id.split(":")[0],
        "content": f"Schema for {chunk_id}",
        "metadata": {},
    }


def test_order_status_semantics():
    semantics = {
        "tables": {
            "orders": {
                "status_column": "order_status",
                "status_values": {
                    "delivered": {
                        "description": "Teslim edilmiş sipariş."
                    },
                    "canceled": {
                        "description": "İptal edilmiş sipariş."
                    },
                },
            },
        },
        "logical_relationships": [],
    }

    context = [make_chunk("table:orders")]

    result = build_business_context(context, semantics)

    statuses = result["tables"]["orders"]["status_values"]

    assert "delivered" in statuses
    assert "canceled" in statuses


def test_relationship_included_when_both_tables_present():
    semantics = {
        "tables": {
            "orders": {},
            "customers": {},
        },
        "logical_relationships": [
            {
                "left": "orders.customer_id",
                "right": "customers.customer_id",
            },
        ],
    }

    context = [
        make_chunk("table:orders"),
        make_chunk("table:customers"),
    ]

    result = build_business_context(context, semantics)

    assert len(result["logical_relationships"]) == 1


def test_relationship_excluded_when_table_missing():
    semantics = {
        "tables": {
            "orders": {},
            "customers": {},
        },
        "logical_relationships": [
            {
                "left": "orders.customer_id",
                "right": "customers.customer_id",
            },
        ],
    }

    result = build_business_context(
        [make_chunk("table:orders")],
        semantics,
    )

    assert result["logical_relationships"] == []


def test_unrelated_table_semantics_excluded():
    semantics = {
        "tables": {
            "orders": {"description": "Orders"},
            "customers": {"description": "Customers"},
        },
        "logical_relationships": [],
    }

    result = build_business_context(
        [make_chunk("table:customers")],
        semantics,
    )

    assert set(result["tables"]) == {"customers"}


def test_system_prompt_contains_grouping_rules():
    assert "GROUP BY" in SYSTEM_PROMPT
    assert "documented relationship" in SYSTEM_PROMPT
    assert "exact status values" in SYSTEM_PROMPT


def test_build_sql_messages_includes_business_context(
    monkeypatch,
):
    semantics = {
        "tables": {
            "orders": {
                "status_column": "order_status",
                "status_values": {
                    "canceled": {
                        "description": "İptal edilmiş sipariş."
                    },
                },
            },
        },
        "logical_relationships": [],
    }

    monkeypatch.setattr(
        "app.backend.sql_prompt_builder.load_semantics",
        lambda: semantics,
    )

    messages = build_sql_messages(
        "İptal edilmiş kaç sipariş var?",
        [make_chunk("table:orders")],
        [],
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    content = messages[1]["content"]

    assert '"canceled"' in content
    assert '"status_column": "order_status"' in content


def test_build_sql_messages_deduplicates_chunks(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.backend.sql_prompt_builder.load_semantics",
        lambda: {
            "tables": {"orders": {}},
            "logical_relationships": [],
        },
    )

    chunk = make_chunk("table:orders")

    messages = build_sql_messages(
        "Toplam kaç sipariş var?",
        [chunk],
        [chunk],
    )

    user_content = messages[1]["content"]
    context_text = user_content.split(
        "Database schema and retrieved context:\n",
        1,
    )[1].split(
        "\n\nRelevant business semantics:",
        1,
    )[0]

    context = json.loads(context_text)

    assert len(context) == 1
