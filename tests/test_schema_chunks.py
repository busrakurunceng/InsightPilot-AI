"""Unit tests for schema retrieval chunk generation (no DB required)."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_schema_chunks.py"
spec = importlib.util.spec_from_file_location("build_schema_chunks", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    catalog = {"schema": "public", "tables": [
        {"name": "orders", "columns": [{"name": "order_id", "type": "text", "nullable": False}],
         "primary_key": ["order_id"], "foreign_keys": []}
    ]}
    semantics = {"schema": "public", "tables": {"orders": {"description": "Siparişler", "grain": "Bir satır bir sipariş"}},
                 "metrics": {"total_orders": {"description": "Toplam sipariş", "expression": "COUNT(*)"}},
                 "rules": {"date_filter": "Başlangıç dahil"}}
    return catalog, semantics


def test_chunk_types_and_ids():
    chunks = module.build_chunks(*sample())
    assert [c["id"] for c in chunks] == ["table:orders", "metric:total_orders", "rule:date_filter"]


def test_table_chunk_contains_columns_and_grain():
    chunks = module.build_chunks(*sample())
    assert "orders.order_id" in chunks[0]["text"]
    assert "Bir satır bir sipariş" in chunks[0]["text"]


def test_deterministic_output():
    assert module.build_chunks(*sample()) == module.build_chunks(*sample())


def test_schema_mismatch_fails():
    import pytest
    catalog, semantics = sample()
    semantics["schema"] = "wrong"
    with pytest.raises(ValueError, match="Schema mismatch"):
        module.build_chunks(catalog, semantics)
