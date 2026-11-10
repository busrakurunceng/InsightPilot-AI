
"""Tests for PostgreSQL schema-aware SQL validation."""

from unittest.mock import MagicMock

import pytest

from app.backend.sql_schema_validator import (
    SQLSchemaValidationError,
    validate_sql_schema,
)
from app.backend.sql_validator import SQLValidationError


ALLOWED_TABLES = {"customers", "orders"}


def make_engine():
    engine = MagicMock()

    connection = (
        engine.connect.return_value.__enter__.return_value
    )

    return engine, connection


def test_valid_query_is_explained():
    engine, connection = make_engine()

    validate_sql_schema(
        "SELECT customer_state FROM customers",
        engine=engine,
        allowed_tables=ALLOWED_TABLES,
    )

    statements = [
        str(call.args[0])
        for call in connection.execute.call_args_list
    ]

    assert any(
        statement.startswith("EXPLAIN (FORMAT JSON)")
        for statement in statements
    )


def test_explain_does_not_use_analyze():
    engine, connection = make_engine()

    validate_sql_schema(
        "SELECT COUNT(*) FROM orders",
        engine=engine,
        allowed_tables=ALLOWED_TABLES,
    )

    statements = [
        str(call.args[0])
        for call in connection.execute.call_args_list
    ]

    explain_statements = [
        statement
        for statement in statements
        if statement.startswith("EXPLAIN")
    ]

    assert len(explain_statements) == 1
    assert "ANALYZE" not in explain_statements[0]


def test_transaction_is_read_only():
    engine, connection = make_engine()

    validate_sql_schema(
        "SELECT COUNT(*) FROM orders",
        engine=engine,
        allowed_tables=ALLOWED_TABLES,
    )

    statements = [
        str(call.args[0])
        for call in connection.execute.call_args_list
    ]

    assert "SET TRANSACTION READ ONLY" in statements


def test_postgresql_error_is_wrapped():
    engine, connection = make_engine()

    connection.execute.side_effect = RuntimeError(
        "column customers.state does not exist"
    )

    with pytest.raises(
        SQLSchemaValidationError
    ) as error:
        validate_sql_schema(
            "SELECT customers.state FROM customers",
            engine=engine,
            allowed_tables=ALLOWED_TABLES,
        )

    assert isinstance(
        error.value.__cause__,
        RuntimeError,
    )


def test_forbidden_sql_rejected_before_database():
    engine, connection = make_engine()

    with pytest.raises(SQLValidationError):
        validate_sql_schema(
            "DELETE FROM orders",
            engine=engine,
            allowed_tables=ALLOWED_TABLES,
        )

    connection.execute.assert_not_called()


def test_disallowed_table_rejected():
    engine, connection = make_engine()

    with pytest.raises(SQLValidationError):
        validate_sql_schema(
            "SELECT * FROM secret_table",
            engine=engine,
            allowed_tables=ALLOWED_TABLES,
        )

    connection.execute.assert_not_called()


def test_invalid_timeout():
    engine, connection = make_engine()

    with pytest.raises(ValueError):
        validate_sql_schema(
            "SELECT * FROM customers",
            engine=engine,
            allowed_tables=ALLOWED_TABLES,
            timeout_ms=0,
        )

    connection.execute.assert_not_called()
