
from unittest.mock import MagicMock, patch

import pytest

from scripts.search_schema import enrich_context


def make_result(chunk_id, chunk_type, similarity=0.8):
    """Semantic search sonucunu taklit eder."""
    return {
        "chunk_id": chunk_id,
        "chunk_type": chunk_type,
        "content": f"Content for {chunk_id}",
        "metadata": {},
        "similarity": similarity,
    }


def make_engine(records):
    """
    PostgreSQL bağlantısını taklit eder.

    records: Veritabanından dönecek kayıtların sözlüğü.
    """
    engine = MagicMock()

    connection = engine.connect.return_value.__enter__.return_value

    def execute_query(query, params):
        requested_ids = params["chunk_ids"]

        rows = [
            records[chunk_id]
            for chunk_id in requested_ids
            if chunk_id in records
        ]

        result = MagicMock()
        result.mappings.return_value.all.return_value = rows
        return result

    connection.execute.side_effect = execute_query

    return engine


def test_adds_required_tables():
    """Gelir metriğinin ihtiyaç duyduğu tablolar eklenmeli."""

    results = [
        make_result("metric:delivered_product_revenue", "metric")
    ]

    records = {
        "table:order_items": make_result(
            "table:order_items", "table"
        ),
        "table:orders": make_result(
            "table:orders", "table"
        ),
    }

    engine = make_engine(records)

    semantic, dependencies = enrich_context(results, engine)

    assert len(semantic) == 1

    assert {
        row["chunk_id"] for row in dependencies
    } == {
        "table:order_items",
        "table:orders",
    }


def test_does_not_duplicate_existing_chunks():
    """Semantic sonuçlarda bulunan tablo tekrar eklenmemeli."""

    results = [
        make_result("metric:late_delivery_rate", "metric"),
        make_result("table:orders", "table"),
    ]

    engine = make_engine({})

    semantic, dependencies = enrich_context(results, engine)

    assert len(semantic) == 2
    assert dependencies == []

    engine.connect.assert_not_called()


def test_no_metric_returns_no_dependencies():
    """Metrik bulunmadığında enrichment yapılmamalı."""

    results = [
        make_result("rule:date_filter", "rule"),
        make_result("table:orders", "table"),
    ]

    engine = make_engine({})

    semantic, dependencies = enrich_context(results, engine)

    assert len(semantic) == 2
    assert dependencies == []

    engine.connect.assert_not_called()


def test_resolves_nested_metric_dependencies():
    """AOV metriği gelir metriği üzerinden tabloları bulmalı."""

    results = [
        make_result("metric:delivered_order_aov", "metric")
    ]

    records = {
        "metric:delivered_product_revenue": make_result(
            "metric:delivered_product_revenue", "metric"
        ),
        "table:order_items": make_result(
            "table:order_items", "table"
        ),
        "table:orders": make_result(
            "table:orders", "table"
        ),
    }

    engine = make_engine(records)

    semantic, dependencies = enrich_context(results, engine)

    assert len(semantic) == 1

    assert {
        row["chunk_id"] for row in dependencies
    } == {
        "metric:delivered_product_revenue",
        "table:order_items",
        "table:orders",
    }


def test_missing_dependency_raises_error():
    """PostgreSQL'de eksik bağımlılık varsa hata verilmeli."""

    results = [
        make_result("metric:late_delivery_rate", "metric")
    ]

    # orders kaydı bilinçli olarak eksik.
    engine = make_engine({})

    with pytest.raises(
        ValueError,
        match="PostgreSQL'de bağımlılık chunk'ları bulunamadı",
    ):
        enrich_context(results, engine)
