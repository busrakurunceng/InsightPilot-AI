
import pytest

from app.backend.schema_dependencies import (
    load_semantics,
    metric_dependencies,
)


@pytest.fixture
def semantics():
    return load_semantics()


def test_late_delivery_rate_dependencies(semantics):
    """Geç teslimat metriği orders tablosuna bağlı olmalı."""

    result = metric_dependencies(
        "late_delivery_rate",
        semantics,
    )

    assert result == ["table:orders"]


def test_revenue_dependencies(semantics):
    """Gelir metriği hem order_items hem orders gerektirir."""

    result = metric_dependencies(
        "delivered_product_revenue",
        semantics,
    )

    assert "table:order_items" in result
    assert "table:orders" in result
    assert len(result) == 2


def test_aov_nested_dependencies(semantics):
    """AOV metriği gelir metriğinin bağımlılıklarını da almalı."""

    result = metric_dependencies(
        "delivered_order_aov",
        semantics,
    )

    assert "metric:delivered_product_revenue" in result
    assert "table:order_items" in result
    assert "table:orders" in result


def test_no_duplicate_dependencies(semantics):
    """Aynı bağımlılık birden fazla kez eklenmemeli."""

    result = metric_dependencies(
        "delivered_order_aov",
        semantics,
    )

    assert len(result) == len(set(result))


def test_unknown_metric_raises_error(semantics):
    """Tanımlanmamış metrikler sessizce kabul edilmemeli."""

    with pytest.raises(ValueError, match="Bilinmeyen metrik"):
        metric_dependencies(
            "nonexistent_metric",
            semantics,
        )


def test_total_orders_dependencies(semantics):
    """Toplam sipariş metriği yalnızca orders tablosunu gerektirir."""

    result = metric_dependencies(
        "total_orders",
        semantics,
    )

    assert result == ["table:orders"]
