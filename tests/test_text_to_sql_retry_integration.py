from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.usefixtures("mock_schema_validation")

from app.backend.sql_executor import SQLExecutionResult
from app.backend.sql_generator import SQLGenerationResult
from app.backend.text_to_sql_service import (
    OLIST_ALLOWED_TABLES,
    InsufficientContextError,
    SQLGenerationPipelineError,
    SQLSemanticValidationPipelineError,
    SQLValidationPipelineError,
    TextToSQLService,
)

QUESTION = (
    "Her eyaletteki müşterilerin verdiği "
    "sipariş sayısını göster."
)

INVALID_SQL = "SELECT COUNT(*) AS total_orders FROM orders;"

VALID_SQL = """
SELECT c.customer_state, COUNT(*) AS total_orders
FROM orders AS o
JOIN customers AS c ON o.customer_id = c.customer_id
GROUP BY c.customer_state;
"""


def make_generation(sql):
    return SQLGenerationResult(
        question=QUESTION,
        sql=sql,
        model="test-model",
        selected_chunk_ids=["metric:total_orders"],
        dependency_chunk_ids=["table:orders", "table:customers"],
        messages=[
            {"role": "system", "content": "SQL assistant"},
            {"role": "user", "content": "Original schema context"},
        ],
    )


def make_service(initial_sql, retry_sql=VALID_SQL):
    generator = Mock()
    generator.generate.return_value = make_generation(initial_sql)
    generator.regenerate.return_value = make_generation(retry_sql)

    executor = Mock()
    executor.allowed_tables = set(OLIST_ALLOWED_TABLES)
    executor.execute.return_value = SQLExecutionResult(
        columns=["customer_state", "total_orders"],
        rows=[{"customer_state": "SP", "total_orders": 100}],
        row_count=1,
        truncated=False,
    )

    return (
        TextToSQLService(generator=generator, executor=executor),
        generator,
        executor,
    )


def test_invalid_grouping_triggers_single_retry():
    service, generator, executor = make_service(INVALID_SQL)

    result = service.run(QUESTION)

    assert result.sql.strip() == VALID_SQL.strip()
    assert result.rows[0]["customer_state"] == "SP"
    generator.generate.assert_called_once_with(QUESTION)
    generator.regenerate.assert_called_once()
    executor.execute.assert_called_once()


def test_correct_sql_does_not_trigger_retry():
    service, generator, executor = make_service(VALID_SQL)

    service.run(QUESTION)

    generator.regenerate.assert_not_called()
    executor.execute.assert_called_once()


def test_retry_receives_semantic_feedback():
    service, generator, _ = make_service(INVALID_SQL)

    service.run(QUESTION)

    kwargs = generator.regenerate.call_args.kwargs
    assert kwargs["issues"]
    assert any("GROUP BY" in issue for issue in kwargs["issues"])


def test_second_semantic_failure_stops_execution():
    service, generator, executor = make_service(
        INVALID_SQL,
        retry_sql=INVALID_SQL,
    )

    with pytest.raises(SQLSemanticValidationPipelineError):
        service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_unsafe_retry_sql_is_rejected():
    service, generator, executor = make_service(
        INVALID_SQL,
        retry_sql="DELETE FROM orders;",
    )

    with pytest.raises(SQLValidationPipelineError):
        service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_retry_generation_failure_stops_execution():
    service, generator, executor = make_service(INVALID_SQL)

    generator.regenerate.side_effect = RuntimeError(
        "Ollama unavailable"
    )

    with pytest.raises(
        SQLGenerationPipelineError,
        match="regeneration failed",
    ):
        service.run(QUESTION)

    executor.execute.assert_not_called()


def test_no_retry_for_unsafe_initial_sql():
    service, generator, executor = make_service(
        "DELETE FROM orders;"
    )

    with pytest.raises(SQLValidationPipelineError):
        service.run(QUESTION)

    generator.regenerate.assert_not_called()
    executor.execute.assert_not_called()


def test_retry_abstention_stops_execution():
    service, generator, executor = make_service(
        INVALID_SQL,
        retry_sql="INSUFFICIENT_CONTEXT",
    )

    with pytest.raises(InsufficientContextError):
        service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_retry_uses_updated_generation_metadata():
    service, generator, _ = make_service(INVALID_SQL)

    corrected = make_generation(VALID_SQL)
    generator.regenerate.return_value = SQLGenerationResult(
        question=corrected.question,
        sql=corrected.sql,
        model="retry-model",
        selected_chunk_ids=corrected.selected_chunk_ids,
        dependency_chunk_ids=corrected.dependency_chunk_ids,
        messages=corrected.messages,
    )

    result = service.run(QUESTION)

    assert result.model == "retry-model"
