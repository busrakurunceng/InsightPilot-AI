"""Module 1 regression checks.

Unit tests run without a database. Optional integration checks run against the
local Olist database when RUN_DB_TESTS=1 is set in the environment.
"""
import os
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.backend import analytics


def test_inclusive_single_day_bounds():
    params = analytics.date_parameters(date(2016, 9, 4), date(2016, 9, 4))
    assert params == {
        "start_ts": datetime(2016, 9, 4),
        "end_ts": datetime(2016, 9, 5),
    }


def test_inclusive_multi_day_bounds():
    params = analytics.date_parameters(date(2018, 1, 1), date(2018, 3, 31))
    assert params["start_ts"] == datetime(2018, 1, 1)
    assert params["end_ts"] == datetime(2018, 4, 1)


@pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="Set RUN_DB_TESTS=1 to check the local PostgreSQL database")
def test_full_dataset_reference_metrics():
    start_date, end_date = analytics.get_date_bounds()
    kpis = analytics.get_core_kpis(start_date, end_date)
    delivery = analytics.get_delivery_performance(start_date, end_date)
    monthly = analytics.get_monthly_revenue(start_date, end_date)
    status = analytics.get_order_status_distribution(start_date, end_date)
    products = analytics.get_top_products(start_date, end_date)
    sellers = analytics.get_top_sellers(start_date, end_date)

    assert int(kpis["total_orders"]) == 99_441
    assert int(kpis["delivered_orders"]) == 96_478
    assert Decimal(str(kpis["total_revenue"])).quantize(Decimal("0.01")) == Decimal("13221498.11")
    assert Decimal(str(kpis["average_order_value"])).quantize(Decimal("0.01")) == Decimal("137.04")
    assert len(monthly) == 23
    assert round(float(monthly["monthly_revenue"].sum()), 2) == 13_221_498.11
    assert int(status["order_count"].sum()) == 99_441
    assert len(status) == 8
    assert len(products) == 10 and len(sellers) == 10
    assert int(delivery["evaluated_deliveries"]) == 96_470
    assert int(delivery["late_deliveries"]) == 7_826
    assert Decimal(str(delivery["avg_delivery_days"])) == Decimal("12.56")
    assert Decimal(str(delivery["late_delivery_rate"])) == Decimal("8.11")


@pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="Set RUN_DB_TESTS=1 to check the local PostgreSQL database")
def test_selected_date_range_consistency():
    start_date, end_date = date(2018, 1, 1), date(2018, 3, 31)
    kpis = analytics.get_core_kpis(start_date, end_date)
    monthly = analytics.get_monthly_revenue(start_date, end_date)
    status = analytics.get_order_status_distribution(start_date, end_date)
    assert int(status["order_count"].sum()) == int(kpis["total_orders"])
    assert round(float(monthly["monthly_revenue"].sum()), 2) == round(float(kpis["total_revenue"]), 2)
