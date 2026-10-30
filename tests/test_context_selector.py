
from app.backend.context_selector import select_context


def make_result(chunk_id, similarity=0.5):
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_id.split(":")[0],
        "similarity": similarity,
        "content": f"Content for {chunk_id}",
        "metadata": {},
    }


def test_selects_primary_metric_only():
    results = [
        make_result("metric:total_orders", 0.45),
        make_result("table:orders", 0.44),
        make_result("metric:average_delivery_days", 0.43),
        make_result("metric:delivered_order_aov", 0.42),
        make_result("rule:join_caveat", 0.41),
    ]

    selected = select_context(
        "Toplam kaç sipariş var?",
        results,
    )

    assert [
        row["chunk_id"]
        for row in selected
    ] == ["metric:total_orders"]


def test_selects_aov_instead_of_other_metrics():
    results = [
        make_result("rule:revenue_caveat", 0.26),
        make_result("metric:average_delivery_days", 0.20),
        make_result("metric:delivered_product_revenue", 0.19),
        make_result("metric:delivered_order_aov", 0.18),
        make_result("metric:total_orders", 0.14),
    ]

    selected = select_context(
        "Sipariş başına ortalama gelir nedir?",
        results,
    )

    assert [
        row["chunk_id"]
        for row in selected
    ] == ["metric:delivered_order_aov"]


def test_selects_join_rule_only():
    results = [
        make_result("rule:revenue_caveat", 0.43),
        make_result("rule:join_caveat", 0.41),
        make_result("table:order_payments", 0.29),
        make_result("metric:delivered_product_revenue", 0.25),
        make_result("metric:delivered_order_aov", 0.24),
    ]

    selected = select_context(
        "Sipariş ve ödeme tablolarını birleştirirken nelere dikkat etmeliyiz?",
        results,
    )

    assert [
        row["chunk_id"]
        for row in selected
    ] == ["rule:join_caveat"]


def test_unknown_intent_keeps_semantic_results():
    results = [
        make_result("table:customers", 0.52),
        make_result("table:orders", 0.31),
    ]

    selected = select_context(
        "Müşterilerin hangi şehirlerde yaşadığını göster.",
        results,
    )

    assert selected == results


def test_empty_results():
    assert select_context(
        "Toplam kaç sipariş var?",
        [],
    ) == []


def test_does_not_modify_original_results():
    results = [
        make_result("metric:total_orders", 0.45),
        make_result("metric:average_delivery_days", 0.43),
    ]

    original = [
        dict(result)
        for result in results
    ]

    select_context(
        "Toplam kaç sipariş var?",
        results,
    )

    assert results == original


def test_join_rule_takes_priority():
    results = [
        make_result("metric:total_orders", 0.50),
        make_result("rule:join_caveat", 0.40),
    ]

    selected = select_context(
        "Toplam sipariş sayısını hesaplarken tabloları nasıl birleştiririz?",
        results,
    )

    assert [
        row["chunk_id"]
        for row in selected
    ] == ["rule:join_caveat"]
