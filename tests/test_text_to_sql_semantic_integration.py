from unittest.mock import Mock, patch

import pytest

from app.backend.sql_executor import SQLExecutionResult
from app.backend.sql_generator import SQLGenerationResult
from app.backend.text_to_sql_service import (
    OLIST_ALLOWED_TABLES,
    SQLGenerationPipelineError,
    SQLSemanticValidationPipelineError,
    SQLValidationPipelineError,
    TextToSQLService,
)

QUESTION = (
    "Her eyaletteki müşterilerin verdiği "
    "sipariş sayısını göster."
)

INVALID_GROUPING_SQL = (
    "SELECT COUNT(*) AS total_orders FROM orders;"
)

VALID_GROUPING_SQL = """
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


def make_service(sql):
    generator = Mock()
    generator.generate.return_value = make_generation(sql)

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


def test_missing_required_grouping_is_rejected():
    service, generator, executor = make_service(
        INVALID_GROUPING_SQL
    )

    generator.regenerate.side_effect = RuntimeError(
        "Retry unavailable"
    )

    with pytest.raises(
        SQLGenerationPipelineError,
        match="regeneration failed",
    ):
        service.run(QUESTION)

    generator.generate.assert_called_once_with(QUESTION)
    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_correct_grouping_is_executed():
    service, generator, executor = make_service(
        VALID_GROUPING_SQL
    )

    result = service.run(QUESTION)

    assert result.sql.strip() == VALID_GROUPING_SQL.strip()
    assert result.rows[0]["customer_state"] == "SP"

    generator.regenerate.assert_not_called()
    executor.execute.assert_called_once()


def test_no_dimension_keeps_existing_execution_flow():
    question = "Toplam kaç sipariş var?"

    service, generator, executor = make_service(
        "SELECT COUNT(*) AS total_orders FROM orders;"
    )

    generator.generate.return_value = SQLGenerationResult(
        question=question,
        sql="SELECT COUNT(*) AS total_orders FROM orders;",
        model="test-model",
        selected_chunk_ids=["metric:total_orders"],
        dependency_chunk_ids=["table:orders"],
    )

    result = service.run(question)

    assert result.sql == (
        "SELECT COUNT(*) AS total_orders FROM orders;"
    )

    generator.regenerate.assert_not_called()
    executor.execute.assert_called_once()


def test_unsafe_sql_is_rejected_before_semantic_check():
    service, generator, executor = make_service(
        "DELETE FROM orders;"
    )

    with patch(
        "app.backend.text_to_sql_service.infer_question_dimension"
    ) as mapper:
        with pytest.raises(SQLValidationPipelineError):
            service.run(QUESTION)

    mapper.assert_not_called()
    generator.regenerate.assert_not_called()
    executor.execute.assert_not_called()


def test_semantic_mapper_failure_is_fail_closed():
    service, generator, executor = make_service(
        VALID_GROUPING_SQL
    )

    with patch(
        "app.backend.text_to_sql_service.infer_question_dimension",
        side_effect=RuntimeError("Mapping failed"),
    ):
        with pytest.raises(
            SQLSemanticValidationPipelineError,
            match="Could not determine",
        ):
            service.run(QUESTION)

    generator.regenerate.assert_not_called()
    executor.execute.assert_not_called()


def test_semantic_validator_failure_is_fail_closed():
    service, generator, executor = make_service(
        VALID_GROUPING_SQL
    )

    with patch(
        "app.backend.text_to_sql_service.validate_grouping_requirement",
        side_effect=RuntimeError("Validation failed"),
    ):
        with pytest.raises(
            SQLSemanticValidationPipelineError,
            match="Semantic SQL validation failed",
        ):
            service.run(QUESTION)

    generator.regenerate.assert_not_called()
    executor.execute.assert_not_called()
