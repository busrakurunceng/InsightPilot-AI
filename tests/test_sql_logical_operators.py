
import pytest

from app.backend.sql_validator import (
    SQLValidationError,
    validate_sql,
)


ALLOWED_TABLES = {
    "orders",
    "customers",
    "order_items",
}


@pytest.mark.parametrize(
    "sql",
    [
        # AND with date filters
        """
        SELECT COUNT(*)
        FROM orders
        WHERE order_purchase_timestamp >= '2018-01-01'
          AND order_purchase_timestamp < '2019-01-01'
        """,

        # OR with order statuses
        """
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'delivered'
           OR order_status = 'shipped'
        """,

        # AND and OR together
        """
        SELECT order_id
        FROM orders
        WHERE order_status = 'delivered'
          AND (
              customer_id IS NOT NULL
              OR order_id IS NOT NULL
          )
        """,

        # Multiple AND conditions
        """
        SELECT COUNT(*)
        FROM orders
        WHERE order_purchase_timestamp >= '2018-01-01'
          AND order_purchase_timestamp < '2019-01-01'
          AND order_status = 'delivered'
        """,
    ],
)
def test_logical_operators_accepted(sql):
    result = validate_sql(
        sql,
        ALLOWED_TABLES,
    )

    assert result.referenced_tables == ("orders",)


@pytest.mark.parametrize(
    "sql",
    [
        # Dangerous function within an AND condition
        """
        SELECT order_id
        FROM orders
        WHERE order_status = 'delivered'
          AND pg_sleep(1) IS NULL
        """,

        # Dangerous function within an OR condition
        """
        SELECT order_id
        FROM orders
        WHERE order_status = 'delivered'
           OR pg_read_file('/etc/passwd') IS NOT NULL
        """,

        # Unauthorized table within an AND condition
        """
        SELECT order_id
        FROM orders
        WHERE order_status = 'delivered'
          AND customer_id IN (
              SELECT customer_id
              FROM secret_table
          )
        """,
    ],
)
def test_logical_operators_do_not_bypass_security(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(
            sql,
            ALLOWED_TABLES,
        )
