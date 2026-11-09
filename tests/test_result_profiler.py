
"""Tests for deterministic SQL result profiling."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.backend.result_profiler import profile_result


def test_numeric_integer_column():
    profiles = profile_result(
        ["total_orders"],
        [
            {"total_orders": 100},
            {"total_orders": 50},
        ],
    )

    assert profiles[0].data_type == "numeric"
    assert profiles[0].role == "measure"
    assert profiles[0].nullable is False


def test_numeric_float_column():
    profiles = profile_result(
        ["average_value"],
        [
            {"average_value": 120.5},
            {"average_value": 99.9},
        ],
    )

    assert profiles[0].data_type == "numeric"


def test_decimal_column():
    profiles = profile_result(
        ["revenue"],
        [
            {"revenue": Decimal("120.50")},
            {"revenue": Decimal("80.25")},
        ],
    )

    assert profiles[0].data_type == "numeric"
    assert profiles[0].role == "measure"


def test_mixed_numeric_types():
    profiles = profile_result(
        ["amount"],
        [
            {"amount": 10},
            {"amount": 12.5},
            {"amount": Decimal("14.25")},
        ],
    )

    assert profiles[0].data_type == "numeric"


def test_categorical_column():
    profiles = profile_result(
        ["customer_state"],
        [
            {"customer_state": "SP"},
            {"customer_state": "RJ"},
        ],
    )

    assert profiles[0].data_type == "categorical"
    assert profiles[0].role == "dimension"


def test_date_column():
    profiles = profile_result(
        ["order_date"],
        [
            {"order_date": date(2026, 1, 1)},
            {"order_date": date(2026, 1, 2)},
        ],
    )

    assert profiles[0].data_type == "datetime"
    assert profiles[0].role == "dimension"


def test_datetime_column():
    profiles = profile_result(
        ["created_at"],
        [
            {"created_at": datetime(2026, 1, 1, 10)},
            {"created_at": datetime(2026, 1, 2, 11)},
        ],
    )

    assert profiles[0].data_type == "datetime"


def test_boolean_column():
    profiles = profile_result(
        ["is_delivered"],
        [
            {"is_delivered": True},
            {"is_delivered": False},
        ],
    )

    assert profiles[0].data_type == "boolean"
    assert profiles[0].role == "dimension"


def test_nullable_numeric_column():
    profiles = profile_result(
        ["total_orders"],
        [
            {"total_orders": 100},
            {"total_orders": None},
        ],
    )

    assert profiles[0].data_type == "numeric"
    assert profiles[0].nullable is True


def test_all_null_column():
    profiles = profile_result(
        ["unknown_value"],
        [
            {"unknown_value": None},
            {"unknown_value": None},
        ],
    )

    assert profiles[0].data_type == "unknown"
    assert profiles[0].role == "unknown"
    assert profiles[0].nullable is True


def test_mixed_string_numeric_column():
    profiles = profile_result(
        ["mixed"],
        [
            {"mixed": "100"},
            {"mixed": 200},
        ],
    )

    assert profiles[0].data_type == "unknown"
    assert profiles[0].role == "unknown"


def test_unsupported_value_type():
    profiles = profile_result(
        ["metadata"],
        [
            {"metadata": {"key": "value"}},
        ],
    )

    assert profiles[0].data_type == "unknown"


def test_empty_rows():
    profiles = profile_result(
        ["customer_state", "total_orders"],
        [],
    )

    assert len(profiles) == 2
    assert all(
        profile.data_type == "unknown"
        for profile in profiles
    )
    assert all(
        profile.nullable is False
        for profile in profiles
    )


def test_empty_columns_and_rows():
    assert profile_result([], []) == []


def test_preserves_column_order():
    profiles = profile_result(
        ["state", "count", "date"],
        [
            {
                "state": "SP",
                "count": 100,
                "date": date(2026, 1, 1),
            }
        ],
    )

    assert [profile.name for profile in profiles] == [
        "state",
        "count",
        "date",
    ]


def test_does_not_modify_input_rows():
    rows = [
        {"state": "SP", "count": 100},
        {"state": "RJ", "count": None},
    ]

    original = [
        dict(row)
        for row in rows
    ]

    profile_result(
        ["state", "count"],
        rows,
    )

    assert rows == original


def test_duplicate_columns_rejected():
    with pytest.raises(ValueError, match="unique"):
        profile_result(
            ["state", "state"],
            [],
        )


def test_missing_column_rejected():
    with pytest.raises(ValueError, match="declared columns"):
        profile_result(
            ["state", "count"],
            [{"state": "SP"}],
        )


def test_extra_column_rejected():
    with pytest.raises(ValueError, match="declared columns"):
        profile_result(
            ["state"],
            [{"state": "SP", "count": 100}],
        )


def test_invalid_column_name_rejected():
    with pytest.raises(ValueError, match="Column names"):
        profile_result(
            [""],
            [],
        )


def test_invalid_rows_type_rejected():
    with pytest.raises(TypeError, match="Rows"):
        profile_result(
            ["state"],
            None,
        )


def test_invalid_row_object_rejected():
    with pytest.raises(TypeError, match="dictionary"):
        profile_result(
            ["state"],
            [["SP"]],
        )


def test_non_finite_float_is_unknown():
    profiles = profile_result(
        ["value"],
        [{"value": float("nan")}],
    )

    assert profiles[0].data_type == "unknown"


def test_non_finite_decimal_is_unknown():
    profiles = profile_result(
        ["value"],
        [{"value": Decimal("Infinity")}],
    )

    assert profiles[0].data_type == "unknown"
