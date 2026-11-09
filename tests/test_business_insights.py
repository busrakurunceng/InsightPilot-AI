
"""Tests for deterministic business insights."""

from decimal import Decimal

import pytest

from app.backend.analytics_contract import AnalyticsResponse
from app.backend.business_insights import generate_insights
from app.backend.result_profiler import profile_result


def make_response(columns, rows, truncated=False, profiles=None):
    if profiles is None:
        profiles = profile_result(columns, rows)

    return AnalyticsResponse(
        question="Test question",
        sql="SELECT 1",
        columns=columns,
        rows=rows,
        row_count=len(rows),
        truncated=truncated,
        column_profiles=profiles,
    )


def test_scalar_kpi():
    response = make_response(
        ["total_orders"],
        [{"total_orders": 99441}],
    )

    assert generate_insights(response) == [
        "total_orders: 99441."
    ]


def test_decimal_kpi():
    response = make_response(
        ["total_revenue"],
        [{"total_revenue": Decimal("1250.50")}],
    )

    assert generate_insights(response) == [
        "total_revenue: 1250.5."
    ]


def test_zero_kpi():
    response = make_response(
        ["total_orders"],
        [{"total_orders": 0}],
    )

    assert generate_insights(response) == [
        "total_orders: 0."
    ]


def test_negative_kpi():
    response = make_response(
        ["net_profit"],
        [{"net_profit": Decimal("-125.50")}],
    )

    assert generate_insights(response) == [
        "net_profit: -125.5."
    ]


def test_categorical_max_min_and_sum():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "RJ", "orders": 50},
            {"state": "MG", "orders": 35},
        ],
    )

    insights = generate_insights(response)

    assert insights == [
        "Highest orders: SP (100).",
        "Lowest orders: MG (35).",
        "Sum of returned orders values: 185.",
    ]


def test_decimal_category_values():
    response = make_response(
        ["state", "revenue"],
        [
            {"state": "SP", "revenue": Decimal("100.25")},
            {"state": "RJ", "revenue": Decimal("50.50")},
        ],
    )

    insights = generate_insights(response)

    assert "Highest revenue: SP (100.25)." in insights
    assert "Lowest revenue: RJ (50.5)." in insights
    assert "Sum of returned revenue values: 150.75." in insights


def test_ties_are_deterministic():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "RJ", "orders": 100},
            {"state": "MG", "orders": 50},
        ],
    )

    insights = generate_insights(response)

    assert insights[0] == "Highest orders: RJ (100)."
    assert insights[1] == "Lowest orders: MG (50)."


def test_truncated_result_avoids_comparison():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "RJ", "orders": 50},
        ],
        truncated=True,
    )

    insights = generate_insights(response)

    assert len(insights) == 1
    assert "truncated" in insights[0]


def test_empty_result():
    response = make_response(
        ["state", "orders"],
        [],
    )

    assert generate_insights(response) == [
        "The query returned no rows."
    ]


def test_missing_measure_is_excluded():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "RJ", "orders": None},
            {"state": "MG", "orders": 35},
        ],
    )

    insights = generate_insights(response)

    assert "Highest orders: SP (100)." in insights
    assert "Lowest orders: MG (35)." in insights
    assert not any(
        "Sum of returned" in insight
        for insight in insights
    )
    assert any(
        "1 row(s) were excluded" in insight
        for insight in insights
    )


def test_all_null_measures_produce_no_comparison():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": None},
            {"state": "RJ", "orders": None},
        ],
    )

    assert generate_insights(response) == []


def test_duplicate_categories_do_not_produce_sum():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
            {"state": "SP", "orders": 50},
        ],
    )

    insights = generate_insights(response)

    assert not any(
        "Sum of returned" in insight
        for insight in insights
    )


def test_multiple_measures_produce_no_insights():
    response = make_response(
        ["state", "orders", "revenue"],
        [
            {
                "state": "SP",
                "orders": 100,
                "revenue": 200,
            }
        ],
    )

    assert generate_insights(response) == []


def test_unprofiled_result_produces_no_insights():
    response = make_response(
        ["state", "orders"],
        [
            {"state": "SP", "orders": 100},
        ],
        profiles=[],
    )

    assert generate_insights(response) == []


def test_nonfinite_kpi_produces_no_insights():
    response = make_response(
        ["value"],
        [{"value": float("inf")}],
    )

    assert generate_insights(response) == []


def test_string_numeric_values_are_not_coerced():
    response = make_response(
        ["value"],
        [{"value": "100"}],
    )

    assert generate_insights(response) == []


def test_boolean_is_not_treated_as_numeric():
    response = make_response(
        ["flag"],
        [{"flag": True}],
    )

    assert generate_insights(response) == []


def test_does_not_mutate_rows():
    rows = [
        {"state": "SP", "orders": 100},
        {"state": "RJ", "orders": 50},
    ]

    response = make_response(
        ["state", "orders"],
        rows,
    )

    original = [dict(row) for row in rows]

    generate_insights(response)

    assert rows == original


def test_wrong_input_type():
    with pytest.raises(TypeError, match="AnalyticsResponse"):
        generate_insights({"rows": []})
