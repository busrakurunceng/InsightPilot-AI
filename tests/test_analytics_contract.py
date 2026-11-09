
"""Tests for the Module 4 analytics data contracts."""

import pytest

from app.backend.analytics_contract import (
    AnalyticsResponse,
    ColumnProfile,
    VisualizationSpec,
)


def make_response(**overrides):
    values = {
        "question": "Her eyalette kaç sipariş var?",
        "sql": (
            "SELECT customer_state, COUNT(*) AS total_orders "
            "FROM customers GROUP BY customer_state"
        ),
        "columns": ["customer_state", "total_orders"],
        "rows": [
            {"customer_state": "SP", "total_orders": 100},
            {"customer_state": "RJ", "total_orders": 50},
        ],
        "row_count": 2,
        "truncated": False,
    }

    values.update(overrides)
    return AnalyticsResponse(**values)


def test_valid_analytics_response():
    result = make_response()

    assert result.question
    assert result.row_count == 2
    assert result.rows[0]["customer_state"] == "SP"
    assert result.visualization is None
    assert result.insights == []


def test_column_profile():
    profile = ColumnProfile(
        name="total_orders",
        data_type="numeric",
        role="measure",
    )

    assert profile.name == "total_orders"
    assert profile.data_type == "numeric"
    assert profile.role == "measure"


def test_empty_column_name_rejected():
    with pytest.raises(ValueError, match="Column name"):
        ColumnProfile(
            name=" ",
            data_type="numeric",
            role="measure",
        )


def test_bar_chart_requires_axes():
    with pytest.raises(ValueError, match="require"):
        VisualizationSpec(chart_type="bar")


def test_line_chart_requires_axes():
    with pytest.raises(ValueError, match="require"):
        VisualizationSpec(
            chart_type="line",
            x_column="month",
        )


def test_kpi_requires_value_column():
    with pytest.raises(ValueError, match="value column"):
        VisualizationSpec(chart_type="kpi")


def test_valid_visualization():
    spec = VisualizationSpec(
        chart_type="bar",
        x_column="customer_state",
        y_column="total_orders",
        title="Orders by state",
    )

    assert spec.chart_type == "bar"
    assert spec.x_column == "customer_state"


def test_empty_question_rejected():
    with pytest.raises(ValueError, match="Question"):
        make_response(question=" ")


def test_empty_sql_rejected():
    with pytest.raises(ValueError, match="SQL"):
        make_response(sql="")


def test_negative_row_count_rejected():
    with pytest.raises(ValueError, match="Row count"):
        make_response(row_count=-1)


def test_incorrect_row_count_rejected():
    with pytest.raises(ValueError, match="Row count"):
        make_response(row_count=10)


def test_duplicate_columns_rejected():
    with pytest.raises(ValueError, match="unique"):
        make_response(
            columns=["customer_state", "customer_state"]
        )


def test_missing_row_column_rejected():
    with pytest.raises(ValueError, match="declared columns"):
        make_response(
            rows=[
                {"customer_state": "SP"},
                {"customer_state": "RJ"},
            ]
        )


def test_extra_row_column_rejected():
    with pytest.raises(ValueError, match="declared columns"):
        make_response(
            rows=[
                {
                    "customer_state": "SP",
                    "total_orders": 100,
                    "extra": 1,
                },
                {
                    "customer_state": "RJ",
                    "total_orders": 50,
                },
            ]
        )


def test_unknown_profile_column_rejected():
    with pytest.raises(ValueError, match="Column profiles"):
        make_response(
            column_profiles=[
                ColumnProfile(
                    name="unknown_column",
                    data_type="numeric",
                    role="measure",
                )
            ]
        )


def test_duplicate_profiles_rejected():
    profile = ColumnProfile(
        name="total_orders",
        data_type="numeric",
        role="measure",
    )

    with pytest.raises(ValueError, match="unique"):
        make_response(
            column_profiles=[profile, profile]
        )


def test_unknown_visualization_column_rejected():
    with pytest.raises(ValueError, match="unknown column"):
        make_response(
            visualization=VisualizationSpec(
                chart_type="bar",
                x_column="missing_state",
                y_column="total_orders",
            )
        )


def test_valid_profiles_and_visualization():
    result = make_response(
        column_profiles=[
            ColumnProfile(
                name="customer_state",
                data_type="categorical",
                role="dimension",
            ),
            ColumnProfile(
                name="total_orders",
                data_type="numeric",
                role="measure",
            ),
        ],
        visualization=VisualizationSpec(
            chart_type="bar",
            x_column="customer_state",
            y_column="total_orders",
        ),
        insights=[
            "SP has the highest order count."
        ],
        model="qwen2.5-coder:7b-instruct",
    )

    assert len(result.column_profiles) == 2
    assert result.visualization.chart_type == "bar"
    assert len(result.insights) == 1
    assert result.model == "qwen2.5-coder:7b-instruct"


def test_empty_result_is_allowed():
    result = make_response(
        rows=[],
        row_count=0,
    )

    assert result.rows == []
    assert result.row_count == 0


def test_truncated_result_is_allowed():
    result = make_response(truncated=True)

    assert result.truncated is True
