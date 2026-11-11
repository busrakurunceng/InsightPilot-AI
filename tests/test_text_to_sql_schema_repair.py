
from unittest.mock import Mock, patch

import pytest

from app.backend.sql_generator import SQLGenerationResult
from app.backend.text_to_sql_service import (
    InsufficientContextError,
    SQLSemanticValidationPipelineError,
    SQLValidationPipelineError,
    TextToSQLService,
)


QUESTION = "Müşteri sayısı nedir?"

INVALID_SQL = (
    "SELECT customers.state FROM customers"
)

VALID_SQL = (
    "SELECT customers.customer_state FROM customers"
)

UNSAFE_SQL = "DELETE FROM customers"


def make_generation(sql):
    return SQLGenerationResult(
        question=QUESTION,
        sql=sql,
        model="test-model",
        selected_chunk_ids=["customers"],
        dependency_chunk_ids=[],
        messages=[
            {
                "role": "system",
                "content": "customers.customer_state",
            },
            {
                "role": "user",
                "content": QUESTION,
            },
        ],
    )


@pytest.fixture
def setup_service():
    generator = Mock()
    executor = Mock()

    executor.allowed_tables = {
        "customers",
    }
    executor.engine = Mock()
    executor.timeout_ms = 5000

    executor.execute.return_value = Mock(
        columns=["customer_state"],
        rows=[
            {"customer_state": "SP"},
        ],
        row_count=1,
        truncated=False,
    )

    service = TextToSQLService(
        generator=generator,
        executor=executor,
        allowed_tables={"customers"},
    )

    return service, generator, executor


def test_valid_sql_does_not_retry(setup_service):
    service, generator, executor = setup_service

    generator.generate.return_value = make_generation(
        VALID_SQL
    )

    with patch.object(
        service,
        "_validate_database_schema",
        return_value=None,
    ):
        result = service.run(QUESTION)

    assert result.sql == VALID_SQL

    generator.regenerate.assert_not_called()
    executor.execute.assert_called_once()


def test_schema_failure_triggers_one_repair(setup_service):
    service, generator, executor = setup_service

    generator.generate.return_value = make_generation(
        INVALID_SQL
    )

    generator.regenerate.return_value = make_generation(
        VALID_SQL
    )

    with patch.object(
        service,
        "_validate_database_schema",
        side_effect=[
            SQLValidationPipelineError(
                "Invalid database reference."
            ),
            None,
        ],
    ) as schema_check:
        result = service.run(QUESTION)

    assert result.sql == VALID_SQL
    assert schema_check.call_count == 2

    generator.regenerate.assert_called_once()

    assert (
        generator.regenerate.call_args.kwargs[
            "validation_type"
        ]
        == "schema"
    )

    executor.execute.assert_called_once_with(
        VALID_SQL
    )


def test_schema_repair_failure_is_rejected(setup_service):
    service, generator, executor = setup_service

    generator.generate.return_value = make_generation(
        INVALID_SQL
    )

    generator.regenerate.return_value = make_generation(
        INVALID_SQL
    )

    with patch.object(
        service,
        "_validate_database_schema",
        side_effect=SQLValidationPipelineError(
            "Invalid database reference."
        ),
    ):
        with pytest.raises(
            SQLValidationPipelineError
        ):
            service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_unsafe_repair_is_rejected(setup_service):
    service, generator, executor = setup_service

    generator.generate.return_value = make_generation(
        INVALID_SQL
    )

    generator.regenerate.return_value = make_generation(
        UNSAFE_SQL
    )

    with patch.object(
        service,
        "_validate_database_schema",
        side_effect=SQLValidationPipelineError(
            "Invalid database reference."
        ),
    ):
        with pytest.raises(
            SQLValidationPipelineError
        ):
            service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_schema_repair_insufficient_context(setup_service):
    service, generator, executor = setup_service

    generator.generate.return_value = make_generation(
        INVALID_SQL
    )

    generator.regenerate.return_value = make_generation(
        "INSUFFICIENT_CONTEXT"
    )

    with patch.object(
        service,
        "_validate_database_schema",
        side_effect=SQLValidationPipelineError(
            "Invalid database reference."
        ),
    ):
        with pytest.raises(
            InsufficientContextError
        ):
            service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_semantic_retry_does_not_allow_schema_retry(
    setup_service,
):
    service, generator, executor = setup_service

    generator.generate.return_value = make_generation(
        "SELECT COUNT(*) FROM customers"
    )

    generator.regenerate.return_value = make_generation(
        VALID_SQL
    )

    with (
        patch(
            "app.backend.text_to_sql_service."
            "infer_question_dimension",
            return_value="customer_state",
        ),
        patch.object(
            service,
            "_validate_semantics",
            side_effect=[
                ["Missing required grouping dimension."],
                [],
            ],
        ),
        patch.object(
            service,
            "_validate_database_schema",
            side_effect=SQLValidationPipelineError(
                "Invalid database reference."
            ),
        ),
    ):
        with pytest.raises(
            SQLValidationPipelineError
        ):
            service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()


def test_schema_repair_preserves_semantic_requirements(
    setup_service,
):
    service, generator, executor = setup_service

    generator.generate.return_value = make_generation(
        INVALID_SQL
    )

    generator.regenerate.return_value = make_generation(
        "SELECT COUNT(*) FROM customers"
    )

    with (
        patch(
            "app.backend.text_to_sql_service."
            "infer_question_dimension",
            return_value="customer_state",
        ),
        patch.object(
            service,
            "_validate_semantics",
            side_effect=[
                [],
                ["Missing required grouping dimension."],
            ],
        ),
        patch.object(
            service,
            "_validate_database_schema",
            side_effect=SQLValidationPipelineError(
                "Invalid database reference."
            ),
        ),
    ):
        with pytest.raises(
            SQLSemanticValidationPipelineError
        ):
            service.run(QUESTION)

    generator.regenerate.assert_called_once()
    executor.execute.assert_not_called()
