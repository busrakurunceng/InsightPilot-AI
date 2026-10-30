
import pytest

from scripts.evaluate_retrieval import calculate_metrics


def test_raw_recall_uses_raw_results():
    metrics = calculate_metrics(
        expected=["metric:a", "table:b"],
        raw_ids=["metric:a", "rule:c"],
        final_ids=["metric:a", "table:b"],
    )

    assert metrics["raw_recall_at_5"] == 0.5
    assert metrics["context_recall"] == 1.0
    assert metrics["context_precision"] == 1.0


def test_extra_chunks_reduce_precision():
    metrics = calculate_metrics(
        expected=["metric:a", "table:b"],
        raw_ids=["metric:a"],
        final_ids=["metric:a", "table:b", "rule:c"],
    )

    assert metrics["context_recall"] == 1.0
    assert metrics["context_precision"] == 0.6667
    assert metrics["extra"] == ["rule:c"]


def test_missing_chunks_reduce_context_recall():
    metrics = calculate_metrics(
        expected=["metric:a", "table:b"],
        raw_ids=["metric:a"],
        final_ids=["metric:a"],
    )

    assert metrics["context_recall"] == 0.5
    assert metrics["context_precision"] == 1.0
    assert metrics["missing"] == ["table:b"]


def test_empty_final_context():
    metrics = calculate_metrics(
        expected=["metric:a"],
        raw_ids=["metric:a"],
        final_ids=[],
    )

    assert metrics["raw_recall_at_5"] == 1.0
    assert metrics["context_recall"] == 0.0
    assert metrics["context_precision"] == 0.0


def test_duplicate_chunks_do_not_inflate_metrics():
    metrics = calculate_metrics(
        expected=["metric:a", "table:b"],
        raw_ids=["metric:a", "metric:a"],
        final_ids=["metric:a", "table:b", "table:b"],
    )

    assert metrics["raw_recall_at_5"] == 0.5
    assert metrics["context_recall"] == 1.0
    assert metrics["context_precision"] == 1.0


def test_empty_expected_is_rejected():
    with pytest.raises(ValueError):
        calculate_metrics(
            expected=[],
            raw_ids=["metric:a"],
            final_ids=["metric:a"],
        )
