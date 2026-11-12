# InsightPilot AI — Semantic Layer and SQL Repair

**Checkpoint:** 12 November 2026.

## Purpose

Schema correctness alone does not ensure business correctness. A query may execute successfully while counting the wrong customer identity or applying an unrequested status filter. The semantic layer adds business-specific validation after generation.

## Business concepts

| Concept | Intended interpretation |
|---|---|
| Distinct customers | `COUNT(DISTINCT customers.customer_unique_id)` when the question asks for unique customers |
| Delivered product revenue | Sum of `order_items.price` for delivered orders, excluding freight; used by the historical dashboard KPI |
| Unqualified product-category item revenue | Sum of `order_items.price` without silently restricting to delivered orders when the question does not request that restriction |
| Payment receipts | `order_payments.payment_value`, a different monetary measure from item prices |

**Important:** These are distinct measures. The original dashboard KPI and the advanced category-revenue benchmark intentionally have different status-filter semantics. Do not collapse them into one universal revenue rule.

## Implementation references

- `semantic/business_semantics.yaml`: semantic metadata and metric definitions.
- `app/backend/sql_prompt_builder.py`: semantic context in generation prompts.
- `app/backend/semantic_sql_validator.py`: required grouping-dimension validation.
- `app/backend/business_rule_validator.py`: SQLGlot AST checks for selected business rules.
- `app/backend/text_to_sql_service.py`: validator integration and bounded corrective regeneration.
- `tests/test_business_rule_validator.py`: dedicated business-rule tests.

## Observed repairs

1. **State order counts:** the initial SQL omitted the requested state grouping; the regenerated SQL joined `customers` and grouped by `customer_state`.
2. **Top 10 categories by item revenue:** the initial SQL unnecessarily restricted orders to `delivered`; the regenerated SQL removed the restriction and matched the reference result.

The distinct-customer question was correct on the first attempt, using `customer_unique_id`. The evaluation does not isolate whether this improvement was caused by prompt grounding, model variation, or the new validator.

## Limitations

Business-rule checks recognize a bounded set of question patterns and SQL AST structures. They are not a general theorem prover for SQL correctness. In particular, multi-table fan-out, ambiguous intent, paraphrase diversity and multi-metric requests need expanded testing.

See [advanced evaluation](advanced_sql_evaluation.md).
