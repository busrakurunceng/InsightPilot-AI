
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from app.backend.sql_executor import SQLExecutionResult
from app.backend.sql_generator import SQLGenerationResult
from app.backend.text_to_sql_service import (
    InsufficientContextError,
    SQLExecutionPipelineError,
    SQLGenerationPipelineError,
    SQLValidationPipelineError,
    TextToSQLService,
)


@pytest.fixture
def components():
    """Create a pipeline with mocked dependencies."""

    generator = MagicMock()
    executor = MagicMock()

    executor.allowed_tables = {"orders"}

    generator.generate.return_value = SQLGenerationResult(
        question="Toplam kaç sipariş var?",
        sql="SELECT COUNT(*) AS total_orders FROM orders",
        model="qwen2.5-coder:7b-instruct",
        selected_chunk_ids=["metric:total_orders"],
        dependency_chunk_ids=["table:orders"],
    )

    executor.execute.return_value = SQLExecutionResult(
        columns=["total_orders"],
        rows=[{"total_orders": 99441}],
        row_count=1,
        truncated=False,
    )

    service = TextToSQLService(
        generator=generator,
        executor=executor,
        allowed_tables={"orders"},
    )

    return service, generator, executor


def test_successful_pipeline(components):
    service, generator, executor = components

    result = service.run("Toplam kaç sipariş var?")

    assert result.question == "Toplam kaç sipariş var?"
    assert result.sql == (
        "SELECT COUNT(*) AS total_orders FROM orders"
    )
    assert result.model == "qwen2.5-coder:7b-instruct"
    assert result.columns == ["total_orders"]
    assert result.rows == [{"total_orders": 99441}]
    assert result.row_count == 1
    assert result.truncated is False

    assert result.selected_chunk_ids == [
        "metric:total_orders"
    ]
    assert result.dependency_chunk_ids == [
        "table:orders"
    ]

    generator.generate.assert_called_once_with(
        "Toplam kaç sipariş var?"
    )
    executor.execute.assert_called_once_with(
        result.sql
    )


def test_question_is_trimmed(components):
    service, generator, _ = components

    result = service.run(
        "  Toplam kaç sipariş var?  "
    )

    assert result.question == "Toplam kaç sipariş var?"

    generator.generate.assert_called_once_with(
        "Toplam kaç sipariş var?"
    )


@pytest.mark.parametrize(
    "question",
    ["", "   ", None, 123],
)
def test_invalid_question_rejected(
    components,
    question,
):
    service, generator, executor = components

    with pytest.raises(ValueError):
        service.run(question)

    generator.generate.assert_not_called()
    executor.execute.assert_not_called()


def test_insufficient_context_stops_execution(
    components,
):
    service, generator, executor = components

    generator.generate.return_value = replace(
        generator.generate.return_value,
        sql="INSUFFICIENT_CONTEXT",
    )

    with pytest.raises(InsufficientContextError):
        service.run("Bilinmeyen bir metrik?")

    executor.execute.assert_not_called()


def test_insufficient_context_case_insensitive(
    components,
):
    service, generator, executor = components

    generator.generate.return_value = replace(
        generator.generate.return_value,
        sql="  insufficient_context  ",
    )

    with pytest.raises(InsufficientContextError):
        service.run("Bilinmeyen bir metrik?")

    executor.execute.assert_not_called()


@pytest.mark.parametrize(
    "unsafe_sql",
    [
        "DELETE FROM orders",
        "DROP TABLE orders",
        "SELECT * FROM customers",
        "SELECT pg_sleep(10) FROM orders",
        "SELECT * FROM orders; SELECT * FROM orders",
    ],
)
def test_invalid_sql_stops_execution(
    components,
    unsafe_sql,
):
    service, generator, executor = components

    generator.generate.return_value = replace(
        generator.generate.return_value,
        sql=unsafe_sql,
    )

    with pytest.raises(SQLValidationPipelineError):
        service.run("Test sorusu")

    executor.execute.assert_not_called()


def test_generation_failure(components):
    service, generator, executor = components

    generator.generate.side_effect = RuntimeError(
        "LLM unavailable"
    )

    with pytest.raises(
        SQLGenerationPipelineError
    ) as exc_info:
        service.run("Toplam kaç sipariş var?")

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )

    executor.execute.assert_not_called()


def test_execution_failure(components):
    service, _, executor = components

    executor.execute.side_effect = RuntimeError(
        "Database unavailable"
    )

    with pytest.raises(
        SQLExecutionPipelineError
    ) as exc_info:
        service.run("Toplam kaç sipariş var?")

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )


def test_allowlist_mismatch_rejected():
    generator = MagicMock()
    executor = MagicMock()

    executor.allowed_tables = {"customers"}

    with pytest.raises(
        ValueError,
        match="allowlists must match",
    ):
        TextToSQLService(
            generator=generator,
            executor=executor,
            allowed_tables={"orders"},
        )


def test_empty_allowlist_rejected():
    with pytest.raises(
        ValueError,
        match="allowlist must not be empty",
    ):
        TextToSQLService(
            generator=MagicMock(),
            executor=MagicMock(),
            allowed_tables=set(),
        )


def test_result_truncation_metadata(components):
    service, _, executor = components

    executor.execute.return_value = SQLExecutionResult(
        columns=["order_id"],
        rows=[
            {"order_id": "A"},
            {"order_id": "B"},
        ],
        row_count=2,
        truncated=True,
    )

    result = service.run("Toplam kaç sipariş var?")

    assert result.row_count == 2
    assert result.truncated is True
    assert len(result.rows) == 2
