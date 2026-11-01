
from unittest.mock import MagicMock

import pytest

from app.backend.sql_executor import (
    SQLExecutionError,
    SQLExecutor,
)
from app.backend.sql_validator import SQLValidationError


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value

    transaction = connection.begin.return_value
    transaction.__enter__.return_value = transaction

    return engine, connection


def make_executor(engine, max_rows=100):
    return SQLExecutor(
        engine=engine,
        allowed_tables={"orders"},
        max_rows=max_rows,
    )


def test_rejects_missing_table_allowlist(mock_engine):
    engine, _ = mock_engine

    with pytest.raises(ValueError):
        SQLExecutor(engine=engine, allowed_tables=set())


@pytest.mark.parametrize("max_rows", [0, -1])
def test_rejects_invalid_max_rows(mock_engine, max_rows):
    engine, _ = mock_engine

    with pytest.raises(ValueError):
        make_executor(engine, max_rows=max_rows)


def test_rejects_invalid_timeout(mock_engine):
    engine, _ = mock_engine

    with pytest.raises(ValueError):
        SQLExecutor(
            engine=engine,
            allowed_tables={"orders"},
            timeout_ms=0,
        )


def test_executes_valid_select(mock_engine):
    engine, connection = mock_engine

    result = MagicMock()
    result.keys.return_value = ["total_orders"]
    result.mappings.return_value.fetchmany.return_value = [
        {"total_orders": 99441}
    ]

    connection.execute.return_value = result

    executor = make_executor(engine)

    output = executor.execute(
        "SELECT COUNT(*) AS total_orders FROM orders"
    )

    assert output.columns == ["total_orders"]
    assert output.rows == [{"total_orders": 99441}]
    assert output.row_count == 1
    assert output.truncated is False

    assert connection.begin.called
    assert connection.execute.call_count == 3


def test_enforces_row_limit(mock_engine):
    engine, connection = mock_engine

    result = MagicMock()
    result.keys.return_value = ["order_id"]
    result.mappings.return_value.fetchmany.return_value = [
        {"order_id": "A"},
        {"order_id": "B"},
        {"order_id": "C"},
    ]

    connection.execute.return_value = result

    executor = make_executor(engine, max_rows=2)

    output = executor.execute(
        "SELECT order_id FROM orders"
    )

    assert output.row_count == 2
    assert output.truncated is True
    assert output.rows == [
        {"order_id": "A"},
        {"order_id": "B"},
    ]

    result.mappings.return_value.fetchmany.assert_called_once_with(3)


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "UPDATE orders SET order_status = 'canceled'",
        "DROP TABLE orders",
    ],
)
def test_rejects_write_operations(mock_engine, sql):
    engine, connection = mock_engine

    executor = make_executor(engine)

    with pytest.raises(SQLValidationError):
        executor.execute(sql)

    connection.execute.assert_not_called()


def test_rejects_unauthorized_table(mock_engine):
    engine, connection = mock_engine

    executor = make_executor(engine)

    with pytest.raises(SQLValidationError):
        executor.execute("SELECT * FROM customers")

    connection.execute.assert_not_called()


def test_wraps_database_errors(mock_engine):
    engine, connection = mock_engine

    connection.execute.side_effect = RuntimeError(
        "Database unavailable"
    )

    executor = make_executor(engine)

    with pytest.raises(SQLExecutionError):
        executor.execute("SELECT * FROM orders")


def test_rejects_multiple_statements(mock_engine):
    engine, connection = mock_engine

    executor = make_executor(engine)

    with pytest.raises(SQLValidationError):
        executor.execute(
            "SELECT * FROM orders; SELECT * FROM orders"
        )

    connection.execute.assert_not_called()
