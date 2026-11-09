
"""Deterministic visualization recommendations for analytics results.

Module 4.3.1:
- KPI for a single numeric value.
- Line chart for datetime + numeric data.
- Bar chart for categorical + numeric data.
- Table fallback for ambiguous or unsupported results.
"""

from app.backend.analytics_contract import (
    AnalyticsResponse,
    ColumnProfile,
    VisualizationSpec,
)


def _columns_with_type(
    profiles: list[ColumnProfile],
    data_type: str,
) -> list[str]:
    """Return column names matching a data type."""

    return [
        profile.name
        for profile in profiles
        if profile.data_type == data_type
    ]


def recommend_visualization(
    response: AnalyticsResponse,
) -> VisualizationSpec:
    """Choose a visualization using deterministic rules."""

    if not isinstance(response, AnalyticsResponse):
        raise TypeError(
            "Expected an AnalyticsResponse instance."
        )

    # No data: avoid suggesting an empty chart.
    if response.row_count == 0:
        return VisualizationSpec(
            chart_type="table",
            title="No data available",
        )

    # Do not guess when profiling is missing or incomplete.
    if len(response.column_profiles) != len(response.columns):
        return VisualizationSpec(
            chart_type="table",
            title="Query results",
        )

    profiles = response.column_profiles

    numeric = _columns_with_type(profiles, "numeric")
    categorical = _columns_with_type(profiles, "categorical")
    datetime_columns = _columns_with_type(profiles, "datetime")

    # One numeric column, one row: scalar KPI.
    if (
        response.row_count == 1
        and len(response.columns) == 1
        and len(numeric) == 1
    ):
        return VisualizationSpec(
            chart_type="kpi",
            y_column=numeric[0],
            title=numeric[0].replace("_", " ").title(),
        )

    # Exactly one date dimension and one numeric measure.
    if (
        len(response.columns) == 2
        and len(datetime_columns) == 1
        and len(numeric) == 1
    ):
        return VisualizationSpec(
            chart_type="line",
            x_column=datetime_columns[0],
            y_column=numeric[0],
            title="Trend over time",
        )

    # Exactly one categorical dimension and one numeric measure.
    if (
        len(response.columns) == 2
        and len(categorical) == 1
        and len(numeric) == 1
    ):
        return VisualizationSpec(
            chart_type="bar",
            x_column=categorical[0],
            y_column=numeric[0],
            title="Category comparison",
        )

    return VisualizationSpec(
        chart_type="table",
        title="Query results",
    )
