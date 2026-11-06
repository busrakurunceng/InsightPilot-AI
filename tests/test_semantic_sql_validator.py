
import pytest

from app.backend.semantic_sql_validator import (
    validate_grouping_requirement,
)


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
        required_dimension="customers.customer_state",
    )

    assert result.valid is False
    assert any(
        "GROUP BY" in issue
        for issue in result.issues
    )


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
        required_dimension="customers.customer_state",
    )

    assert result.valid is True
    assert result.issues == []


def test_wrong_grouping_dimension_is_rejected():
    sql = """
    SELECT
        order_status,
        COUNT(*)
    FROM orders
    GROUP BY order_status
    """

    result = validate_grouping_requirement(
        sql,
        required_dimension="customers.customer_state",
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
        required_dimension="customers.customer_state",
    )

    assert result.valid is False
