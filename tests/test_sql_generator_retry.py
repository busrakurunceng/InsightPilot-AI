
from unittest.mock import Mock, patch

import pytest

from app.backend.llm_client import LLMResponse
from app.backend.sql_generator import (
    SQLGenerationResult,
    SQLGenerator,
)


QUESTION = (
    "Her eyaletteki müşterilerin verdiği "
    "sipariş sayısını göster."
)

FIRST_SQL = "SELECT COUNT(*) AS total_orders FROM orders;"

CORRECTED_SQL = """
SELECT c.customer_state, COUNT(*) AS total_orders
FROM orders AS o
JOIN customers AS c
    ON o.customer_id = c.customer_id
GROUP BY c.customer_state;
"""


def make_previous(messages=None):
    if messages is None:
        messages = [
            {
                "role": "system",
                "content": "Generate PostgreSQL SQL.",
            },
            {
                "role": "user",
                "content": (
                    "Original business question and "
                    "retrieved schema context."
                ),
            },
        ]

    return SQLGenerationResult(
        question=QUESTION,
        sql=FIRST_SQL,
        model="test-model",
        selected_chunk_ids=["metric:total_orders"],
        dependency_chunk_ids=[
            "table:orders",
            "table:customers",
        ],
        messages=messages,
    )


def test_retry_reuses_original_messages():
    llm = Mock()
    llm.chat.return_value = LLMResponse(
        content=CORRECTED_SQL,
        model="test-model",
    )

    generator = SQLGenerator(llm_client=llm)
    previous = make_previous()

    with patch(
        "app.backend.sql_generator.search_schema"
    ) as retrieval:
        result = generator.regenerate(
            previous,
            issues=["Required dimension is not grouped."],
        )

    retrieval.assert_not_called()

    assert result.sql.strip() == CORRECTED_SQL.strip()
    assert result.question == QUESTION
    assert result.selected_chunk_ids == previous.selected_chunk_ids
    assert result.dependency_chunk_ids == previous.dependency_chunk_ids

    sent_messages = llm.chat.call_args.args[0]

    assert sent_messages[:2] == previous.messages
    assert sent_messages[2]["role"] == "assistant"
    assert sent_messages[2]["content"] == FIRST_SQL
    assert sent_messages[3]["role"] == "user"
    assert "Required dimension" in sent_messages[3]["content"]


def test_retry_does_not_mutate_original_messages():
    llm = Mock()
    llm.chat.return_value = LLMResponse(
        content=CORRECTED_SQL,
        model="test-model",
    )

    generator = SQLGenerator(llm_client=llm)
    previous = make_previous()

    original_messages = [
        dict(message)
        for message in previous.messages
    ]

    generator.regenerate(
        previous,
        issues=["Missing GROUP BY."],
    )

    assert previous.messages == original_messages
    assert len(previous.messages) == 2


def test_retry_rejects_missing_prompt_context():
    generator = SQLGenerator(llm_client=Mock())
    previous = make_previous(messages=[])

    with pytest.raises(
        ValueError,
        match="context is unavailable",
    ):
        generator.regenerate(
            previous,
            issues=["Missing GROUP BY."],
        )


@pytest.mark.parametrize(
    "issues",
    [
        [],
        [""],
        ["   "],
        ["Valid issue", ""],
        "Missing GROUP BY",
        None,
    ],
)
def test_retry_rejects_invalid_feedback(issues):
    generator = SQLGenerator(llm_client=Mock())

    with pytest.raises(ValueError):
        generator.regenerate(
            make_previous(),
            issues=issues,
        )


def test_retry_rejects_empty_llm_response():
    llm = Mock()
    llm.chat.return_value = LLMResponse(
        content="   ",
        model="test-model",
    )

    generator = SQLGenerator(llm_client=llm)

    with pytest.raises(
        ValueError,
        match="empty SQL retry response",
    ):
        generator.regenerate(
            make_previous(),
            issues=["Missing GROUP BY."],
        )


def test_retry_normalizes_single_sql_code_fence():
    llm = Mock()
    llm.chat.return_value = LLMResponse(
        content=f"```sql\n{CORRECTED_SQL.strip()}\n```",
        model="test-model",
    )

    generator = SQLGenerator(llm_client=llm)

    result = generator.regenerate(
        make_previous(),
        issues=["Missing GROUP BY."],
    )

    assert result.sql == CORRECTED_SQL.strip()


def test_initial_generation_preserves_prompt_context():
    llm = Mock()
    llm.chat.return_value = LLMResponse(
        content=FIRST_SQL,
        model="test-model",
    )

    selected = [
        {
            "chunk_id": "metric:total_orders",
            "chunk_type": "metric",
            "content": "COUNT(*)",
        }
    ]

    dependencies = [
        {
            "chunk_id": "table:orders",
            "chunk_type": "table",
            "content": "orders schema",
        }
    ]

    prompt_messages = [
        {
            "role": "system",
            "content": "System prompt",
        },
        {
            "role": "user",
            "content": "Schema context",
        },
    ]

    with (
        patch(
            "app.backend.sql_generator.search_schema",
            return_value=(selected, dependencies),
        ),
        patch(
            "app.backend.sql_generator.build_sql_messages",
            return_value=prompt_messages,
        ),
    ):
        generator = SQLGenerator(llm_client=llm)

        result = generator.generate(QUESTION)

    assert result.messages == prompt_messages
    assert result.selected_chunk_ids == [
        "metric:total_orders"
    ]
    assert result.dependency_chunk_ids == [
        "table:orders"
    ]


def test_retry_preserves_original_generation_metadata():
    llm = Mock()
    llm.chat.return_value = LLMResponse(
        content=CORRECTED_SQL,
        model="retry-model",
    )

    generator = SQLGenerator(llm_client=llm)
    previous = make_previous()

    result = generator.regenerate(
        previous,
        issues=["Missing GROUP BY."],
    )

    assert result.model == "retry-model"
    assert result.question == previous.question
    assert result.selected_chunk_ids == previous.selected_chunk_ids
    assert result.dependency_chunk_ids == previous.dependency_chunk_ids


def test_retry_uses_zero_temperature():
    llm = Mock()
    llm.chat.return_value = LLMResponse(
        content=CORRECTED_SQL,
        model="test-model",
    )

    generator = SQLGenerator(llm_client=llm)

    generator.regenerate(
        make_previous(),
        issues=["Missing GROUP BY."],
    )

    assert llm.chat.call_args.kwargs["temperature"] == 0.0
