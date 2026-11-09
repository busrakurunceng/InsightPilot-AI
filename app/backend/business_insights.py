
"""Deterministic, evidence-based business insights.

Module 4.4.1:
- Describe scalar KPIs.
- Summarize categorical numeric comparisons.
- Calculate extrema and totals from returned rows.
- Avoid unsupported claims from partial or invalid data.

This module never calls an LLM or a database.
"""

from decimal import Decimal, InvalidOperation
from math import isfinite
from numbers import Real

from app.backend.analytics_contract import AnalyticsResponse


def _to_decimal(value: object) -> Decimal | None:
    """Convert a finite numeric value to Decimal safely."""

    if isinstance(value, bool):
        return None

    if isinstance(value, Decimal):
        return value if value.is_finite() else None

    if isinstance(value, Real):
        try:
            if not isfinite(value):
                return None

            converted = Decimal(str(value))
            return converted if converted.is_finite() else None

        except (
            TypeError,
            ValueError,
            OverflowError,
            InvalidOperation,
        ):
            return None

    return None


def _format_number(value: Decimal) -> str:
    """Format finite decimal numbers without unnecessary zeros."""

    if value == 0:
        return "0"

    return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")


def _get_profile_columns(
    response: AnalyticsResponse,
    role: str,
    data_type: str,
) -> list[str]:
    """Find columns matching an analytical role and type."""

    return [
        profile.name
        for profile in response.column_profiles
        if profile.role == role
        and profile.data_type == data_type
    ]


def generate_insights(
    response: AnalyticsResponse,
) -> list[str]:
    """Generate factual insights from returned SQL result rows.

    Insights describe only the returned result, never the
    complete underlying database unless completeness is known.
    """

    if not isinstance(response, AnalyticsResponse):
        raise TypeError(
            "Expected an AnalyticsResponse instance."
        )

    if response.row_count == 0:
        return ["The query returned no rows."]

    # A truncated result may omit categories or extremes.
    # Do not produce potentially misleading comparisons.
    if response.truncated:
        return [
            "The result is truncated; insights about the "
            "complete result cannot be determined."
        ]

    if len(response.column_profiles) != len(response.columns):
        return []

    numeric_columns = _get_profile_columns(
        response,
        role="measure",
        data_type="numeric",
    )

    categorical_columns = _get_profile_columns(
        response,
        role="dimension",
        data_type="categorical",
    )

    # Case 1: one numeric scalar (KPI).
    if (
        response.row_count == 1
        and len(response.columns) == 1
        and len(numeric_columns) == 1
    ):
        column = numeric_columns[0]
        value = _to_decimal(response.rows[0][column])

        if value is None:
            return []

        return [
            f"{column}: {_format_number(value)}."
        ]

    # Case 2: exactly one category and one numeric measure.
    if not (
        len(response.columns) == 2
        and len(categorical_columns) == 1
        and len(numeric_columns) == 1
    ):
        return []

    category_column = categorical_columns[0]
    measure_column = numeric_columns[0]

    pairs: list[tuple[str, Decimal]] = []

    for row in response.rows:
        category = row[category_column]
        value = _to_decimal(row[measure_column])

        if category is None or value is None:
            continue

        pairs.append((str(category), value))

    if not pairs:
        return []

    # Missing values mean the visible comparison is incomplete.
    # Do not imply that all rows were included.
    skipped_count = response.row_count - len(pairs)

    # Stable ordering for ties.
    ordered = sorted(
        pairs,
        key=lambda item: (-item[1], item[0]),
    )

    highest_category, highest_value = ordered[0]

    lowest_category, lowest_value = min(
        pairs,
        key=lambda item: (item[1], item[0]),
    )

    insights = [
        (
            f"Highest {measure_column}: "
            f"{highest_category} ({_format_number(highest_value)})."
        ),
        (
            f"Lowest {measure_column}: "
            f"{lowest_category} ({_format_number(lowest_value)})."
        ),
    ]

    # Sum only when every row is valid and category labels
    # are unique. This is a sum of returned measure values,
    # not necessarily an independently defined business KPI.
    categories = [
        category
        for category, _ in pairs
    ]

    if (
        skipped_count == 0
        and len(categories) == len(set(categories))
    ):
        total = sum(
            (value for _, value in pairs),
            Decimal("0"),
        )

        insights.append(
            f"Sum of returned {measure_column} values: "
            f"{_format_number(total)}."
        )

    if skipped_count:
        insights.append(
            f"{skipped_count} row(s) were excluded from "
            "the comparison due to missing or invalid values."
        )

    return insights
