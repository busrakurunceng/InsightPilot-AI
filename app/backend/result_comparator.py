
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from numbers import Number
from typing import Any, Mapping, Sequence


SUPPORTED_COMPARISONS = frozenset({
    "scalar",
    "unordered_rows",
    "ordered_rows",
})


@dataclass(frozen=True)
class ComparisonResult:
    matched: bool
    comparison: str
    expected_row_count: int
    actual_row_count: int
    reason: str


def _as_decimal(value: Any) -> Decimal | None:
    """Convert finite real numbers to comparable decimals."""
    if isinstance(value, bool):
        return None

    if not isinstance(value, Number):
        return None

    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

    return result if result.is_finite() else None


def _values_equal(
    expected: Any,
    actual: Any,
    tolerance: Decimal,
) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None

    if isinstance(expected, bool) or isinstance(actual, bool):
        return (
            isinstance(expected, bool)
            and isinstance(actual, bool)
            and expected == actual
        )

    expected_number = _as_decimal(expected)
    actual_number = _as_decimal(actual)

    if expected_number is not None and actual_number is not None:
        return abs(expected_number - actual_number) <= tolerance

    # Numeric values must not match text or unsupported numbers.
    if expected_number is not None or actual_number is not None:
        return False

    if isinstance(expected, Number) or isinstance(actual, Number):
        return False

    return (
        type(expected) is type(actual)
        and expected == actual
    )


def _row_values(
    row: Mapping[str, Any],
) -> tuple[Any, ...]:
    return tuple(row.values())


def _rows_equal(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    tolerance: Decimal,
) -> bool:
    left = _row_values(expected)
    right = _row_values(actual)

    if len(left) != len(right):
        return False

    return all(
        _values_equal(a, b, tolerance)
        for a, b in zip(left, right)
    )


def _unordered_rows_equal(
    expected: Sequence[Mapping[str, Any]],
    actual: Sequence[Mapping[str, Any]],
    tolerance: Decimal,
) -> bool:
    """
    Find a one-to-one matching between rows.

    This preserves duplicate counts and avoids incorrect
    greedy matching when numeric tolerance is enabled.
    """
    count = len(expected)

    if count != len(actual):
        return False

    candidates = [
        [
            j
            for j, actual_row in enumerate(actual)
            if _rows_equal(expected_row, actual_row, tolerance)
        ]
        for expected_row in expected
    ]

    if any(not matches for matches in candidates):
        return False

    matched_actual = [-1] * count

    def assign(
        expected_index: int,
        visited: set[int],
    ) -> bool:
        for actual_index in candidates[expected_index]:
            if actual_index in visited:
                continue

            visited.add(actual_index)

            previous = matched_actual[actual_index]

            if previous == -1 or assign(previous, visited):
                matched_actual[actual_index] = expected_index
                return True

        return False

    # Match the most constrained rows first.
    order = sorted(
        range(count),
        key=lambda i: len(candidates[i]),
    )

    for expected_index in order:
        if not assign(expected_index, set()):
            return False

    return True


def compare_results(
    expected_rows: Sequence[Mapping[str, Any]],
    actual_rows: Sequence[Mapping[str, Any]],
    comparison: str,
    *,
    expected_truncated: bool = False,
    actual_truncated: bool = False,
    numeric_tolerance: str = "0.000001",
) -> ComparisonResult:
    """
    Compare reference and generated SQL result sets.

    Column aliases are ignored, but column order is
    significant. Row order depends on comparison mode.
    """
    if comparison not in SUPPORTED_COMPARISONS:
        raise ValueError(
            f"Unsupported comparison mode: {comparison}"
        )

    try:
        tolerance = Decimal(numeric_tolerance)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(
            "Invalid numeric tolerance."
        ) from exc

    if not tolerance.is_finite() or tolerance < 0:
        raise ValueError(
            "Numeric tolerance must be finite and nonnegative."
        )

    expected_count = len(expected_rows)
    actual_count = len(actual_rows)

    def result(matched: bool, reason: str) -> ComparisonResult:
        return ComparisonResult(
            matched=matched,
            comparison=comparison,
            expected_row_count=expected_count,
            actual_row_count=actual_count,
            reason=reason,
        )

    if expected_truncated or actual_truncated:
        return result(False, "Result set is truncated.")

    if expected_count != actual_count:
        return result(False, "Row counts differ.")

    if comparison == "scalar":
        if expected_count != 1:
            return result(
                False,
                "Scalar comparison requires exactly one row.",
            )

        if (
            len(expected_rows[0]) != 1
            or len(actual_rows[0]) != 1
        ):
            return result(
                False,
                "Scalar comparison requires exactly one column.",
            )

        matched = _rows_equal(
            expected_rows[0],
            actual_rows[0],
            tolerance,
        )

    elif comparison == "ordered_rows":
        matched = all(
            _rows_equal(a, b, tolerance)
            for a, b in zip(expected_rows, actual_rows)
        )

    else:
        matched = _unordered_rows_equal(
            expected_rows,
            actual_rows,
            tolerance,
        )

    return result(
        matched,
        "Results match." if matched else "Result values differ.",
    )
