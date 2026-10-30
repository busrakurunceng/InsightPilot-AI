
import pytest

from app.backend.schema_relevance import (
    normalize_text,
    intent_score,
    select_primary_metric,
)


def make_metric_result(metric_name, similarity=0.5):
    return {
        "chunk_id": f"metric:{metric_name}",
        "chunk_type": "metric",
        "similarity": similarity,
    }


def make_rule_result(rule_name, similarity=0.5):
    return {
        "chunk_id": f"rule:{rule_name}",
        "chunk_type": "rule",
        "similarity": similarity,
    }


def test_normalize_turkish_text():
    result = normalize_text(
        "SİPARİŞ Başına ORTALAMA Gelir Nedir?"
    )

    assert result == "siparis basina ortalama gelir nedir"


def test_total_orders_intent():
    results = [
        make_metric_result("average_delivery_days", 0.60),
        make_metric_result("total_orders", 0.45),
        make_metric_result("delivered_order_aov", 0.42),
    ]

    selected = select_primary_metric(
        "Toplam kaç sipariş var?",
        results,
    )

    assert selected == "metric:total_orders"


def test_revenue_intent():
    results = [
        make_rule_result("join_caveat", 0.41),
        make_metric_result("delivered_product_revenue", 0.38),
        make_metric_result("delivered_order_aov", 0.35),
        make_metric_result("late_delivery_rate", 0.33),
    ]

    selected = select_primary_metric(
        "Teslim edilen siparişlerden ne kadar gelir elde ettik?",
        results,
    )

    assert selected == "metric:delivered_product_revenue"


def test_aov_intent_even_when_ranked_lower():
    results = [
        make_rule_result("revenue_caveat", 0.26),
        make_metric_result("average_delivery_days", 0.20),
        make_metric_result("delivered_product_revenue", 0.19),
        make_metric_result("delivered_order_aov", 0.18),
        make_metric_result("total_orders", 0.14),
    ]

    selected = select_primary_metric(
        "Sipariş başına ortalama gelir nedir?",
        results,
    )

    assert selected == "metric:delivered_order_aov"


def test_late_delivery_intent():
    results = [
        make_metric_result("delivered_product_revenue", 0.50),
        make_metric_result("late_delivery_rate", 0.32),
    ]

    selected = select_primary_metric(
        "Siparişlerin yüzde kaçı geç teslim edildi?",
        results,
    )

    assert selected == "metric:late_delivery_rate"


def test_average_delivery_days_intent():
    results = [
        make_metric_result("total_orders", 0.60),
        make_metric_result("average_delivery_days", 0.30),
    ]

    selected = select_primary_metric(
        "Ortalama teslimat süresi kaç gün?",
        results,
    )

    assert selected == "metric:average_delivery_days"


def test_unrelated_question_returns_none():
    results = [
        make_rule_result("join_caveat", 0.40),
        make_metric_result("total_orders", 0.30),
    ]

    selected = select_primary_metric(
        "Müşterilerin hangi şehirlerde yaşadığını göster.",
        results,
    )

    assert selected is None


def test_unknown_metric_has_zero_score():
    score = intent_score(
        "Toplam kaç sipariş var?",
        "nonexistent_metric",
    )

    assert score == 0


def test_no_metric_candidates_returns_none():
    results = [
        make_rule_result("join_caveat", 0.60),
        make_rule_result("revenue_caveat", 0.50),
    ]

    selected = select_primary_metric(
        "Sipariş sayısı kaç?",
        results,
    )

    assert selected is None


def test_empty_results_returns_none():
    selected = select_primary_metric(
        "Toplam kaç sipariş var?",
        [],
    )

    assert selected is None
