
"""Tests for the Plotly analytics renderer."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import plotly.graph_objects as go
import pytest

from app.backend.analytics_contract import (
    AnalyticsResponse,
    VisualizationSpec,
)
from app.frontend.components.analytics_renderer import (
    _format_kpi,
    _numeric_value,
    build_chart,
    render_visualization,
)


def make_response(
    columns,
    rows,
    chart_type="table",
    x_column=None,
    y_column=None,
    title="",
):
    return AnalyticsResponse(
        question="Test question",
        sql="SELECT 1",
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=False,
        visualization=VisualizationSpec(
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            title=title,
        ),
    )


def test_integer_kpi_format():
    assert _format_kpi(99441) == "99,441"


def test_decimal_kpi_format():
    assert _format_kpi(Decimal("1250.50")) == "1,250.5"


def test_zero_kpi_format():
    assert _format_kpi(0) == "0"


def test_negative_kpi_format():
    assert _format_kpi(-125.5) == "-125.5"


def test_nonfinite_number_rejected():
    assert _numeric_value(float("inf")) is None
    assert _numeric_value(float("nan")) is None


def test_boolean_not_numeric():
    assert _numeric_value(True) is None


def test_string_not_numeric():
    assert _numeric_value("100") is None


def test_decimal_numeric_conversion():
    assert _numeric_value(Decimal("12.5")) == 12.5


def test_bar_chart_created():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "RJ", "orders": 50},
        ],
        chart_type="bar",
        x_column="state",
        y_column="orders",
    )

    figure = build_chart(response)

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "bar"
    assert list(figure.data[0].x) == ["SP", "RJ"]
    assert list(figure.data[0].y) == [100, 50]


def test_line_chart_created_and_sorted():
    response = make_response(
        ["month", "orders"],
        [
            {"month": date(2026, 2, 1), "orders": 150},
            {"month": date(2026, 1, 1), "orders": 100},
        ],
        chart_type="line",
        x_column="month",
        y_column="orders",
    )

    figure = build_chart(response)

    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == "scatter"
    assert list(figure.data[0].y) == [100, 150]


def test_table_does_not_create_chart():
    response = make_response(
        ["state"],
        [{"state": "SP"}],
    )

    assert build_chart(response) is None


def test_kpi_does_not_create_plotly_chart():
    response = make_response(
        ["orders"],
        [{"orders": 100}],
        chart_type="kpi",
        y_column="orders",
    )

    assert build_chart(response) is None


def test_empty_bar_result():
    response = make_response(
        ["state", "orders"],
        [],
        chart_type="bar",
        x_column="state",
        y_column="orders",
    )

    assert build_chart(response) is None


def test_invalid_numeric_rows_are_skipped():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "RJ", "orders": None},
        ],
        chart_type="bar",
        x_column="state",
        y_column="orders",
    )

    figure = build_chart(response)

    assert figure is not None
    assert list(figure.data[0].x) == ["SP"]


def test_all_invalid_numeric_rows():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": None},
        ],
        chart_type="bar",
        x_column="state",
        y_column="orders",
    )

    assert build_chart(response) is None


def test_kpi_render_calls_streamlit_metric():
    response = make_response(
        ["total_orders"],
        [{"total_orders": 99441}],
        chart_type="kpi",
        y_column="total_orders",
        title="Total Orders",
    )

    with patch(
        "app.frontend.components.analytics_renderer.st.metric"
    ) as metric:
        render_visualization(response)

    metric.assert_called_once_with(
        label="Total Orders",
        value="99,441",
    )


def test_bar_render_calls_plotly():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
        ],
        chart_type="bar",
        x_column="state",
        y_column="orders",
    )

    with patch(
        "app.frontend.components.analytics_renderer.st.plotly_chart"
    ) as plotly_chart:
        render_visualization(response)

    plotly_chart.assert_called_once()


def test_table_render_does_not_call_plotly():
    response = make_response(
        ["state"],
        [{"state": "SP"}],
    )

    with patch(
        "app.frontend.components.analytics_renderer.st.plotly_chart"
    ) as plotly_chart:
        render_visualization(response)

    plotly_chart.assert_not_called()


def test_source_rows_are_not_modified():
    rows = [
        {"state": "SP", "orders": Decimal("100.50")},
        {"state": "RJ", "orders": Decimal("50.25")},
    ]

    response = make_response(
        ["state", "orders"],
        rows,
        chart_type="bar",
        x_column="state",
        y_column="orders",
    )

    original = [dict(row) for row in rows]

    build_chart(response)

    assert rows == original


def test_invalid_input_type():
    with pytest.raises(TypeError):
        build_chart({"rows": []})


def test_line_rejects_text_dates():
    response = make_response(
        ["month", "orders"],
        [
            {"month": "2026-01", "orders": 100},
        ],
        chart_type="line",
        x_column="month",
        y_column="orders",
    )

    assert build_chart(response) is None
