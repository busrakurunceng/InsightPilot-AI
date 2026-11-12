"""Advanced Text-to-SQL evaluation against PostgreSQL reference results.

Run from repository root: python -m scripts.evaluate_advanced_sql
"""
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter

from app.backend.sql_executor import SQLExecutor
from app.backend.sql_generator import SQLGenerator
from app.backend.text_to_sql_service import OLIST_ALLOWED_TABLES, TextToSQLService


@dataclass(frozen=True)
class Case:
    name: str
    question: str
    reference_sql: str
    ordered: bool = False
    comparison_mode: str = "default"


CASES = [
    Case(
        "Orders per state",
        "Her eyalette kaç sipariş verilmiş?",
        """SELECT c.customer_state, COUNT(*) AS order_count
           FROM orders o JOIN customers c ON o.customer_id = c.customer_id
           GROUP BY c.customer_state""",
    ),
    Case(
        "Monthly orders in 2018",
        "2018 yılında aylara göre kaç sipariş verilmiş?",
        """SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month,
                  COUNT(*) AS order_count
           FROM orders
           WHERE order_purchase_timestamp >= '2018-01-01'
             AND order_purchase_timestamp < '2019-01-01'
           GROUP BY DATE_TRUNC('month', order_purchase_timestamp)
           ORDER BY month""",
        comparison_mode="monthly",
    ),
    Case(
        "Unique customers per state",
        "Her eyalette kaç farklı müşteri sipariş vermiş?",
        """SELECT c.customer_state,
                  COUNT(DISTINCT c.customer_unique_id) AS unique_customers
           FROM orders o JOIN customers c ON o.customer_id = c.customer_id
           GROUP BY c.customer_state""",
    ),
    Case(
        "Payments for delivered orders",
        "Teslim edilmiş siparişlerin toplam ödeme tutarı nedir?",
        """SELECT SUM(op.payment_value) AS total_payment
           FROM orders o JOIN order_payments op ON o.order_id = op.order_id
           WHERE o.order_status = 'delivered'""",
    ),
    Case(
        "Top 10 categories by item revenue",
        "En fazla gelir getiren 10 ürün kategorisi hangileri? Kargo ücretini dahil etme.",
        """SELECT p.product_category_name, SUM(oi.price) AS total_revenue
           FROM order_items oi JOIN products p ON oi.product_id = p.product_id
           GROUP BY p.product_category_name
           ORDER BY total_revenue DESC LIMIT 10""",
        ordered=True,
    ),
]


class TracedGenerator(SQLGenerator):
    def __init__(self):
        super().__init__()
        self.initial_sql = None
        self.retry_count = 0
        self.retry_sql = None

    def generate(self, question):
        result = super().generate(question)
        self.initial_sql = result.sql
        return result

    def regenerate(self, previous, issues, validation_type="semantic"):
        self.retry_count += 1
        result = super().regenerate(
            previous, issues=issues, validation_type=validation_type
        )
        self.retry_sql = result.sql
        return result


def normalize_value(value):
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float, Decimal)):
        # Olist monetary fields have cent precision. Preserve exact counts.
        return ("number", Decimal(str(value)).quantize(Decimal("0.01")))
    if isinstance(value, (datetime, date)):
        return ("date", value.isoformat())
    return ("text", str(value))


def normalize_rows(rows):
    # Compare by column position: aliases may legitimately differ.
    return [tuple(normalize_value(v) for v in row.values()) for row in rows]


def normalize_monthly_rows(result):
    """Normalize monthly outputs to (YYYY-MM-01, count), without guessing columns.

    Supported layouts:
      - month (date/datetime), count
      - order_year, order_month, count (in any column order)
    """
    columns = [column.lower() for column in result.columns]
    year_names = {"order_year", "year"}
    month_number_names = {"order_month", "month_number"}

    if len(columns) == 3:
        year_indexes = [i for i, name in enumerate(columns) if name in year_names]
        month_indexes = [i for i, name in enumerate(columns) if name in month_number_names]
        if len(year_indexes) != 1 or len(month_indexes) != 1:
            raise ValueError("Monthly output requires recognizable year and month columns")
        year_idx, month_idx = year_indexes[0], month_indexes[0]
        count_idx = next(i for i in range(3) if i not in {year_idx, month_idx})
        normalized = []
        for row in result.rows:
            values = list(row.values())
            year_value, month_value = values[year_idx], values[month_idx]
            if (isinstance(year_value, bool) or isinstance(month_value, bool)
                    or int(year_value) != year_value or int(month_value) != month_value):
                raise ValueError("Year and month must be whole numbers")
            month_start = date(int(year_value), int(month_value), 1)
            normalized.append((normalize_value(month_start), normalize_value(values[count_idx])))
        return normalized

    if len(columns) == 2:
        month_indexes = [i for i, name in enumerate(columns) if name in {"month", "order_month", "month_start"}]
        if len(month_indexes) != 1:
            raise ValueError("Monthly output requires a recognizable month date column")
        month_idx = month_indexes[0]
        count_idx = 1 - month_idx
        normalized = []
        for row in result.rows:
            values = list(row.values())
            month_value = values[month_idx]
            if not isinstance(month_value, (date, datetime)):
                raise ValueError("Two-column monthly output must contain a date/datetime month")
            if month_value.day != 1 or (isinstance(month_value, datetime) and
                                         (month_value.hour, month_value.minute, month_value.second,
                                          month_value.microsecond) != (0, 0, 0, 0)):
                raise ValueError("Monthly date must represent the first day of the month")
            month_start = date(month_value.year, month_value.month, 1)
            normalized.append((normalize_value(month_start), normalize_value(values[count_idx])))
        return normalized

    raise ValueError("Unsupported monthly result layout")


