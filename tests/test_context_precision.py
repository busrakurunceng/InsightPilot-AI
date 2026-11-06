
import pytest

from app.backend.context_selector import select_context


def make_chunk(chunk_id):
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_id.split(":")[0],
        "content": f"Context for {chunk_id}",
        "metadata": {},
        "similarity": 0.8,
    }


@pytest.mark.parametrize(
    ("question", "raw_ids", "expected_ids"),
    [
        (
            "Müşterilerin eyaletlere göre dağılımı nedir?",
            [
                "metric:delivered_product_revenue",
                "metric:late_delivery_rate",
                "table:customers",
                "metric:delivered_order_aov",
                "metric:total_orders",
            ],
            ["table:customers"],
        ),
        (
            "Ödeme kayıtlarındaki toplam ödeme tutarı nedir?",
            [
                "rule:revenue_caveat",
                "table:order_payments",
                "metric:delivered_product_revenue",
                "metric:delivered_order_aov",
                "rule:join_caveat",
            ],
            ["table:order_payments"],
        ),
        (
            "Ödeme kayıtlarının ortalama tutarı nedir?",
            [
                "metric:delivered_product_revenue",
                "rule:revenue_caveat",
                "metric:average_delivery_days",
                "metric:delivered_order_aov",
                "table:order_payments",
            ],
            ["table:order_payments"],
        ),
        (
            "São Paulo eyaletindeki müşterilerin verdiği toplam sipariş sayısı kaçtır?",
            [
                "metric:total_orders",
                "metric:delivered_product_revenue",
                "metric:late_delivery_rate",
                "metric:delivered_order_aov",
                "metric:average_delivery_days",
            ],
            ["metric:total_orders"],
        ),
        (
            "Her eyaletteki müşterilerin verdiği sipariş sayısını göster.",
            [
                "metric:delivered_order_aov",
                "metric:total_orders",
                "metric:delivered_product_revenue",
                "metric:average_delivery_days",
                "table:orders",
            ],
            ["metric:total_orders"],
        ),
    ],
)
def test_context_precision(question, raw_ids, expected_ids):
    raw_results = [
        make_chunk(chunk_id)
        for chunk_id in raw_ids
    ]

    selected = select_context(question, raw_results)

    assert [
        row["chunk_id"]
        for row in selected
    ] == expected_ids


def test_unknown_intent_preserves_semantic_results():
    raw_results = [
        make_chunk("table:products"),
        make_chunk("rule:date_filter"),
    ]

    selected = select_context(
        "Veri setinin yapısını açıkla.",
        raw_results,
    )

    assert selected == raw_results


def test_explicit_table_missing_from_raw_results():
    raw_results = [
        make_chunk("metric:delivered_product_revenue"),
        make_chunk("rule:revenue_caveat"),
    ]

    selected = select_context(
        "Ödeme kayıtlarını göster.",
        raw_results,
    )

    # Missing table will be loaded by enrich_context().
    assert selected == []


def test_empty_results():
    assert select_context("Toplam kaç sipariş var?", []) == []


def test_source_results_are_not_mutated():
    raw_results = [
        make_chunk("table:customers"),
        make_chunk("metric:late_delivery_rate"),
    ]

    original = [
        dict(row)
        for row in raw_results
    ]

    select_context(
        "Müşterilerin eyaletlere göre dağılımı nedir?",
        raw_results,
    )

    assert raw_results == original
