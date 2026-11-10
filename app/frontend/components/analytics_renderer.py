
"""Plotly visualization renderer for InsightPilot analytics.

Module 4.5.2:
- KPI cards for scalar numeric results.
- Bar charts for categorical comparisons.
- Line charts for temporal trends.
- Table fallback for unsupported or invalid specifications.

The renderer never executes SQL or calls an LLM.
"""

from datetime import date, datetime
from decimal import Decimal
from math import isfinite
from numbers import Real
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.backend.analytics_contract import (
    AnalyticsResponse,
    VisualizationSpec,
)


def _numeric_value(value: Any) -> float | None:
    """Convert finite numeric values for plotting."""

    if isinstance(value, bool):
        return None

    if isinstance(value, Decimal):
        if not value.is_finite():
            return None
        try:
            converted = float(value)
        except (ValueError, OverflowError):
            return None

    elif isinstance(value, Real):
        try:
            converted = float(value)
        except (TypeError, ValueError, OverflowError):
            return None

    else:
        return None

    return converted if isfinite(converted) else None


def _format_kpi(value: Any) -> str:
    """Format a KPI without unnecessarily losing Decimal precision."""

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, Decimal):
        if not value.is_finite():
            return "N/A"
        return f"{value:,.2f}".rstrip("0").rstrip(".")

    if isinstance(value, int):
        return f"{value:,}"

    if isinstance(value, float):
        if not isfinite(value):
            return "N/A"
        return f"{value:,.2f}".rstrip("0").rstrip(".")

    return str(value)


def _valid_spec(
    response: AnalyticsResponse,
    spec: VisualizationSpec,
) -> bool:
    """Check whether referenced axes exist in the result."""

    if spec.chart_type == "kpi":
        return spec.y_column in response.columns

    if spec.chart_type in ("bar", "line"):
        return (
            spec.x_column in response.columns
            and spec.y_column in response.columns
            and spec.x_column != spec.y_column
        )

    return spec.chart_type == "table"


def build_chart(
    response: AnalyticsResponse,
) -> go.Figure | None:
    """Build a Plotly figure without rendering it.

    Returns None for KPI, table, or unsuitable data.
    """

    if not isinstance(response, AnalyticsResponse):
        raise TypeError("Expected AnalyticsResponse.")

    spec = response.visualization

    if spec is None or not _valid_spec(response, spec):
        return None

    if spec.chart_type not in ("bar", "line"):
        return None

    if not response.rows:
        return None

    x_column = spec.x_column
    y_column = spec.y_column

    assert x_column is not None
    assert y_column is not None

    valid_rows = []

    for row in response.rows:
        x_value = row[x_column]
        y_value = _numeric_value(row[y_column])

        if x_value is None or y_value is None:
            continue

        if spec.chart_type == "line" and not isinstance(
            x_value, (date, datetime, pd.Timestamp)
        ):
            continue

        valid_rows.append(
            {
                x_column: x_value,
                y_column: y_value,
            }
        )

    if not valid_rows:
        return None

    dataframe = pd.DataFrame(valid_rows)

    if spec.chart_type == "line":
        dataframe = dataframe.sort_values(
            x_column,
            kind="stable",
        )

        figure = px.line(
            dataframe,
            x=x_column,
            y=y_column,
            markers=True,
            title=spec.title or "Trend over time",
        )

    else:
        figure = px.bar(
            dataframe,
            x=x_column,
            y=y_column,
            title=spec.title or "Category comparison",
        )

    figure.update_layout(
        margin=dict(l=20, r=20, t=55, b=30),
        hovermode=(
            "x unified"
            if spec.chart_type == "line"
            else "closest"
        ),
    )

    return figure


def render_visualization(
    response: AnalyticsResponse,
) -> None:
    """Render the recommended visualization in Streamlit."""

    if not isinstance(response, AnalyticsResponse):
        raise TypeError("Expected AnalyticsResponse.")

    spec = response.visualization

    if spec is None:
        return

    if not _valid_spec(response, spec):
        st.info(
            "Visualization metadata is inconsistent. "
            "Showing the result table instead."
        )
        return

    if spec.chart_type == "table":
        return

    if spec.chart_type == "kpi":
        if response.row_count != 1:
            return

        value_column = spec.y_column

        assert value_column is not None

        value = response.rows[0][value_column]

        if _numeric_value(value) is None:
            return

        st.metric(
            label=spec.title or value_column.replace("_", " ").title(),
            value=_format_kpi(value),
        )
        return

    figure = build_chart(response)

    if figure is None:
        st.info(
            "No suitable data is available for this chart. "
            "The result table is shown above."
        )
        return

    st.plotly_chart(
        figure,
        width="stretch",
    )