def compare_results(actual, reference, ordered, comparison_mode="default"):
    if actual.truncated or reference.truncated:
        return False, "TRUNCATED: increase max_rows before comparing"
    if comparison_mode == "monthly":
        try:
            a = normalize_monthly_rows(actual)
            b = normalize_monthly_rows(reference)
        except (ValueError, TypeError, OverflowError) as exc:
            return False, f"Invalid monthly result format: {exc}"
    elif comparison_mode == "default":
        if len(actual.columns) != len(reference.columns):
            return False, "Different number of result columns"
        a = normalize_rows(actual.rows)
        b = normalize_rows(reference.rows)
    else:
        raise ValueError(f"Unknown comparison mode: {comparison_mode}")
    if ordered:
        equal = a == b
    else:
        equal = Counter(a) == Counter(b)
    if equal:
        return True, "Result values match reference"
    sample_a = next((row for row in a if row not in b), a[0] if a else None)
    sample_b = next((row for row in b if row not in a), b[0] if b else None)
    return False, f"Result mismatch; generated sample={sample_a}; reference sample={sample_b}"


def main():
    print("InsightPilot-AI | Advanced SQL Reference Evaluation")
    print("Cases:", len(CASES))
    executor = SQLExecutor(
        allowed_tables=set(OLIST_ALLOWED_TABLES), max_rows=1000, timeout_ms=10000
    )
    results = []
    try:
        for index, case in enumerate(CASES, 1):
            print("\n" + "=" * 65)
            print(f"TEST {index}/{len(CASES)}: {case.name}")
            print("Question:", case.question)
            generator = TracedGenerator()
            service = TextToSQLService(generator=generator, executor=executor)
            started = perf_counter()
            try:
                generated = service.run(case.question)
                reference = executor.execute(case.reference_sql)
                # TextToSQLResult and SQLExecutionResult both expose these fields.
                match, reason = compare_results(generated, reference, case.ordered, case.comparison_mode)
                first_attempt_match = None
                if generator.initial_sql is not None:
                    try:
                        first_execution = executor.execute(generator.initial_sql)
                        first_attempt_match, _ = compare_results(
                            first_execution, reference, case.ordered, case.comparison_mode
                        )
                    except Exception as exc:
                        print("First SQL could not execute:", exc)
                        first_attempt_match = False
                print("\nInitial SQL:\n", generator.initial_sql)
                print("\nFinal SQL:\n", generated.sql)
                print("Retry count:", generator.retry_count)
                print("Generated rows:", generated.row_count)
                print("Reference rows:", reference.row_count)
                print("First attempt reference match:", first_attempt_match)
                print("Final reference match:", match)
                print("Detail:", reason)
                results.append((case.name, first_attempt_match, match, generator.retry_count))
            except Exception as exc:
                print("Initial SQL:", generator.initial_sql)
                print("Retry count:", generator.retry_count)
                print("FAILED:", type(exc).__name__, str(exc))
                if exc.__cause__:
                    print("Cause:", type(exc.__cause__).__name__, str(exc.__cause__))
                results.append((case.name, False, False, generator.retry_count))
            print(f"Elapsed: {perf_counter() - started:.3f} s")
    finally:
        executor.engine.dispose()

    print("\n" + "=" * 65 + "\nSUMMARY\n" + "=" * 65)
    for name, first, final, retries in results:
        print(f"{name}: first={first}, final={final}, retries={retries}")
    print("First-attempt reference matches:", sum(first is True for _, first, _, _ in results), "/", len(results))
    print("Final reference matches:", sum(final for _, _, final, _ in results), "/", len(results))
    print("Total retries:", sum(r for _, _, _, r in results))
    if not all(final for _, _, final, _ in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
