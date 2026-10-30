
import json

import pytest

from scripts.evaluate_retrieval import (
    load_benchmark,
    summarize,
    group_summaries,
)


def test_benchmark_contains_25_questions():
    cases = load_benchmark()

    assert len(cases) == 25
    assert len({case["id"] for case in cases}) == 25


def test_benchmark_categories():
    cases = load_benchmark()

    categories = {case["category"] for case in cases}

    assert categories == {
        "baseline",
        "paraphrase",
        "business_semantics",
        "relationships",
        "complex",
    }


def test_benchmark_expected_chunks_exist():
    from app.backend.schema_dependencies import load_semantics

    semantics = load_semantics()

    known_ids = (
        {f"table:{name}" for name in semantics["tables"]}
        | {f"metric:{name}" for name in semantics["metrics"]}
        | {f"rule:{name}" for name in semantics["rules"]}
    )

    for case in load_benchmark():
        assert set(case["expected"]) <= known_ids, case["id"]


def test_duplicate_ids_are_rejected(tmp_path):
    path = tmp_path / "benchmark.json"

    path.write_text(
        json.dumps({
            "cases": [
                {
                    "id": "Q01",
                    "category": "baseline",
                    "difficulty": "supported",
                    "question": "Test question",
                    "expected": ["table:orders"],
                },
                {
                    "id": "Q01",
                    "category": "baseline",
                    "difficulty": "supported",
                    "question": "Another question",
                    "expected": ["table:orders"],
                },
            ]
        }),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tekrarlanan"):
        load_benchmark(path)


def test_summary_metrics():
    results = [
        {
            "category": "baseline",
            "difficulty": "supported",
            "raw_recall_at_5": 0.5,
            "context_recall": 1.0,
            "context_precision": 1.0,
        },
        {
            "category": "complex",
            "difficulty": "challenge",
            "raw_recall_at_5": 0.0,
            "context_recall": 0.5,
            "context_precision": 0.5,
        },
    ]

    summary = summarize(results)

    assert summary["total_questions"] == 2
    assert summary["mean_raw_recall_at_5"] == 0.25
    assert summary["mean_context_recall"] == 0.75
    assert summary["mean_context_precision"] == 0.75
    assert summary["full_context_recall_count"] == 1
    assert summary["perfect_context_count"] == 1

    grouped = group_summaries(results, "difficulty")

    assert grouped["supported"]["mean_context_recall"] == 1.0
    assert grouped["challenge"]["mean_context_recall"] == 0.5
