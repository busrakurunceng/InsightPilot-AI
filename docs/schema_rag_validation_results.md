# InsightPilot AI — Schema RAG Validation Results

**Module:** 2 — Schema RAG & Semantic Retrieval  
**Status:** Step 2.6 unit tests and manual integration check passed; retrieval quality evaluation pending  
**Environment:** Windows, Python 3.11.5, pytest 9.1.1, PostgreSQL 18, pgvector  
**Evidence:** Local terminal outputs recorded during development (29 October 2026)

## 1. Scope

This document records observed validation evidence for schema extraction, business semantics, schema chunking, embedding generation and upload, semantic search, and dependency-aware context enrichment. A passing unit test is not equivalent to a full end-to-end or retrieval-quality evaluation.

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

**Observed:** `31 passed, 2 skipped in 20.17s` (33 collected). No failed tests. The two skipped cases require `RUN_DB_TESTS=1` and a local PostgreSQL connection.

| Test module | Passed | Skipped |
|---|---:|---:|
| `test_dashboard_kpis.py` | 2 | 2 |
| `test_embeddings.py` | 6 | 0 |
| `test_schema_chunks.py` | 4 | 0 |
| `test_schema_dependencies.py` | 6 | 0 |
| `test_schema_search.py` | 5 | 0 |
| `test_semantic_validation.py` | 3 | 0 |
| `test_upload_embeddings.py` | 5 | 0 |
| **Total** | **31** | **2** |

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

**Interpretation:** `table:orders` is required for late-delivery rate. `table:order_items` was included because the top-five semantic hits also contained `metric:delivered_product_revenue`; it is not needed to compute late-delivery rate. The implementation expands dependencies for every retrieved metric, not just the highest-ranked relevant metric.

## 5. Additional exploratory retrieval observations

The following were observed in earlier manual searches, but they are **not yet a scored retrieval benchmark**:

| User question | Notable observation |
|---|---|
| Delivered-order revenue | `metric:delivered_product_revenue` appeared at rank 2; `rule:join_caveat` at rank 1. |
| Late delivery percentage | `metric:late_delivery_rate` appeared at rank 1. |
| Best-selling products | `table:products` appeared at rank 3, but `table:order_items` was absent from the initial top five. |
| Joining orders and payments | `rule:revenue_caveat` and `rule:join_caveat` appeared in the top two. |

These observations motivate a future question-level relevance set and measurements such as Recall@k and context precision. They do not establish retrieval accuracy percentages.

## 6. Known limitations and open validation work

1. **Context noise:** Expanding all retrieved metric dependencies can add irrelevant tables; consider selecting or reranking relevant metrics before enrichment.
2. **Table discovery:** Dependency enrichment only follows metrics already retrieved. It does not guarantee discovery of all tables needed for arbitrary questions.
3. **Benchmark not yet performed:** No labeled question-to-chunk relevance dataset, Recall@k, precision, or threshold comparison has been completed.
4. **Live integration coverage:** The manual retrieval command succeeded, but automated `enrich_context()` tests mock database results. A dedicated automated live retrieval integration test remains optional future work.
5. **SQL generation:** Module 2 retrieves context only. Text-to-SQL generation, SQL safety checks, and agent orchestration belong to later modules.

## 7. Conclusion and next actions

**Validated:** 31 non-database-dependent tests passed; the two database-gated dashboard tests passed when enabled; dependency-aware semantic retrieval succeeded manually for a late-delivery question.

**Pending before final Module 2 quality sign-off:** establish a small labeled question set, evaluate relevance and unnecessary context, decide whether to improve retrieval/reranking, then record results. Commit tested Step 2.6 code and this validation document as appropriate. Keep the development log synchronized with actual status.
