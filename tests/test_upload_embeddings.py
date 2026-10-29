import importlib.util
from pathlib import Path
import numpy as np
import pytest

FILE = Path(__file__).resolve().parents[1] / "scripts" / "upload_embeddings.py"
spec = importlib.util.spec_from_file_location("upload_embeddings", FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    chunks = [{"id": "table:orders", "kind": "table", "text": "Orders schema"}]
    vectors = np.zeros((1, 384), dtype=np.float32)
    vectors[0, 0] = 1.0
    meta = {"chunk_ids": ["table:orders"], "dimensions": 384, "model": "test-model"}
    return chunks, vectors, meta


def test_valid_row():
    rows = module.prepare_rows(*fixture())
    assert len(rows) == 1
    assert rows[0]["chunk_id"] == "table:orders"
    assert rows[0]["embedding"].startswith("[1,")


def test_wrong_id_order_rejected():
    chunks, vectors, meta = fixture()
    meta["chunk_ids"] = ["table:customers"]
    with pytest.raises(ValueError, match="metadata"):
        module.prepare_rows(chunks, vectors, meta)


def test_wrong_dimension_rejected():
    chunks, vectors, meta = fixture()
    with pytest.raises(ValueError, match="384"):
        module.prepare_rows(chunks, vectors[:, :3], meta)


def test_nonfinite_rejected():
    chunks, vectors, meta = fixture()
    vectors[0, 2] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        module.prepare_rows(chunks, vectors, meta)


def test_duplicate_id_rejected():
    chunks, vectors, meta = fixture()
    with pytest.raises(ValueError, match="unique"):
        module.prepare_rows(chunks * 2, np.vstack([vectors, vectors]), {**meta, "chunk_ids": ["table:orders"] * 2})
