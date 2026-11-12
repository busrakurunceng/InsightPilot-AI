# InsightPilot AI â€” Text-to-SQL Evaluation and Error Analysis

**Project:** InsightPilot AI
**Module:** 3 â€” Text-to-SQL Engine
**Benchmark:** `evaluations/text_to_sql_benchmark.json`
**Database:** PostgreSQL / Olist
**Historical benchmark at the time of this report:** 11/12 correct (91.67%); later README/development log records a 12/12 run on the same benchmark. See dated addendum below.
**Historical unit-test suite at the time of this report:** 266 passed, 2 skipped; see dated addendum below.

## 1. Evaluation Method

The 12-case Turkish-language benchmark includes simple counts, filters, aggregations, joins and date filtering. Reference SQL is executed against the local Olist database using the read-only SQL executor. Model-generated SQL is compared by **result**, not merely by text equality. `result_comparator.py` supports scalar, unordered and ordered row comparison, numeric tolerance and duplicate-aware row matching.

An accurate result on this benchmark does not establish general correctness, robustness to paraphrases, or production readiness. Model responses can vary across runs.

## 2. Recorded Milestones

| Stage | Correct / 12 | Execution accuracy | Evidence |
|---|---:|---:|---|
| Initial evaluation baseline | 5 | 41.67% | Baseline report committed as `b6be864` |
| Context precision filtering | 9 | 75.00% | Report backup `text_to_sql_context_precision_75pct.json` |
| Business semantics grounding | 11 | 91.67% | Report backup `text_to_sql_business_grounding_91pct.json` |

**Important:** The planning-prompt experiment and semantic SQL validator prototype have **not** demonstrated a further increase in full-benchmark accuracy. Do not label the system 12/12 until a new complete evaluation confirms it.

## 3. Error Analysis

### Initial baseline

- SQL_004 (delivered orders): used a non-null delivery timestamp instead of `order_status = 'delivered'`.
- SQL_005 (canceled orders): used `'Cancelled'` instead of the exact database enum `'canceled'`.
- SQL_007 (customers by state): introduced an unwanted delivered-order filter and JOIN.
- SQL_008 (total payment value): added an unrequested delivered-order restriction.
- SQL_009 (average payment): added an unrequested delivered-order restriction.
- SQL_010 (orders from SÃ£o Paulo state): initially recorded as an execution error; the original failing SQL was not preserved in the report. A later standalone generation produced a different incorrect SQL and should not be treated as the original cause.
- SQL_012 (orders by customer state): omitted customer-state grouping and JOIN.

### Following context precision and business semantics improvements

- Context precision improved the live evaluation to 9/12; SQL_004, SQL_005 and SQL_012 remained incorrect.
- Business semantics grounding corrected the status-based SQL_004 and SQL_005 cases, increasing the live evaluation to 11/12.
- SQL_012 remained the only reported result mismatch.

## 4. SQL_012 Detailed Investigation

**Question:** Her eyaletteki mÃ¼ÅŸterilerin verdiÄŸi sipariÅŸ sayÄ±sÄ±nÄ± gÃ¶ster.

**Expected reference query shape:**

```sql
SELECT c.customer_state, COUNT(*) AS total_orders
FROM orders AS o
JOIN customers AS c ON o.customer_id = c.customer_id
GROUP BY c.customer_state;
```

**Observed generated query:**

```sql
SELECT COUNT(*) AS total_orders
FROM orders;
```

**Retrieved context:** `metric:total_orders` plus `table:orders` and `table:customers`. The retrieved table chunks include `orders.customer_id`, `customers.customer_id`, `customers.customer_state`, and the physical FK relationship.

**Conclusion:** Required schema is available; SQL generation fails to preserve the question's grouping dimension. The additional analytical planning instructions did not fix the standalone SQL_012 test.

**Diagnostic caveat:** A PowerShell pipeline using literal Turkish characters replaced some characters with `?` before Python received them. A Unicode-escaped diagnostic retrieved the expected context. This terminal issue is distinct from the SQL_012 benchmark error.

## 5. Semantic SQL Validator Prototype

`app/backend/semantic_sql_validator.py` introduces `validate_grouping_requirement(sql, required_dimension=None)`. Given a required dimension, it detects a missing `GROUP BY` and a missing grouping column. Six dedicated tests passed; the full regression suite was **266 passed, 2 skipped**. Commit `8fd89c6` was pushed to `origin/main`.

**Not yet implemented:** question-to-dimension mapping, service integration, robust alias/ordinal/qualified-column validation, complete JOIN checks, and bounded LLM regeneration. The prototype does **not** currently prevent SQL_012 from reaching execution in the main pipeline.

## 6. Reproduction and Artifact Preservation

Run the existing unit tests:

```powershell
python -m pytest -q
```

Before running the evaluation CLI, **back up** the current report if it exists:

```powershell
$report = 'artifacts/evaluations/text_to_sql_report.json'
if (Test-Path $report) {
    $backup = 'artifacts/evaluations/text_to_sql_report_before_next_run.json'
    if (Test-Path $backup) { throw "Backup already exists: $backup. Choose a new filename." }
    Copy-Item $report $backup
    if (-not (Test-Path $backup)) { throw 'Backup failed.' }
}
```

Only after confirming the backup, run:

```powershell
python -m scripts.run_text_to_sql_evaluation
```

The evaluation runs the model and database queries and may overwrite `artifacts/evaluations/text_to_sql_report.json`. It should not be run as part of routine unit testing.

## 7. Next Milestones

1. Schema-grounded dimension inference for Turkish questions.
2. Stronger SQL AST validation of requested dimensions and joins.
3. Optional bounded feedback/retry after validation, followed by normal SQL security validation.
4. Full benchmark comparison with the preserved 91.67% report; record both improvements and regressions.
5. Expand benchmark coverage beyond 12 questions.


---

## Addendum â€” 12 November 2026

This report is retained as a historical investigation of the original 12-case benchmark. Subsequent development integrated dimension mapping, bounded retry and business-rule validation. The README and development log recorded a later **12/12** result on that original benchmark (8 November 2026); the original 11/12 result above remains valid as an earlier checkpoint.

The **separate five-case advanced evaluation** subsequently reported **3/5 first-attempt matches, 5/5 final matches, and two successful retries**. Latest pytest: **532 passed, 2 skipped**. For cases, commands, limitations and Git commits see [`advanced_sql_evaluation.md`](advanced_sql_evaluation.md). No claim is made that the original 12-case benchmark was rerun after the 12 November changes.
