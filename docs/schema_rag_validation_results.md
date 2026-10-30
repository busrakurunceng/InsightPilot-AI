
# InsightPilot AI — Schema RAG Validation Results

**Module:** 2 — Schema RAG & Semantic Retrieval  
**Status:** Module 2 MVP retrieval implementation and 25-question evaluation completed; release tag pending  
**Environment:** Windows, Python 3.11.5, pytest 9.1.1, PostgreSQL 18, pgvector  
**Evidence:** Local terminal outputs recorded during development (29–30 October 2026)

## 1. Scope

This document records observed validation evidence for schema extraction, business semantics, schema chunking, embedding generation and upload, semantic search, context selection, dependency enrichment, and retrieval robustness. A passing unit test is not equivalent to end-to-end Text-to-SQL correctness.

## 2. Data and schema baseline

| Item | Observed value |
|---|---:|
| Olist relational tables | 9 |
| Schema columns | 52 |
| Physical foreign keys | 6 |
| Business metrics | 5 |
| Business rules | 4 |
| Generated schema chunks | 18 |
| Table chunks | 9 |
| Metric chunks | 5 |
| Rule chunks | 4 |
| Embedding dimension | 384 |
| Uploaded pgvector records | 18 |

**Embedding model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. The upload count was checked earlier against PostgreSQL. The embedding arrays are generated artifacts, not source code.

## 3. Automated test results

### 3.1 Full regression suite

Command: `python -m pytest tests/ -v`

**Most recent observed result (30 October 2026):** `70 passed, 2 skipped` (72 collected). No failures. The two skipped cases require `RUN_DB_TESTS=1` and a local PostgreSQL connection.

This includes dashboard, embeddings, schema chunking, dependency resolution, schema search, semantic validation, context selection, metric/rule relevance, retrieval evaluation, benchmark validation, and upload tests.

The earlier Step 2.6 regression baseline was **31 passed, 2 skipped** (33 collected); it has been superseded by the expanded test suite. Passing tests confirm tested code behavior, not retrieval correctness on every question.

### 3.2 PostgreSQL-enabled dashboard checks

Commands (PowerShell):

```powershell
$env:RUN_DB_TESTS = "1"
python -m pytest tests/test_dashboard_kpis.py -v
Remove-Item Env:RUN_DB_TESTS
```

**Observed:** `4 passed in 4.41s`. Both previously skipped database-dependent cases passed: `test_full_dataset_reference_metrics` and `test_selected_date_range_consistency`. These four tests are part of the 33 collected tests, not four additional unique test cases.

### 3.3 Step 2.6 unit checks

- `test_schema_dependencies.py`: **6 passed in 0.13s**. Covers direct table dependencies, nested metric dependencies, deduplication, unknown metrics, and total-order dependencies.
- `test_schema_search.py`: **5 passed in 13.00s**. Covers required-table expansion, avoidance of duplicates, no-metric behavior, nested metric expansion, and missing-record error handling. PostgreSQL responses are mocked in these five tests; they do not independently verify a live database connection.

## 4. Manual semantic search and enrichment

**Command:**

```powershell
python scripts/search_schema.py "Siparişlerin yüzde kaçı geç teslim edildi?"
```

**Observed semantic results:**

| Rank | Chunk ID | Cosine similarity |
|---:|---|---:|
| 1 | `metric:late_delivery_rate` | 0.3276 |
| 2 | `rule:date_filter` | 0.2884 |
| 3 | `rule:revenue_caveat` | 0.2550 |
| 4 | `rule:join_caveat` | 0.2449 |
| 5 | `metric:delivered_product_revenue` | 0.2048 |

**Observed enrichment:** `table:orders`, `table:order_items`.

**Summary:** 5 semantic hits + 2 dependency hits = **7 unique chunks**. This confirms a successful manual end-to-end run against the local PostgreSQL schema-embedding table for this query.

**Historical interpretation (before context filtering):** `table:orders` is required for late-delivery rate. `table:order_items` was included because the initial top-five results contained `metric:delivered_product_revenue`; it is not needed for this calculation. Subsequent context selection addressed this specific baseline case.

## 5. Retrieval robustness evaluation (30 October 2026)

**Command:** `python scripts/evaluate_retrieval.py` against the local PostgreSQL pgvector index.

**Benchmark:** `artifacts/evaluations/schema_benchmark.json` — 25 labeled questions across five categories.

| Measure | Result |
|---|---:|
| Mean Raw Recall@5 | 57.33% |
| Mean Context Recall | 79.67% |
| Mean Context Precision | 65.80% |
| Perfect final contexts | 10/25 |
| Questions with missing or extra chunks | 15 |

### Category results

| Category | Context Recall | Context Precision |
|---|---:|---:|
| Baseline | 100.00% | 100.00% |
| Paraphrase | 70.00% | 44.00% |
| Business semantics | 80.00% | 60.00% |
| Relationships | 80.00% | 57.00% |
| Complex | 68.33% | 68.00% |

### Difficulty results

| Difficulty | Context Recall | Context Precision |
|---|---:|---:|
| Supported | 89.29% | 80.00% |
| Challenge | 67.42% | 47.73% |

**Interpretation:** Context enrichment and filtering improved mean recall compared with raw Top-5 retrieval, but the result is not uniformly reliable. The five baseline questions achieved perfect final context recall and precision; broader wording and question types exposed limitations. These are retrieval-context measurements, **not SQL execution accuracy**.

**Observed failure examples:**

- Q07, “Sipariş adedini öğrenmek istiyorum.” — `metric:total_orders` was missing from the final context.
- Q08, “Ortalama sepet tutarı nedir?” — required order tables were missing from the final context.
- Q13–Q14 — business/date rules appeared in raw retrieval but required table dependencies were missing.
- Q19 — an order-review relationship question incorrectly selected `rule:join_caveat`, missing `table:order_reviews`.
- Q21–Q23 — multi-metric questions retained only one requested metric.
- Q25 — “En iyi müşterilerimiz kimler?” remains ambiguous and lacks necessary table context.

**Generated reports:**

- `artifacts/evaluations/schema_robustness_evaluation.json`
- `artifacts/evaluations/schema_robustness_evaluation.csv`

## 6. Known limitations and deferred work

1. **Turkish paraphrases:** Hard-coded intent patterns do not cover all equivalent expressions; fallback Top-5 context can be noisy.
2. **Single primary metric:** Multiple requested metrics are not consistently retained.
3. **Business rules:** Some specialized rules lack reliable routing and dependency expansion.
4. **Relationships:** Generic relationship keywords can select an unrelated join warning; some relevant tables are missed.
5. **Ambiguity:** Vague questions do not yet trigger a dedicated clarification mechanism.
6. **Live integration:** The benchmark exercised live retrieval, while some automated dependency tests use mocks. End-to-end Text-to-SQL safety and correctness are not validated in Module 2.

**MVP decision:** Preserve the measured baseline and defer advanced retrieval optimization until it is informed by the first constrained Text-to-SQL workflow. Downstream SQL generation must include independent validation and restricted read-only execution; retrieval alone is not a safety guarantee.

**Next module:** Module 3 — Text-to-SQL Engine.
