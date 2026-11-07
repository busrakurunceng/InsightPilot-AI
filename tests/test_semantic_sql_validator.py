
import pytest

from app.backend.semantic_sql_validator import (
    validate_grouping_requirement,
)


DIMENSION = "customers.customer_state"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM orders",
        "SELECT COUNT(*) AS total_orders FROM orders;",
    ],
)
def test_missing_group_by_is_rejected(sql):
    result = validate_grouping_requirement(
        sql,
        required_dimension=DIMENSION,
    )

    assert result.valid is False
    assert any("GROUP BY" in issue for issue in result.issues)


def test_correct_grouping_is_accepted():
    sql = """
    SELECT
        c.customer_state,
        COUNT(*) AS total_orders
    FROM orders AS o
    JOIN customers AS c
        ON o.customer_id = c.customer_id
    GROUP BY c.customer_state
    """

    result = validate_grouping_requirement(
        sql,
        required_dimension=DIMENSION,
    )

    assert result.valid is True
    assert result.issues == []


def test_wrong_grouping_dimension_is_rejected():
    sql = """
    SELECT order_status, COUNT(*)
    FROM orders
    GROUP BY order_status
    """

    result = validate_grouping_requirement(
        sql,
        required_dimension=DIMENSION,
    )

    assert result.valid is False


def test_no_required_dimension_is_accepted():
    result = validate_grouping_requirement(
        "SELECT COUNT(*) FROM orders",
    )

    assert result.valid is True


def test_invalid_sql_is_rejected():
    result = validate_grouping_requirement(
        "SELECT FROM",
        required_dimension=DIMENSION,
    )

    assert result.valid is False


def test_required_table_missing_is_rejected():
    sql = """
    SELECT customer_state, COUNT(*)
    FROM orders
    GROUP BY customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False
    assert any("Required table" in issue for issue in result.issues)


def test_dimension_missing_from_select_is_rejected():
    sql = """
    SELECT COUNT(*) AS total_orders
    FROM customers
    GROUP BY customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False
    assert any("SELECT" in issue for issue in result.issues)


def test_wrong_table_alias_is_rejected():
    sql = """
    SELECT o.customer_state, COUNT(*)
    FROM orders AS o
    JOIN customers AS c
        ON o.customer_id = c.customer_id
    GROUP BY o.customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False


def test_unqualified_dimension_in_single_table_is_accepted():
    sql = """
    SELECT customer_state, COUNT(*)
    FROM customers
    GROUP BY customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is True


def test_unqualified_dimension_in_multi_table_is_rejected():
    sql = """
    SELECT customer_state, COUNT(*)
    FROM orders AS o
    JOIN customers AS c
        ON o.customer_id = c.customer_id
    GROUP BY customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False


def test_dimension_only_in_select_is_rejected():
    sql = """
    SELECT customer_state, COUNT(*)
    FROM customers
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False
    assert any("GROUP BY" in issue for issue in result.issues)


def test_correct_group_by_but_wrong_select_is_rejected():
    sql = """
    SELECT customer_city, COUNT(*)
    FROM customers
    GROUP BY customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False


def test_multiple_statements_are_rejected():
    sql = """
    SELECT customer_state, COUNT(*)
    FROM customers
    GROUP BY customer_state;
    SELECT COUNT(*) FROM orders;
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False


def test_required_dimension_format_is_validated():
    result = validate_grouping_requirement(
        "SELECT COUNT(*) FROM orders",
        required_dimension="customer_state",
    )

    assert result.valid is False


def test_empty_sql_is_rejected_when_dimension_required():
    result = validate_grouping_requirement(
        "",
        required_dimension=DIMENSION,
    )

    assert result.valid is False


def test_nested_query_is_conservatively_rejected():
    sql = """
    SELECT c.customer_state, COUNT(*)
    FROM customers AS c
    WHERE c.customer_id IN (
        SELECT customer_id FROM orders
    )
    GROUP BY c.customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False


def test_correct_grouping_with_projection_alias():
    sql = """
    SELECT c.customer_state AS state, COUNT(*) AS total
    FROM customers AS c
    GROUP BY c.customer_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is True


def test_grouping_by_different_table_is_rejected():
    sql = """
    SELECT s.seller_state, COUNT(*)
    FROM sellers AS s
    JOIN customers AS c
        ON s.seller_state = c.customer_state
    GROUP BY s.seller_state
    """

    result = validate_grouping_requirement(sql, DIMENSION)

    assert result.valid is False
