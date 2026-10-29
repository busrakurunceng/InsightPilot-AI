"""Unit tests for embedding input/output validation; no model download needed."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_embeddings.py"
spec = importlib.util.spec_from_file_location("build_embeddings", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_load_chunks(tmp_path):
    path = tmp_path / "chunks.json"
    path.write_text(json.dumps([{"id": "table:orders", "text": "Orders table"}]), encoding="utf-8")
    assert module.load_chunks(path)[0]["id"] == "table:orders"


def test_reject_duplicate_ids(tmp_path):
    path = tmp_path / "chunks.json"
    path.write_text(json.dumps([{"id": "a", "text": "x"}, {"id": "a", "text": "y"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        module.load_chunks(path)


def test_accept_normalized_vectors():
    vectors = np.zeros((2, 384), dtype=np.float32)
    vectors[:, 0] = 1.0
    module.validate_embeddings(vectors, 2)


def test_reject_wrong_dimensions():
    with pytest.raises(ValueError, match="Expected"):
        module.validate_embeddings(np.ones((2, 3), dtype=np.float32), 2)


def test_reject_nan_vectors():
    vectors = np.zeros((1, 384), dtype=np.float32)
    vectors[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        module.validate_embeddings(vectors, 1)


def test_reject_non_normalized_vectors():
    vectors = np.ones((1, 384), dtype=np.float32)
    with pytest.raises(ValueError, match="normalized"):
        module.validate_embeddings(vectors, 1)
