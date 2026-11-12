
"""
Evaluate first-attempt SQL generation quality.

Run:
    python -m scripts.evaluate_sql_generation

Uses real Schema RAG, Ollama, and PostgreSQL.
Does not modify application source files.
"""

import time
from dataclasses import dataclass
from unittest.mock import patch

from sqlglot import exp, parse_one

from app.backend.sql_executor import SQLExecutor
from app.backend.sql_generator import SQLGenerator
from app.backend.text_to_sql_service import (
    OLIST_ALLOWED_TABLES,
    TextToSQLService,
)


@dataclass(frozen=True)
class TestCase:
    name: str
    question: str
    dimension: str | None
    measure: str


TEST_CASES = [
    TestCase(
        name="Customer count by state",
        question="Her eyaletteki müşteri sayısı nedir?",
        dimension="customer_state",
        measure="count",
    ),
    TestCase(
        name="Total customer count",
        question="Toplam müşteri sayısı kaçtır?",
        dimension=None,
        measure="count",
    ),
    TestCase(
        name="Orders by status",
        question="Her sipariş durumunda kaç sipariş var?",
        dimension="order_status",
        measure="count",
    ),
    TestCase(
        name="Payment total by type",
        question=(
            "Her ödeme türü için toplam ödeme tutarı nedir?"
        ),
        dimension="payment_type",
        measure="sum",
    ),
    TestCase(
        name="Products by category",
        question="Her ürün kategorisinde kaç ürün var?",
        dimension="product_category_name",
        measure="count",
    ),
]


def inspect_sql(sql, test_case):
    """
    Basic structural checks.

    These checks do not prove full business correctness.
    The normal pipeline performs its own validations.
    """
    issues = []

    try:
        tree = parse_one(sql, read="postgres")
    except Exception as exc:
        return [f"SQL parse failed: {exc}"]

    if not isinstance(tree, exp.Select):
        issues.append("Expected a SELECT statement.")
        return issues

    select_columns = {
        column.name.lower()
        for expression in tree.expressions
        for column in expression.find_all(exp.Column)
    }

    group = tree.args.get("group")

    group_columns = set()

    if group is not None:
        for expression in group.expressions:
            for column in expression.find_all(exp.Column):
                group_columns.add(column.name.lower())

    if test_case.dimension is None:
        if group is not None:
            issues.append(
                "Unexpected GROUP BY for an overall total."
            )
    else:
        expected = test_case.dimension.lower()

        if expected not in select_columns:
            issues.append(
                f"Missing dimension in SELECT: {expected}"
            )

        if group is None:
            issues.append("Missing GROUP BY.")
        elif expected not in group_columns:
            issues.append(
                f"Missing dimension in GROUP BY: {expected}"
            )

    aggregate_type = {
        "count": exp.Count,
        "sum": exp.Sum,
    }[test_case.measure]

    if not any(
        isinstance(node, aggregate_type)
        for node in tree.walk()
    ):
        issues.append(
            f"Missing expected aggregate: "
            f"{test_case.measure.upper()}"
        )

    return issues


