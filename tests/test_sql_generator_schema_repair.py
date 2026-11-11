
from unittest.mock import Mock

import pytest

from app.backend.sql_generator import (
    SQLGenerationResult,
    SQLGenerator,
)


@pytest.fixture
def setup_generator():
    llm = Mock()
    llm.chat.return_value = Mock(
        content=(
            "SELECT customer_state "
            "FROM customers"
        ),
        model="test-model",
    )

    generator = SQLGenerator(llm_client=llm)

    previous = SQLGenerationResult(
        question="Müşterileri eyaletlerine göre göster",
        sql="SELECT state FROM customers",
        model="test-model",
        selected_chunk_ids=["table:customers"],
        dependency_chunk_ids=[],
        messages=[
            {
                "role": "system",
                "content": (
                    "The customers table contains "
                    "customer_state."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Müşterileri eyaletlerine göre göster"
                ),
            },
        ],
    )

    return generator, llm, previous


def test_schema_repair_uses_original_context(setup_generator):
    generator, llm, previous = setup_generator

    result = generator.regenerate(
        previous,
        issues=["Invalid database column reference."],
        validation_type="schema",
    )

    assert result.sql == (
        "SELECT customer_state FROM customers"
    )

    messages = llm.chat.call_args.args[0]

    assert messages[0] == previous.messages[0]
    assert messages[1] == previous.messages[1]
    assert messages[2] == {
        "role": "assistant",
        "content": previous.sql,
    }

    assert "PostgreSQL schema" in messages[3]["content"]
    assert "GROUP BY" not in messages[3]["content"]
    assert "Invalid database column reference." in (
        messages[3]["content"]
    )

    llm.chat.assert_called_once()
    assert llm.chat.call_args.kwargs["temperature"] == 0.0


def test_schema_repair_preserves_metadata(setup_generator):
    generator, _, previous = setup_generator

    result = generator.regenerate(
        previous,
        issues=["Invalid database column reference."],
        validation_type="schema",
    )

    assert result.question == previous.question
    assert result.selected_chunk_ids == (
        previous.selected_chunk_ids
    )
    assert result.dependency_chunk_ids == (
        previous.dependency_chunk_ids
    )
    assert result.model == "test-model"
    assert result.messages == previous.messages


def test_schema_repair_rejects_unknown_validation_type(
    setup_generator,
):
    generator, llm, previous = setup_generator

    with pytest.raises(
        ValueError,
        match="Unsupported validation type",
    ):
        generator.regenerate(
            previous,
            issues=["Invalid column"],
            validation_type="unknown",
        )

    llm.chat.assert_not_called()


def test_schema_repair_rejects_empty_issues(setup_generator):
    generator, llm, previous = setup_generator

    with pytest.raises(
        ValueError,
        match="Validation issues",
    ):
        generator.regenerate(
            previous,
            issues=[],
            validation_type="schema",
        )

    llm.chat.assert_not_called()


def test_schema_repair_rejects_missing_context(
    setup_generator,
):
    generator, llm, previous = setup_generator

    previous_without_context = SQLGenerationResult(
        question=previous.question,
        sql=previous.sql,
        model=previous.model,
        selected_chunk_ids=previous.selected_chunk_ids,
        dependency_chunk_ids=previous.dependency_chunk_ids,
        messages=[],
    )

    with pytest.raises(
        ValueError,
        match="Original SQL prompt context",
    ):
        generator.regenerate(
            previous_without_context,
            issues=["Invalid column"],
            validation_type="schema",
        )

    llm.chat.assert_not_called()


def test_schema_repair_normalizes_markdown(
    setup_generator,
):
    generator, llm, previous = setup_generator

    llm.chat.return_value.content = (
        "```sql\n"
        "SELECT customer_state FROM customers\n"
        "```"
    )

    result = generator.regenerate(
        previous,
        issues=["Invalid column"],
        validation_type="schema",
    )

    assert result.sql == (
        "SELECT customer_state FROM customers"
    )
