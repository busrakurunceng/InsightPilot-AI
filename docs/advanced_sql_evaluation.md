# InsightPilot AI — Advanced SQL Reference Evaluation

**Observed:** 12 November 2026. **Dataset:** local Olist PostgreSQL. **Scope:** five manually specified analytical questions with reference SQL.

## Reproduce

```powershell
python -m pytest -q
python -m scripts.evaluate_advanced_sql
```

These commands require the project's Python dependencies and, for the live evaluation, the configured local database and model. The evaluation is not a deterministic unit test: LLM outputs may vary.

## Recorded results

| Case | First attempt | Final | Retries |
|---|---|---|---:|
| Orders per state | Mismatch | Match | 1 |
| Monthly orders in 2018 | Match | Match | 0 |
| Unique customers per state | Match | Match | 0 |
| Payments for delivered orders | Match | Match | 0 |
| Top 10 categories by item revenue, excluding freight | Mismatch | Match | 1 |
| **Total** | **3/5** | **5/5** | **2** |

- **First-attempt reference matches:** 60% (3/5).
- **Final reference matches:** 100% (5/5).
- **Successful retries:** 2 of 2 attempted.
- **Regression suite:** 532 passed, 2 skipped, 17.97 seconds.

The evaluator reported matching **result values** rather than requiring identical SQL text. This is distinct from the historical 12-question Text-to-SQL benchmark.

## Failure analysis

- **State grouping:** initial `SELECT COUNT(*) FROM orders` omitted the requested state dimension. A single retry added the customers join and state grouping.
- **Unrequested delivered filter:** initial category-revenue query used `orders.order_status = 'delivered'` despite no such request. A single retry removed the restriction.
- **Distinct customer identity:** the model initially used `COUNT(DISTINCT customers.customer_unique_id)`, which matched the reference.
- **Delivered payment sum:** the explicit delivered-only filter was preserved, as requested.

## Evidence and limitations

The user-observed terminal run reported the results above. Five cases are too few to estimate generalization accuracy. No confidence interval, repeated-run stability study, unseen paraphrase benchmark, complex join fan-out test or production safety assessment is claimed. The previous 12-question benchmark was not rerun as part of this checkpoint.

## Git milestones

- `777807f`: semantic business-rule validation and SQL repair.
- `ca09421`: advanced SQL evaluation and date-function support.

## Next evaluation

Expand to 20–25 questions with unseen Turkish paraphrases, negative business-rule cases, multi-join fan-out, date filters, ambiguity and repeated-run stability. Track first attempt, retries, final results and latency separately.
