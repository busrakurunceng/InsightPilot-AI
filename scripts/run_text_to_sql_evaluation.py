
import argparse
from pathlib import Path

from app.backend.evaluation_runner import (
    EvaluationRunner,
    save_report,
)


DEFAULT_BENCHMARK = Path(
    "evaluations/text_to_sql_benchmark.json"
)

DEFAULT_OUTPUT = Path(
    "artifacts/evaluations/text_to_sql_report.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run InsightPilot Text-to-SQL evaluation."
    )

    parser.add_argument(
        "--benchmark",
        type=Path,
        default=DEFAULT_BENCHMARK,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    runner = EvaluationRunner()

    report = runner.run(args.benchmark)

    save_report(report, args.output)

    print("\n=== EVALUATION SUMMARY ===")
    print(f"Total cases: {report.total_cases}")
    print(f"Correct cases: {report.correct_cases}")
    print(
        f"Execution Accuracy: "
        f"{report.execution_accuracy:.2%}"
    )
    print(f"Status counts: {report.status_counts}")
    print(f"Report: {args.output}")

    if report.status_counts.get("reference_error", 0):
        print(
            "WARNING: Reference errors detected. "
            "Accuracy is not a valid model-only score."
        )


if __name__ == "__main__":
    main()