def evaluate_case(test_case, index, total):
    initial_sql = None
    retry_sql = None
    retry_type = None
    retry_issues = []
    retry_count = 0

    original_generate = SQLGenerator.generate
    original_regenerate = SQLGenerator.regenerate

    def traced_generate(self, *args, **kwargs):
        nonlocal initial_sql

        result = original_generate(
            self, *args, **kwargs
        )

        initial_sql = result.sql
        return result

    def traced_regenerate(
        self,
        previous,
        issues,
        *,
        validation_type="semantic",
    ):
        nonlocal retry_sql
        nonlocal retry_type
        nonlocal retry_count

        retry_count += 1
        retry_type = validation_type
        retry_issues.extend(issues)

        result = original_regenerate(
            self,
            previous,
            issues=issues,
            validation_type=validation_type,
        )

        retry_sql = result.sql
        return result

    print("\n" + "=" * 65)
    print(f"TEST {index}/{total}: {test_case.name}")
    print("=" * 65)
    print("Question:", test_case.question)

    start = time.perf_counter()
    result = None
    error = None

    with (
        patch.object(
            SQLGenerator,
            "generate",
            traced_generate,
        ),
        patch.object(
            SQLGenerator,
            "regenerate",
            traced_regenerate,
        ),
    ):
        try:
            service = TextToSQLService(
                executor=SQLExecutor(
                    allowed_tables=set(
                        OLIST_ALLOWED_TABLES
                    ),
                ),
            )

            result = service.run(
                test_case.question
            )

        except Exception as exc:
            error = exc

    elapsed = time.perf_counter() - start

    first_issues = (
        inspect_sql(initial_sql, test_case)
        if initial_sql
        else ["No initial SQL was produced."]
    )

    first_pass = (
        initial_sql is not None
        and not first_issues
    )

    final_issues = (
        inspect_sql(result.sql, test_case)
        if result is not None
        else ["Pipeline did not complete."]
    )

    final_pass = (
        result is not None
        and not final_issues
    )

    print("\nInitial SQL:")
    print(initial_sql or "(not generated)")

    print(
        "\nFirst-attempt structural check:",
        "PASS" if first_pass else "FAIL",
    )

    for issue in first_issues:
        print(" -", issue)

    print("\nRetry count:", retry_count)

    if retry_count:
        print("Retry type:", retry_type)
        print("Retry feedback:")

        for issue in retry_issues:
            print(" -", issue)

        print("\nRepaired SQL:")
        print(retry_sql or "(not generated)")

    print(
        "\nPipeline result:",
        "SUCCESS" if result else "FAILED",
    )

    if result:
        print("Final SQL:")
        print(result.sql)
        print("Rows returned:", result.row_count)

    for issue in final_issues:
        if result is not None:
            print("Final check issue:", issue)

    if error:
        print(
            "Error:",
            type(error).__name__,
            str(error),
        )

        if error.__cause__ is not None:
            print(
                "Cause:",
                type(error.__cause__).__name__,
                str(error.__cause__),
            )

    print(f"Elapsed: {elapsed:.3f} s")

    return {
        "name": test_case.name,
        "first_pass": first_pass,
        "final_pass": final_pass,
        "retry_count": retry_count,
        "elapsed": elapsed,
    }


def main():
    print("\nInsightPilot-AI SQL Generation Evaluation")
    print("Tests:", len(TEST_CASES))

    results = []

    for index, test_case in enumerate(
        TEST_CASES, start=1
    ):
        results.append(
            evaluate_case(
                test_case,
                index,
                len(TEST_CASES),
            )
        )

    total = len(results)

    first_passed = sum(
        item["first_pass"]
        for item in results
    )

    final_passed = sum(
        item["final_pass"]
        for item in results
    )

    retries = sum(
        item["retry_count"]
        for item in results
    )

    total_time = sum(
        item["elapsed"]
        for item in results
    )

    print("\n" + "=" * 65)
    print("EVALUATION SUMMARY")
    print("=" * 65)

    for item in results:
        first_status = (
            "PASS"
            if item["first_pass"]
            else "FAIL"
        )

        final_status = (
            "PASS"
            if item["final_pass"]
            else "FAIL"
        )

        print(
            f"{item['name']}: "
            f"first={first_status}, "
            f"final={final_status}, "
            f"retries={item['retry_count']}, "
            f"time={item['elapsed']:.2f}s"
        )

    print(
        "\nFirst-attempt structural pass rate:",
        f"{first_passed}/{total}",
        f"({100 * first_passed / total:.1f}%)",
    )

    print(
        "Final pipeline + structural pass rate:",
        f"{final_passed}/{total}",
        f"({100 * final_passed / total:.1f}%)",
    )

    print("Total retries:", retries)
    print(f"Total elapsed: {total_time:.3f} s")

    print(
        "\nNote: Structural checks are diagnostic, "
        "not a full business-correctness evaluation."
    )


if __name__ == "__main__":
    main()
