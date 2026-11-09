
"""Tests for deterministic visualization recommendations."""

from datetime import date

import pytest

from app.backend.analytics_contract import (
    AnalyticsResponse,
    ColumnProfile,
)
from app.backend.result_profiler import profile_result
from app.backend.visualization_recommender import (
    recommend_visualization,
)


def make_response(columns, rows, profiles=None):
    if profiles is None:
        profiles = profile_result(columns, rows)

    return AnalyticsResponse(
        question="Test question",
        sql="SELECT 1",
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=False,
        column_profiles=profiles,
    )


def test_single_numeric_value_uses_kpi():
    response = make_response(
        ["total_orders"],
        [{"total_orders": 100}],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "kpi"
    assert spec.y_column == "total_orders"
    assert spec.x_column is None


def test_category_and_numeric_uses_bar():
    response = make_response(
        ["state", "total_orders"],
        [
            {"state": "SP", "total_orders": 100},
            {"state": "RJ", "total_orders": 50},
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "bar"
    assert spec.x_column == "state"
    assert spec.y_column == "total_orders"


def test_datetime_and_numeric_uses_line():
    response = make_response(
        ["order_month", "revenue"],
        [
            {
                "order_month": date(2026, 1, 1),
                "revenue": 100,
            },
            {
                "order_month": date(2026, 2, 1),
                "revenue": 150,
            },
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "line"
    assert spec.x_column == "order_month"
    assert spec.y_column == "revenue"


def test_empty_result_uses_table():
    response = make_response(
        ["state", "total_orders"],
        [],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"


def test_multiple_numeric_columns_use_table():
    response = make_response(
        ["revenue", "orders"],
        [
            {"revenue": 100, "orders": 5},
            {"revenue": 200, "orders": 10},
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"


def test_multiple_categories_use_table():
    response = make_response(
        ["state", "city", "orders"],
        [
            {
                "state": "SP",
                "city": "Sao Paulo",
                "orders": 100,
            }
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"


def test_single_category_uses_table():
    response = make_response(
        ["state"],
        [
            {"state": "SP"},
            {"state": "RJ"},
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"


def test_boolean_and_numeric_uses_table():
    response = make_response(
        ["is_delivered", "orders"],
        [
            {"is_delivered": True, "orders": 100},
            {"is_delivered": False, "orders": 20},
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"


def test_unknown_column_type_uses_table():
    response = make_response(
        ["mixed", "orders"],
        [
            {"mixed": "SP", "orders": 100},
            {"mixed": 123, "orders": 50},
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"


def test_missing_profiles_use_table():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
        ],
        profiles=[],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"


def test_truncated_results_can_use_bar():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "RJ", "orders": 50},
        ],
    )

    response = AnalyticsResponse(
        question=response.question,
        sql=response.sql,
        columns=response.columns,
        rows=response.rows,
        row_count=response.row_count,
        truncated=True,
        column_profiles=response.column_profiles,
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "bar"


def test_recommender_does_not_modify_response():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
        ],
    )

    original_rows = [
        dict(row)
        for row in response.rows
    ]

    recommend_visualization(response)

    assert response.rows == original_rows
    assert response.visualization is None


def test_wrong_input_type_rejected():
    with pytest.raises(TypeError, match="AnalyticsResponse"):
        recommend_visualization({"rows": []})


def test_incomplete_profile_count_uses_table():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
        ],
        profiles=[
            ColumnProfile(
                name="state",
                data_type="categorical",
                role="dimension",
            )
        ],
    )

    spec = recommend_visualization(response)

    assert spec.chart_type == "table"
