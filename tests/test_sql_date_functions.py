"""Regression tests for governed date extraction in SQL validation."""

import pytest

from app.backend.sql_validator import SQLValidationError, validate_sql

ALLOWED_TABLES = {"orders"}


@pytest.mark.parametrize("sql", [
    "SELECT EXTRACT(YEAR FROM order_purchase_timestamp) FROM orders",
    "SELECT EXTRACT(MONTH FROM order_purchase_timestamp) FROM orders",
    "SELECT EXTRACT(YEAR FROM order_purchase_timestamp) AS yr, COUNT(*) FROM orders GROUP BY yr",
])
def test_extract_is_allowed(sql):
    result = validate_sql(sql, allowed_tables=ALLOWED_TABLES)
    assert result.referenced_tables == ("orders",)


@pytest.mark.parametrize("sql", [
    "SELECT pg_sleep(10) FROM orders",
    "SELECT pg_read_file('/etc/passwd') FROM orders",
    "DELETE FROM orders",
    "SELECT EXTRACT(YEAR FROM order_purchase_timestamp) FROM secret_table",
])
def test_unsafe_or_unapproved_sql_still_rejected(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql, allowed_tables=ALLOWED_TABLES)

def test_date_trunc_is_allowed():
    sql = """
        SELECT DATE_TRUNC(
            'month',
            order_purchase_timestamp
        ) AS month
        FROM orders
    """

    result = validate_sql(
        sql,
        allowed_tables={"orders"},
    )

    assert result.referenced_tables == ("orders",)