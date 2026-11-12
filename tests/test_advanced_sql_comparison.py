"""Focused comparison tests without database or LLM calls."""
from datetime import datetime
from types import SimpleNamespace

from scripts.evaluate_advanced_sql import compare_results


def result(columns, rows, truncated=False):
    return SimpleNamespace(columns=columns, rows=[dict(zip(columns, row)) for row in rows], truncated=truncated)


def test_monthly_equivalent_layouts_match():
    generated = result(["order_year", "order_month", "total_orders"], [(2018, 1, 7), (2018, 2, 9)])
    reference = result(["month", "order_count"], [(datetime(2018, 1, 1), 7), (datetime(2018, 2, 1), 9)])
    assert compare_results(generated, reference, False, "monthly")[0]


def test_monthly_wrong_count_fails():
    generated = result(["order_year", "order_month", "total_orders"], [(2018, 1, 8)])
    reference = result(["month", "order_count"], [(datetime(2018, 1, 1), 7)])
    assert not compare_results(generated, reference, False, "monthly")[0]


def test_monthly_wrong_year_fails():
    generated = result(["order_year", "order_month", "total_orders"], [(2017, 1, 7)])
    reference = result(["month", "order_count"], [(datetime(2018, 1, 1), 7)])
    assert not compare_results(generated, reference, False, "monthly")[0]


def test_monthly_missing_month_fails():
    generated = result(["order_year", "order_month", "total_orders"], [(2018, 1, 7)])
    reference = result(["month", "order_count"], [(datetime(2018, 1, 1), 7), (datetime(2018, 2, 1), 9)])
    assert not compare_results(generated, reference, False, "monthly")[0]


def test_monthly_invalid_month_fails():
    generated = result(["order_year", "order_month", "total_orders"], [(2018, 13, 7)])
    reference = result(["month", "order_count"], [(datetime(2018, 1, 1), 7)])
    assert not compare_results(generated, reference, False, "monthly")[0]


def test_default_comparison_remains_strict():
    generated = result(["order_year", "order_month", "total_orders"], [(2018, 1, 7)])
    reference = result(["month", "order_count"], [(datetime(2018, 1, 1), 7)])
    assert compare_results(generated, reference, False) == (False, "Different number of result columns")


def test_monthly_truncation_fails():
    generated = result(["order_year", "order_month", "total_orders"], [(2018, 1, 7)], truncated=True)
    reference = result(["month", "order_count"], [(datetime(2018, 1, 1), 7)])
    assert not compare_results(generated, reference, False, "monthly")[0]
