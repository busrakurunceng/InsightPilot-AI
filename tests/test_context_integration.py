
from unittest.mock import MagicMock

from scripts.search_schema import enrich_context


def make_result(chunk_id, similarity=0.5):
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_id.split(":")[0],
        "similarity": similarity,
        "content": f"Content for {chunk_id}",
        "metadata": {},
    }


def mock_engine_with_chunks(chunk_ids):
    engine = MagicMock()

    rows = [
        make_result(chunk_id)
        for chunk_id in chunk_ids
    ]

    connection = (
        engine.connect.return_value.__enter__.return_value
    )

    connection.execute.return_value.mappings.return_value.all.return_value = rows

    return engine


def test_order_count_filters_irrelevant_metrics():
    results = [
        make_result("metric:total_orders", 0.45),
        make_result("table:orders", 0.44),
        make_result("metric:average_delivery_days", 0.43),
        make_result("metric:delivered_order_aov", 0.42),
        make_result("rule:join_caveat", 0.41),
    ]

    engine = mock_engine_with_chunks([
        "table:orders",
    ])

    semantic, dependencies = enrich_context(
        results,
        engine,
        question="Toplam kaç sipariş var?",
    )

    ids = {
        row["chunk_id"]
        for row in semantic + dependencies
    }

    assert ids == {
        "metric:total_orders",
        "table:orders",
    }

    assert [
        row["chunk_id"]
        for row in semantic
    ] == ["metric:total_orders"]


def test_aov_preserves_nested_dependencies():
    results = [
        make_result("rule:revenue_caveat", 0.26),
        make_result("metric:average_delivery_days", 0.20),
        make_result("metric:delivered_product_revenue", 0.19),
        make_result("metric:delivered_order_aov", 0.18),
        make_result("metric:total_orders", 0.14),
    ]

    engine = mock_engine_with_chunks([
        "metric:delivered_product_revenue",
        "table:orders",
        "table:order_items",
    ])

    semantic, dependencies = enrich_context(
        results,
        engine,
        question="Sipariş başına ortalama gelir nedir?",
    )

    ids = {
        row["chunk_id"]
        for row in semantic + dependencies
    }

    assert ids == {
        "metric:delivered_order_aov",
        "metric:delivered_product_revenue",
        "table:orders",
        "table:order_items",
    }


def test_join_question_preserves_required_tables():
    results = [
        make_result("rule:revenue_caveat", 0.43),
        make_result("rule:join_caveat", 0.41),
        make_result("table:order_payments", 0.29),
        make_result("metric:delivered_product_revenue", 0.25),
        make_result("metric:delivered_order_aov", 0.24),
    ]

    engine = mock_engine_with_chunks([
        "table:orders",
        "table:order_items",
        "table:order_payments",
    ])

    semantic, dependencies = enrich_context(
        results,
        engine,
        question=(
            "Sipariş ve ödeme tablolarını "
            "birleştirirken nelere dikkat etmeliyiz?"
        ),
    )

    ids = {
        row["chunk_id"]
        for row in semantic + dependencies
    }

    assert ids == {
        "rule:join_caveat",
        "table:orders",
        "table:order_items",
        "table:order_payments",
    }


def test_unknown_intent_uses_fallback():
    results = [
        make_result("table:customers", 0.52),
        make_result("table:orders", 0.31),
    ]

    engine = mock_engine_with_chunks([])

    semantic, dependencies = enrich_context(
        results,
        engine,
        question=(
            "Müşterilerin hangi şehirlerde "
            "yaşadığını göster."
        ),
    )

    assert semantic == results
    assert dependencies == []
