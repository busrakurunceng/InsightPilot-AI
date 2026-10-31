
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


def test_valid_select():
    result = validate_sql(
        "SELECT order_id FROM orders",
        ALLOWED_TABLES,
    )

    assert result.sql == "SELECT order_id FROM orders"
    assert result.referenced_tables == ("orders",)


def test_valid_join():
    result = validate_sql(
        """
        SELECT o.order_id
        FROM orders o
        JOIN customers c
          ON o.customer_id = c.customer_id
        """,
        ALLOWED_TABLES,
    )

    assert result.referenced_tables == (
        "customers",
        "orders",
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM orders",
        "SELECT SUM(price) FROM order_items",
        "SELECT AVG(price) FROM order_items",
        "SELECT MIN(price), MAX(price) FROM order_items",
        "SELECT ROUND(AVG(price), 2) FROM order_items",
        "SELECT COALESCE(SUM(price), 0) FROM order_items",
    ],
)
def test_allowed_analytics_functions(sql):
    result = validate_sql(sql, ALLOWED_TABLES)

    assert result.referenced_tables


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM orders",
        "DROP TABLE orders",
        "UPDATE orders SET order_status = 'cancelled'",
        "INSERT INTO orders (order_id) VALUES ('x')",
        "SELECT * FROM orders; DELETE FROM orders",
        "SELECT * FROM nonexistent_table",
        "SELECT * FROM private.orders",
        "SELECT pg_sleep(10) FROM orders",
        "INSUFFICIENT_CONTEXT",
        "",
    ],
)
def test_unsafe_sql_rejected(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql, ALLOWED_TABLES)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_sleep(10) FROM orders",
        "SELECT pg_read_file('/etc/passwd') FROM orders",
        "SELECT set_config('search_path', 'public', false) FROM orders",
    ],
)
def test_unapproved_functions_rejected(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql, ALLOWED_TABLES)


def test_empty_allowlist_rejected():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT order_id FROM orders",
            set(),
        )


def test_basic_aggregation():
    result = validate_sql(
        "SELECT COUNT(*) FROM orders",
        ALLOWED_TABLES,
    )

    assert result.referenced_tables == ("orders",)


def test_valid_cte():
    result = validate_sql(
        """
        WITH order_counts AS (
            SELECT COUNT(*) AS total
            FROM orders
        )
        SELECT total
        FROM order_counts
        """,
        ALLOWED_TABLES,
    )

    assert result.referenced_tables == ("orders",)


def test_cte_cannot_shadow_allowed_table():
    with pytest.raises(SQLValidationError):
        validate_sql(
            """
            WITH orders AS (
                SELECT order_id FROM customers
            )
            SELECT * FROM orders
            """,
            ALLOWED_TABLES,
        )


def test_cte_cannot_hide_unauthorized_table():
    with pytest.raises(SQLValidationError):
        validate_sql(
            """
            WITH hidden AS (
                SELECT * FROM secret_table
            )
            SELECT * FROM hidden
            """,
            ALLOWED_TABLES,
        )


def test_schema_qualified_table():
    result = validate_sql(
        "SELECT order_id FROM public.orders",
        ALLOWED_TABLES,
    )

    assert result.referenced_tables == ("orders",)


def test_catalog_qualified_table_rejected():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT * FROM otherdb.public.orders",
            ALLOWED_TABLES,
        )


def test_multiple_select_statements_rejected():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT * FROM orders; SELECT * FROM customers",
            ALLOWED_TABLES,
        )


def test_select_into_rejected():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT * INTO new_table FROM orders",
            ALLOWED_TABLES,
        )


def test_empty_sql_rejected():
    with pytest.raises(SQLValidationError):
        validate_sql("   ", ALLOWED_TABLES)



# Step 3.4 - Additional security regression tests


@pytest.mark.parametrize(
    "sql",
    [
        # Unauthorized table inside a subquery
        """
        SELECT order_id
        FROM orders
        WHERE customer_id IN (
            SELECT customer_id FROM secret_table
        )
        """,

        # Unauthorized table inside a nested CTE
        """
        WITH outer_cte AS (
            WITH inner_cte AS (
                SELECT * FROM secret_table
            )
            SELECT * FROM inner_cte
        )
        SELECT * FROM outer_cte
        """,

        # A schema-qualified CTE reference
        """
        WITH order_counts AS (
            SELECT COUNT(*) FROM orders
        )
        SELECT * FROM public.order_counts
        """,

        # Unauthorized table inside a UNION
        """
        SELECT order_id FROM orders
        UNION ALL
        SELECT order_id FROM secret_table
        """,

        # A nested data-modifying statement
        """
        WITH deleted AS (
            DELETE FROM orders
            RETURNING order_id
        )
        SELECT * FROM deleted
        """,

        # A dangerous function in a subquery
        """
        SELECT order_id
        FROM orders
        WHERE EXISTS (
            SELECT pg_sleep(1)
        )
        """,
    ],
)
def test_advanced_unsafe_queries_rejected(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql, ALLOWED_TABLES)


@pytest.mark.parametrize(
    "sql",
    [
        # A normal aggregation with filtering
        """
        SELECT COUNT(*)
        FROM orders
        WHERE order_status = 'delivered'
        """,

        # A normal GROUP BY query
        """
        SELECT order_status, COUNT(*)
        FROM orders
        GROUP BY order_status
        """,

        # A safe subquery
        """
        SELECT order_id
        FROM orders
        WHERE customer_id IN (
            SELECT customer_id FROM customers
        )
        """,

        # A safe CTE
        """
        WITH delivered_orders AS (
            SELECT order_id
            FROM orders
            WHERE order_status = 'delivered'
        )
        SELECT COUNT(*)
        FROM delivered_orders
        """,
    ],
)
def test_advanced_valid_queries_accepted(sql):
    result = validate_sql(sql, ALLOWED_TABLES)
    assert result.referenced_tables
