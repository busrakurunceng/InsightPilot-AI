
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.backend.result_comparator import compare_results
from app.backend.sql_executor import SQLExecutor
from app.backend.text_to_sql_service import (
    InsufficientContextError,
    OLIST_ALLOWED_TABLES,
    SQLExecutionPipelineError,
    SQLGenerationPipelineError,
    SQLValidationPipelineError,
    TextToSQLService,
)


VALID_COMPARISONS = {
    "scalar",
    "unordered_rows",
    "ordered_rows",
}


@dataclass(frozen=True)
class EvaluationCaseResult:
    case_id: str
    question: str
    category: str
    difficulty: str
    status: str
    matched: bool
    generated_sql: str | None
    reference_row_count: int | None
    generated_row_count: int | None
    selected_chunk_ids: list[str]
    dependency_chunk_ids: list[str]
    error_type: str | None
    reason: str


@dataclass(frozen=True)
class EvaluationReport:
    benchmark_name: str
    benchmark_version: str
    evaluated_at: str
    total_cases: int
    correct_cases: int
    execution_accuracy: float
    status_counts: dict[str, int]
    cases: list[EvaluationCaseResult]


def load_benchmark(path: str | Path) -> dict[str, Any]:
    """Load and structurally validate a benchmark."""
    with Path(path).open(encoding="utf-8") as file:
        benchmark = json.load(file)

    if not isinstance(benchmark, dict):
        raise ValueError("Benchmark must be a JSON object.")

    cases = benchmark.get("cases")

    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark must contain cases.")

    required_fields = {
        "id",
        "question",
        "reference_sql",
        "category",
        "difficulty",
        "comparison",
    }

    seen_ids: set[str] = set()

    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Each case must be an object.")

        missing = required_fields - set(case)

        if missing:
            raise ValueError(
                f"Benchmark case is missing: {sorted(missing)}"
            )

        case_id = case["id"]

        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("Case ID must be a nonempty string.")

        if case_id in seen_ids:
            raise ValueError(f"Duplicate case ID: {case_id}")

        seen_ids.add(case_id)

        for field in (
            "question",
            "reference_sql",
            "category",
            "difficulty",
        ):
            value = case[field]

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{case_id}: invalid {field}"
                )

        if case["comparison"] not in VALID_COMPARISONS:
            raise ValueError(
                f"{case_id}: invalid comparison mode"
            )

    return benchmark


class EvaluationRunner:
    """Evaluate Text-to-SQL using reference query results."""

    def __init__(
        self,
        service: TextToSQLService | None = None,
        reference_executor: SQLExecutor | None = None,
    ):
        self.service = (
            service
            if service is not None
            else TextToSQLService()
        )

        self.reference_executor = (
            reference_executor
            if reference_executor is not None
            else SQLExecutor(
                allowed_tables=set(OLIST_ALLOWED_TABLES),
                max_rows=1000,
                timeout_ms=10000,
            )
        )

    def evaluate_case(
        self,
        case: dict[str, Any],
    ) -> EvaluationCaseResult:
        case_id = case["id"]
        question = case["question"]

        common = {
            "case_id": case_id,
            "question": question,
            "category": case["category"],
            "difficulty": case["difficulty"],
        }

        # A reference failure is a benchmark problem,
        # not a model error.
        try:
            reference = self.reference_executor.execute(
                case["reference_sql"]
            )

            if reference.truncated:
                raise ValueError(
                    "Reference result was truncated."
                )

        except Exception as exc:
            return EvaluationCaseResult(
                **common,
                status="reference_error",
                matched=False,
                generated_sql=None,
                reference_row_count=None,
                generated_row_count=None,
                selected_chunk_ids=[],
                dependency_chunk_ids=[],
                error_type=type(exc).__name__,
                reason=str(exc),
            )

        error_categories = (
            (InsufficientContextError, "insufficient_context"),
            (SQLGenerationPipelineError, "generation_error"),
            (SQLValidationPipelineError, "validation_error"),
            (SQLExecutionPipelineError, "execution_error"),
        )

        try:
            generated = self.service.run(question)

        except Exception as exc:
            status = "unexpected_error"

            for exception_type, category in error_categories:
                if isinstance(exc, exception_type):
                    status = category
                    break

            return EvaluationCaseResult(
                **common,
                status=status,
                matched=False,
                generated_sql=None,
                reference_row_count=reference.row_count,
                generated_row_count=None,
                selected_chunk_ids=[],
                dependency_chunk_ids=[],
                error_type=type(exc).__name__,
                reason=str(exc),
            )

        comparison = compare_results(
            expected_rows=reference.rows,
            actual_rows=generated.rows,
            comparison=case["comparison"],
            expected_truncated=reference.truncated,
            actual_truncated=generated.truncated,
        )

        if generated.truncated:
            status = "truncated_result"
        elif comparison.matched:
            status = "correct"
        else:
            status = "result_mismatch"

        return EvaluationCaseResult(
            **common,
            status=status,
            matched=comparison.matched,
            generated_sql=generated.sql,
            reference_row_count=reference.row_count,
            generated_row_count=generated.row_count,
            selected_chunk_ids=list(
                generated.selected_chunk_ids
            ),
            dependency_chunk_ids=list(
                generated.dependency_chunk_ids
            ),
            error_type=None,
            reason=comparison.reason,
        )

    def run(
        self,
        benchmark_path: str | Path,
    ) -> EvaluationReport:
        benchmark = load_benchmark(benchmark_path)
        results = []

        for case in benchmark["cases"]:
            print(
                f"Evaluating {case['id']}: "
                f"{case['question']}",
                flush=True,
            )

            result = self.evaluate_case(case)
            results.append(result)

            print(
                f"  Status: {result.status}",
                flush=True,
            )

        status_counts: dict[str, int] = {}

        for result in results:
            status_counts[result.status] = (
                status_counts.get(result.status, 0) + 1
            )

        correct = sum(
            result.matched
            for result in results
        )

        total = len(results)

        return EvaluationReport(
            benchmark_name=benchmark.get(
                "benchmark_name",
                "Unknown",
            ),
            benchmark_version=benchmark.get(
                "version",
                "Unknown",
            ),
            evaluated_at=datetime.now(
                timezone.utc
            ).isoformat(),
            total_cases=total,
            correct_cases=correct,
            execution_accuracy=correct / total,
            status_counts=status_counts,
            cases=results,
        )


def save_report(
    report: EvaluationReport,
    path: str | Path,
) -> None:
    destination = Path(path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with destination.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            asdict(report),
            file,
            ensure_ascii=False,
            indent=2,
        )
