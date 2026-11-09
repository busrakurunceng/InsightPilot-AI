
"""Deterministic column profiling for SQL query results.

Module 4.2.1:
- Infer column data types from actual Python values.
- Assign basic analytical roles.
- Detect nullable columns.
- Handle empty, mixed, and unsupported data safely.

No LLM calls or database connections are required.
"""

from datetime import date, datetime
from decimal import Decimal
from math import isfinite
from numbers import Real
from typing import Any

from app.backend.analytics_contract import (
    ColumnProfile,
    ColumnRole,
    ColumnType,
)


def _classify_value(value: Any) -> ColumnType:
    """Classify one non-null Python value."""

    # bool is a subclass of int, so it must be checked first.
    if isinstance(value, bool):
        return "boolean"

    # datetime is a subclass of date.
    if isinstance(value, (datetime, date)):
        return "datetime"

    if isinstance(value, Decimal):
        return (
            "numeric"
            if value.is_finite()
            else "unknown"
        )

    if isinstance(value, Real):
        try:
            return (
                "numeric"
                if isfinite(value)
                else "unknown"
            )
        except (TypeError, ValueError, OverflowError):
            return "unknown"

    if isinstance(value, str):
        return "categorical"

    return "unknown"


def _infer_column_type(
    values: list[Any],
) -> ColumnType:
    """Infer one column type from its non-null values."""

    non_null_values = [
        value
        for value in values
        if value is not None
    ]

    if not non_null_values:
        return "unknown"

    observed_types = {
        _classify_value(value)
        for value in non_null_values
    }

    # Mixed types are not silently coerced.
    if len(observed_types) != 1:
        return "unknown"

    return observed_types.pop()


def _infer_column_role(
    data_type: ColumnType,
) -> ColumnRole:
    """Map a recognized type to a basic analytical role."""

    if data_type == "numeric":
        return "measure"

    if data_type in (
        "categorical",
        "datetime",
        "boolean",
    ):
        return "dimension"

    return "unknown"


def profile_result(
    columns: list[str],
    rows: list[dict[str, Any]],
) -> list[ColumnProfile]:
    """Build a profile for every declared result column.

    The function assumes the rows follow the AnalyticsResponse
    contract: every row has the declared columns.

    Column order is preserved.
    """

    if not isinstance(columns, list):
        raise TypeError("Columns must be a list.")

    if not isinstance(rows, list):
        raise TypeError("Rows must be a list.")

    if len(columns) != len(set(columns)):
        raise ValueError("Column names must be unique.")

    if any(
        not isinstance(column, str) or not column.strip()
        for column in columns
    ):
        raise ValueError(
            "Column names must be non-empty strings."
        )

    expected_columns = set(columns)

    for row in rows:
        if not isinstance(row, dict):
            raise TypeError(
                "Every result row must be a dictionary."
            )

        if set(row) != expected_columns:
            raise ValueError(
                "Every result row must match declared columns."
            )

    profiles = []

    for column in columns:
        values = [
            row[column]
            for row in rows
        ]

        data_type = _infer_column_type(values)

        profiles.append(
            ColumnProfile(
                name=column,
                data_type=data_type,
                role=_infer_column_role(data_type),
                nullable=any(
                    value is None
                    for value in values
                ),
            )
        )

    return profiles
