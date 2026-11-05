
import json
from unittest.mock import MagicMock

import pytest

from app.backend.evaluation_runner import (
    EvaluationRunner,
    load_benchmark,
    save_report,
)
from app.backend.sql_executor import SQLExecutionResult
from app.backend.text_to_sql_service import (
    SQLValidationPipelineError,
    TextToSQLResult,
)


def make_case(case_id="SQL_001"):
    return {
        "id": case_id,
        "question": "Toplam kaç sipariş var?",
        "reference_sql": (
            "SELECT COUNT(*) AS total_orders FROM orders;"
        ),
        "category": "basic",
        "difficulty": "easy",
        "comparison": "scalar",
    }


def make_execution(value=99441, truncated=False):
    return SQLExecutionResult(
        columns=["total_orders"],
        rows=[{"total_orders": value}],
        row_count=1,
        truncated=truncated,
    )


def make_generation(value=99441, truncated=False):
    return TextToSQLResult(
        question="Toplam kaç sipariş var?",
        sql="SELECT COUNT(*) FROM orders;",
        model="test-model",
        columns=["count"],
        rows=[{"count": value}],
        row_count=1,
        truncated=truncated,
        selected_chunk_ids=["table:orders"],
        dependency_chunk_ids=[],
    )


def make_runner(
    reference=None,
    generated=None,
):
    executor = MagicMock()
    service = MagicMock()

    executor.execute.return_value = (
        reference
        if reference is not None
        else make_execution()
    )

    service.run.return_value = (
        generated
        if generated is not None
        else make_generation()
    )

    return EvaluationRunner(
        service=service,
        reference_executor=executor,
    )


def test_correct_result():
    runner = make_runner()
    result = runner.evaluate_case(make_case())

    assert result.matched
    assert result.status == "correct"
    assert result.generated_sql is not None
    assert result.selected_chunk_ids == ["table:orders"]


def test_result_mismatch():
    runner = make_runner(
        generated=make_generation(123)
    )

    result = runner.evaluate_case(make_case())

    assert not result.matched
    assert result.status == "result_mismatch"


def test_generated_truncated():
    runner = make_runner(
        generated=make_generation(truncated=True)
    )

    result = runner.evaluate_case(make_case())

    assert not result.matched
    assert result.status == "truncated_result"


def test_reference_truncated():
    runner = make_runner(
        reference=make_execution(truncated=True)
    )

    result = runner.evaluate_case(make_case())

    assert result.status == "reference_error"
    assert not result.matched
    runner.service.run.assert_not_called()


def test_reference_execution_error():
    runner = make_runner()

    runner.reference_executor.execute.side_effect = (
        RuntimeError("Database unavailable")
    )

    result = runner.evaluate_case(make_case())

    assert result.status == "reference_error"
    assert result.error_type == "RuntimeError"
    runner.service.run.assert_not_called()


def test_validation_pipeline_error():
    runner = make_runner()

    runner.service.run.side_effect = (
        SQLValidationPipelineError("Invalid SQL")
    )

    result = runner.evaluate_case(make_case())

    assert result.status == "validation_error"
    assert not result.matched


def test_unexpected_pipeline_error():
    runner = make_runner()

    runner.service.run.side_effect = RuntimeError(
        "Unexpected problem"
    )

    result = runner.evaluate_case(make_case())

    assert result.status == "unexpected_error"


def test_report_accuracy(tmp_path):
    benchmark = {
        "benchmark_name": "Test Benchmark",
        "version": "0.1",
        "cases": [
            make_case("SQL_001"),
            make_case("SQL_002"),
        ],
    }

    path = tmp_path / "benchmark.json"
    path.write_text(
        json.dumps(benchmark),
        encoding="utf-8",
    )

    runner = make_runner()

    runner.service.run.side_effect = [
        make_generation(99441),
        make_generation(100),
    ]

    report = runner.run(path)

    assert report.total_cases == 2
    assert report.correct_cases == 1
    assert report.execution_accuracy == 0.5
    assert report.status_counts["correct"] == 1
    assert report.status_counts["result_mismatch"] == 1


def test_save_report(tmp_path):
    benchmark = {
        "benchmark_name": "Test Benchmark",
        "version": "0.1",
        "cases": [make_case()],
    }

    benchmark_path = tmp_path / "benchmark.json"
    benchmark_path.write_text(
        json.dumps(benchmark),
        encoding="utf-8",
    )

    runner = make_runner()
    report = runner.run(benchmark_path)

    output = tmp_path / "reports" / "report.json"

    save_report(report, output)

    saved = json.loads(
        output.read_text(encoding="utf-8")
    )

    assert saved["total_cases"] == 1
    assert saved["correct_cases"] == 1
    assert saved["execution_accuracy"] == 1.0
    assert saved["cases"][0]["status"] == "correct"


def test_duplicate_ids_rejected(tmp_path):
    benchmark = {
        "cases": [
            make_case("SQL_001"),
            make_case("SQL_001"),
        ]
    }

    path = tmp_path / "benchmark.json"
    path.write_text(
        json.dumps(benchmark),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate"):
        load_benchmark(path)


def test_invalid_comparison_rejected(tmp_path):
    case = make_case()
    case["comparison"] = "unknown"

    path = tmp_path / "benchmark.json"
    path.write_text(
        json.dumps({"cases": [case]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="comparison"):
        load_benchmark(path)


def test_empty_benchmark_rejected(tmp_path):
    path = tmp_path / "benchmark.json"
    path.write_text(
        json.dumps({"cases": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_benchmark(path)
