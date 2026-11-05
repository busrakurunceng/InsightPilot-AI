
from decimal import Decimal

import pytest

from app.backend.result_comparator import compare_results


def compare(expected, actual, mode="unordered_rows", **kwargs):
    return compare_results(
        expected,
        actual,
        mode,
        **kwargs,
    )


def test_scalar_same_value_different_alias():
    result = compare(
        [{"total_orders": 99441}],
        [{"count": 99441}],
        "scalar",
    )
    assert result.matched


def test_scalar_different_values():
    result = compare(
        [{"count": 100}],
        [{"count": 99}],
        "scalar",
    )
    assert not result.matched


def test_scalar_integer_and_decimal():
    result = compare(
        [{"total": Decimal("10.0")}],
        [{"total": 10}],
        "scalar",
    )
    assert result.matched


def test_scalar_numeric_tolerance():
    result = compare(
        [{"avg": Decimal("10.0000001")}],
        [{"avg": 10.0}],
        "scalar",
    )
    assert result.matched


def test_scalar_outside_tolerance():
    result = compare(
        [{"avg": 10.01}],
        [{"avg": 10.0}],
        "scalar",
    )
    assert not result.matched


def test_null_does_not_equal_zero():
    result = compare(
        [{"value": None}],
        [{"value": 0}],
        "scalar",
    )
    assert not result.matched


def test_null_equals_null():
    result = compare(
        [{"value": None}],
        [{"value": None}],
        "scalar",
    )
    assert result.matched


def test_boolean_not_equal_integer():
    result = compare(
        [{"value": True}],
        [{"value": 1}],
        "scalar",
    )
    assert not result.matched


def test_numeric_string_not_equal_number():
    result = compare(
        [{"value": "10"}],
        [{"value": 10}],
        "scalar",
    )
    assert not result.matched


def test_unordered_rows_different_order():
    result = compare(
        [{"state": "SP", "count": 5},
         {"state": "RJ", "count": 3}],
        [{"region": "RJ", "total": 3},
         {"region": "SP", "total": 5}],
    )
    assert result.matched


def test_ordered_rows_different_order():
    result = compare(
        [{"state": "SP"}, {"state": "RJ"}],
        [{"state": "RJ"}, {"state": "SP"}],
        "ordered_rows",
    )
    assert not result.matched


def test_ordered_rows_same_order():
    result = compare(
        [{"state": "SP"}, {"state": "RJ"}],
        [{"region": "SP"}, {"region": "RJ"}],
        "ordered_rows",
    )
    assert result.matched


def test_duplicate_rows_preserved():
    result = compare(
        [{"value": 1}, {"value": 1}],
        [{"value": 1}, {"value": 2}],
    )
    assert not result.matched


def test_duplicate_rows_equal():
    result = compare(
        [{"value": 1}, {"value": 1}],
        [{"value": 1}, {"value": 1}],
    )
    assert result.matched


def test_missing_row():
    result = compare(
        [{"value": 1}, {"value": 2}],
        [{"value": 1}],
    )
    assert not result.matched


def test_extra_row():
    result = compare(
        [{"value": 1}],
        [{"value": 1}, {"value": 2}],
    )
    assert not result.matched


def test_truncated_actual_rejected():
    result = compare(
        [{"value": 1}],
        [{"value": 1}],
        actual_truncated=True,
    )
    assert not result.matched


def test_truncated_reference_rejected():
    result = compare(
        [{"value": 1}],
        [{"value": 1}],
        expected_truncated=True,
    )
    assert not result.matched


def test_scalar_multiple_rows_rejected():
    result = compare(
        [{"value": 1}, {"value": 2}],
        [{"value": 1}, {"value": 2}],
        "scalar",
    )
    assert not result.matched


def test_scalar_multiple_columns_rejected():
    result = compare(
        [{"a": 1, "b": 2}],
        [{"a": 1, "b": 2}],
        "scalar",
    )
    assert not result.matched


def test_empty_unordered_results_match():
    result = compare([], [])
    assert result.matched


def test_empty_ordered_results_match():
    result = compare([], [], "ordered_rows")
    assert result.matched


def test_empty_scalar_results_rejected():
    result = compare([], [], "scalar")
    assert not result.matched


def test_column_order_matters():
    result = compare(
        [{"state": "SP", "count": 5}],
        [{"count": 5, "state": "SP"}],
    )
    assert not result.matched


def test_one_to_one_matching_with_tolerance():
    result = compare(
        [{"value": 0.0}, {"value": 0.0000015}],
        [{"value": 0.0000008}, {"value": 0.0}],
    )
    assert result.matched


@pytest.mark.parametrize(
    "tolerance",
    ["-1", "NaN", "Infinity", "invalid"],
)
def test_invalid_tolerance_rejected(tolerance):
    with pytest.raises(ValueError):
        compare(
            [{"value": 1}],
            [{"value": 1}],
            numeric_tolerance=tolerance,
        )


def test_invalid_comparison_mode():
    with pytest.raises(ValueError):
        compare(
            [{"value": 1}],
            [{"value": 1}],
            "unknown",
        )


def test_result_metadata():
    result = compare(
        [{"value": 1}],
        [{"value": 2}],
        "scalar",
    )

    assert result.comparison == "scalar"
    assert result.expected_row_count == 1
    assert result.actual_row_count == 1
    assert result.reason == "Result values differ."
