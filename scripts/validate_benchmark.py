
import json
import sys
from pathlib import Path

from app.backend.sql_executor import SQLExecutor
from app.backend.sql_validator import validate_sql
from app.backend.text_to_sql_service import OLIST_ALLOWED_TABLES


BENCHMARK_PATH = Path(
    "evaluations/text_to_sql_benchmark.json"
)


def main() -> int:
    if not BENCHMARK_PATH.is_file():
        print(
            f"ERROR: Benchmark not found: {BENCHMARK_PATH}"
        )
        return 1

    with BENCHMARK_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        benchmark = json.load(file)

    cases = benchmark["cases"]

    executor = SQLExecutor(
        allowed_tables=set(OLIST_ALLOWED_TABLES),
        max_rows=1000,
        timeout_ms=10000,
    )

    passed = 0
    failed = 0

    print(f"Validating {len(cases)} reference queries")
    print("-" * 60)

    for case in cases:
        case_id = case["id"]
        question = case["question"]
        reference_sql = case["reference_sql"]

        try:
            validation = validate_sql(
                reference_sql,
                allowed_tables=set(OLIST_ALLOWED_TABLES),
            )

            result = executor.execute(validation.sql)

            if result.truncated:
                raise ValueError(
                    "Reference result exceeds max_rows=1000"
                )

            expected_tables = set(
                case["expected_tables"]
            )

            referenced_tables = set(
                validation.referenced_tables
            )

            if not expected_tables.issubset(
                referenced_tables
            ):
                raise ValueError(
                    "Expected tables missing from SQL. "
                    f"Expected: {expected_tables}, "
                    f"Found: {referenced_tables}"
                )

            print(
                f"PASS {case_id} | "
                f"rows={result.row_count} | "
                f"{question}"
            )

            passed += 1

        except Exception as exc:
            print(
                f"FAIL {case_id} | "
                f"{type(exc).__name__}: {exc}"
            )

            failed += 1

    print("-" * 60)
    print(
        f"RESULT: {passed} passed, {failed} failed"
    )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
