# InsightPilot AI — Development Log

## Project Overview

**Project:** InsightPilot AI — Agentic Conversational Business Intelligence Platform  
**Dataset:** Brazilian E-Commerce Public Dataset by Olist  
**Database:** PostgreSQL 18  
**Development Environment:** Python 3.11, VS Code, Windows, pgAdmin  
**Current Phase:** Module 2 — Schema RAG & Semantic Retrieval (MVP implementation and evaluation complete; release tag pending)

### Project Objective

Build an AI-powered business intelligence platform that enables users to query e-commerce data using natural language, generate SQL queries, perform business analytics, visualize results, and execute agentic workflows.

---

## Module 1 — Data Foundation

### Step 1: Development Environment

**Status:** Completed

- Created the project directory and Python virtual environment.
- Installed core libraries including Pandas, SQLAlchemy, psycopg, Streamlit, Plotly, and pytest.
- Established the initial project structure.
- Configured environment variables using `.env`.
- Configured `.gitignore` to exclude credentials, virtual environments, and raw datasets.
- Initialized Git and connected the GitHub repository.

### Step 2: Dataset Exploration

**Status:** Completed

- Downloaded and examined the nine Olist CSV files.
- Inspected column structures, row counts, and table relationships.
- Identified one-to-many relationships that may affect analytical JOIN operations.
- Identified duplicate geolocation records.
- Determined that ZIP code prefixes must be preserved as strings.

**Dataset size:** 1,550,922 records across nine tables.

### Step 3: PostgreSQL Setup

**Status:** Completed

- Installed PostgreSQL 18.
- Created the `insightpilot_db` database.
- Configured the Python-to-PostgreSQL connection using SQLAlchemy and psycopg.
- Verified database connectivity.

**Technical issue:** PostgreSQL initialization failed with the initial Windows locale configuration.

**Resolution:** Reinstalled PostgreSQL using the `English_United States` locale.

### Step 4: Database Schema

**Status:** Completed

- Created `app/database/schema.sql`.
- Defined nine relational tables.
- Assigned primary keys to tables with appropriate unique identifiers.
- Preserved timestamps using PostgreSQL `TIMESTAMP`.
- Preserved prices and payment values using `NUMERIC`.
- Deferred foreign key creation until data validation.

### Step 5: CSV Data Ingestion

**Status:** Completed

- Implemented `scripts/load_olist.py`.
- Loaded CSV data into PostgreSQL using Pandas and SQLAlchemy.
- Used chunked processing to support larger datasets.
- Added checks to prevent reloading already populated tables.

**Technical issue:** PostgreSQL rejected CSV date strings because timestamp columns received `VARCHAR` parameters.

**Resolution:** Converted relevant CSV date columns using `pd.to_datetime()` before insertion.

**Result:** All nine tables loaded successfully.

| Table | Records |
|---|---:|
| customers | 99,441 |
| orders | 99,441 |
| order_items | 112,650 |
| order_payments | 103,886 |
| order_reviews | 99,224 |
| products | 32,951 |
| sellers | 3,095 |
| geolocation | 1,000,163 |
| product_category_name_translation | 71 |
| **Total** | **1,550,922** |

### Step 6: Data Validation

**Status:** Completed

Created SQL validation queries covering:

- Referential integrity
- Duplicate primary keys
- Invalid prices and freight values
- Invalid review scores
- Missing purchase timestamps
- Inconsistent delivery dates
- Negative payment values

**Result:** All 13 validation checks passed with zero violations.

**Artifacts:**
- `docs/data_validation.sql`
- `docs/data_validation_results.md`

### Step 7: Foreign Key Constraints

**Status:** Completed

Created `app/database/constraints.sql` and successfully established six foreign key relationships.

- `orders.customer_id` → `customers.customer_id`
- `order_items.order_id` → `orders.order_id`
- `order_items.product_id` → `products.product_id`
- `order_items.seller_id` → `sellers.seller_id`
- `order_payments.order_id` → `orders.order_id`
- `order_reviews.order_id` → `orders.order_id`

Referential integrity was checked before adding the constraints. All six relationships were verified in PostgreSQL.

**Technical decision:** The `geolocation` table was excluded from direct foreign key relationships because ZIP code prefixes are not unique identifiers.

### Step 8: Database Index Inspection and Baseline Analysis

**Status:** Completed

- Inspected existing PostgreSQL indexes using `pg_indexes`.
- Identified seven automatically created primary key indexes.
- Confirmed that foreign key constraints do not automatically create indexes on referencing columns.
- Identified candidate indexes for analytical queries.
- Used `EXPLAIN (ANALYZE, BUFFERS)` to examine query execution plans.
- Established a baseline for customer-based order lookup.

**Baseline Results:**
- Table: `orders`
- Filter column: `customer_id`
- Scan type: Sequential Scan
- Execution time: 9.301 ms
- Rows removed by filter: 99,440
- Shared buffer hits: 1,809

**Technical finding:** PostgreSQL scanned the orders table to locate a single matching customer record because no index existed on `orders.customer_id`.

**Next:** Create and benchmark a B-tree index on `orders.customer_id`.


### Step 9: Customer Lookup Index and Performance Benchmark

**Status:** Completed

- Created `app/database/indexes.sql`.
- Added a B-tree index named `idx_orders_customer_id` on `orders.customer_id`.
- Verified index creation using `pg_indexes`.
- Repeated the same customer lookup query.
- Confirmed that PostgreSQL selected an Index Scan.

**Performance Results:**

| Metric | Before Index | After Index |
|---|---|---|
| Scan Type | Sequential Scan | Index Scan |
| Execution Time | 9.301 ms | 0.067 ms |
| Shared Buffer Hits | 1,809 | 4 |
| Rows Returned | 1 | 1 |

**Observed speedup:** Approximately 138.8x in this individual measurement.

**Technical finding:** The B-tree index substantially reduced the amount of data accessed for this selective customer lookup.

**Limitation:** The benchmark consists of individual executions. Repeated measurements would be needed for a more reliable performance assessment.

**Artifacts:**
- `app/database/indexes.sql`
- `docs/index_performance.md`

**Next:** Evaluate additional indexes for business analytics queries.


### Step 10: Analytical Database Indexing

**Status:** Completed

Evaluated and implemented four additional B-tree indexes
to optimize analytical queries in PostgreSQL.

**Indexes Created:**
- `idx_orders_purchase_timestamp` on `orders.order_purchase_timestamp`
- `idx_order_items_product_id` on `order_items.product_id`
- `idx_order_items_seller_id` on `order_items.seller_id`
- `idx_order_reviews_order_id` on `order_reviews.order_id`

**Benchmark Results:**

| Query | Before | After | Observed Speedup |
|---|---|---|---|
| Date filtering | 10.053 ms | 3.886 ms | 2.59x |
| Product lookup | 10.960 ms | 0.631 ms | 17.37x |
| Seller lookup | 11.707 ms | 1.566 ms | 7.48x |
| Review lookup | 8.533 ms | 0.153 ms | 55.77x |

**Technical Findings:**
- PostgreSQL selected Bitmap Heap Scans for date, product,
  and seller queries.
- PostgreSQL selected an Index Scan for the review lookup.
- B-tree indexes improved execution time in all four
  individual benchmark comparisons.
- Index benefits depend on query selectivity and data access patterns.
- Repeated measurements and index maintenance cost analysis
  remain outside the scope of these initial experiments.

**Artifacts:**
- `app/database/indexes.sql`
- `app/database/index_benchmarks.sql`
- `docs/index_performance.md`

**Next:** Develop analytical SQL queries for business KPIs
and prepare the initial Streamlit dashboard.



### Step 11: Business KPI SQL Queries and Validation

**Status:** Completed

- Created `app/database/kpi_queries.sql` with eight business KPI queries and three reconciliation checks.
- Defined total orders across all statuses; delivered-order product sales revenue excluding freight; and AOV based on delivered orders with order items.
- Calculated monthly revenue by purchase month, order status distribution, top products, top sellers, and delivery performance.
- Avoided multiplying sales totals through joins to one-to-many payment or review tables.

**Validated KPI Results:**

| Metric | Result |
|---|---:|
| Total orders (all statuses) | 99,441 |
| Delivered orders | 96,478 |
| Delivered product sales revenue (excluding freight) | 13,221,498.11 |
| Average order value (AOV) | 137.04 |
| Monthly revenue periods | 23 |
| Order status categories | 8 |
| Evaluated deliveries (complete dates) | 96,470 |
| Average delivery time | 12.56 days |
| Late deliveries | 7,826 |
| Late delivery rate | 8.11% |

**Reconciliation Checks:**
- Revenue reconciliation difference: `0.00` (passed).
- Order status total: `99,441`; matches total orders: `true` (passed).
- Monthly-to-total revenue difference: `0.00` (passed).

**Technical Notes:**
- Revenue is a product-sales metric, not net accounting revenue or payment receipts; freight, refunds, and payment adjustments are excluded.
- Delivery performance excludes eight delivered orders without all required date fields.
- KPI queries were validated on the local Olist PostgreSQL database; dashboard implementation is pending.

**Artifacts:**
- `app/database/kpi_queries.sql`
- `docs/kpi_validation_results.md`

**Next:** Implement the Streamlit BI dashboard and cross-check its values against the validated SQL results.

### Step 12: Streamlit Business Intelligence Dashboard and Module 1 Closure

**Status:** Completed — released as `v0.1.0-data-dashboard`

- Implemented the initial Streamlit BI dashboard on the validated PostgreSQL data foundation.
- Completed Module 1 and recorded the release milestone `v0.1.0-data-dashboard`.
- The KPI baselines and reconciliation checks from Step 11 remain the reference for dashboard figures.

**Evidence:** `docs/kpi_validation_results.md` and `tests/test_dashboard_kpis.py` provide KPI reference checks; the dashboard release is recorded by the `v0.1.0-data-dashboard` Git tag.

---

## Module 2 — Schema RAG & Semantic Retrieval

### Step 2.1: Database Schema Extraction

**Status:** Completed

- Implemented `scripts/extract_schema.py` to extract PostgreSQL schema metadata.
- Generated `docs/schema_catalog.json`.
- Captured nine tables, 52 columns, and six physical foreign key relationships.

**Validation:** Catalog counts were checked against the existing database schema. A dedicated automated test result for this step has not been supplied in the current record.

**Artifacts:** `scripts/extract_schema.py`, `docs/schema_catalog.json`.

### Step 2.2: Business Semantics

**Status:** Completed

- Created `semantic/business_semantics.yaml` with Turkish table descriptions and grains.
- Defined five business metrics: `total_orders`, `delivered_product_revenue`, `delivered_order_aov`, `average_delivery_days`, and `late_delivery_rate`.
- Defined four business rules: `date_filter`, `revenue_caveat`, `join_caveat`, and `geolocation_caveat`.
- Recorded one logical relationship between `products` and `product_category_name_translation` that is not enforced by a physical foreign key.
- Implemented `scripts/validate_semantics.py`.

**Validation:** Three semantic validation tests passed in the earlier development workflow.

**Artifacts:** `semantic/business_semantics.yaml`, `scripts/validate_semantics.py`.

### Step 2.3: Schema Chunking

**Status:** Completed

- Implemented `scripts/build_schema_chunks.py`.
- Generated 18 chunks: nine table chunks, five metric chunks, and four rule chunks.
- Stored the generated records in `artifacts/schema_chunks.json`.

**Validation:** Four chunking tests passed in the earlier development workflow.

**Artifacts:** `scripts/build_schema_chunks.py`, `artifacts/schema_chunks.json`.

### Step 2.4: Embedding Generation

**Status:** Completed

- Implemented `scripts/build_embeddings.py`.
- Used `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` to embed schema and business-semantic chunks.
- Produced 384-dimensional vectors for the 18 chunks.
- Generated `artifacts/schema_embeddings.npy` and `artifacts/schema_embeddings_metadata.json`.
- Excluded the generated `.npy` file from Git.

**Validation:** Embedding generation and output dimensions were checked during implementation. A dedicated automated test result is not recorded here.

### Step 2.5: PostgreSQL pgvector Storage

**Status:** Completed

- Installed and enabled pgvector v0.8.1 for PostgreSQL 18 on Windows.
- Created `public.schema_embeddings` with `chunk_id` as primary key, content, JSONB metadata, and `VECTOR(384)` embedding.
- Implemented `scripts/upload_embeddings.py` with UPSERT behavior.
- Verified that all 18 embedding records were present in PostgreSQL.

**Technical issues and resolutions:**
- The initial database connection configuration contained a placeholder password in `DATABASE_URL`; the local configuration was corrected without recording credentials here.
- pgvector installation on Windows required a compatible compiled extension and build tooling.

**Validation:** Five upload-embedding tests passed in the earlier workflow; the PostgreSQL record count was verified as 18.

**Artifacts:** `scripts/upload_embeddings.py`, `tests/test_upload_embeddings.py`.

### Step 2.6: Semantic Search and Dependency-Aware Retrieval

**Status:** Completed

- Implemented `scripts/search_schema.py` to embed Turkish natural-language questions and search pgvector using cosine similarity.
- Implemented `app/backend/schema_dependencies.py` for direct and nested metric dependencies derived from the semantic YAML.
- Added dependency enrichment to retrieve required chunks missing from the initial vector search.
- Preserved separate semantic and dependency result groups for traceability.

**Initial integration evidence (29 October 2026):** The late-delivery question retrieved `metric:late_delivery_rate` at rank 1 (similarity 0.3276). Initial dependency enrichment included `table:orders` and the irrelevant `table:order_items`, motivating subsequent context filtering.

**Validation:** Six dependency tests passed at this stage. Subsequent integration and regression tests are summarized below.

**Artifacts:** `scripts/search_schema.py`, `app/backend/schema_dependencies.py`, `tests/test_schema_dependencies.py`, `tests/test_schema_search.py`.

### Step 2.7: Retrieval Validation and Context Selection

**Status:** Completed for MVP

- Added metric-intent relevance scoring and join-rule selection in `app/backend/schema_relevance.py`.
- Added primary-context filtering in `app/backend/context_selector.py`.
- Enriched selected metrics and join rules with their required table and nested-metric chunks.
- Preserved fallback semantic results when no supported intent is identified.
- Added automated tests for context selection, relevance, rule selection, and integration behavior.

**Technical trade-off:** Primary-metric selection improves context precision for supported single-metric questions but does not support all paraphrases or multi-metric questions. This is an explicitly deferred improvement, not a completed feature.

**Artifacts:** `app/backend/schema_relevance.py`, `app/backend/context_selector.py`, `scripts/search_schema.py`, related `tests/test_*.py`.

### Step 2.8: Retrieval Evaluation and Robustness Benchmark

**Status:** Completed for MVP (through Step 2.8.5)

- Separated raw Top-5 retrieval results from selected and dependency-enriched final context.
- Implemented evaluation metrics for raw Recall@5, final context recall, and final context precision.
- Built a labeled 25-question benchmark spanning five categories: baseline, paraphrase, business semantics, relationships, and complex questions.
- Saved machine-readable benchmark and evaluation outputs under `artifacts/evaluations/`.
- Added tests for benchmark validation, metric calculations, and summary aggregation.

**Observed evaluation (30 October 2026; live PostgreSQL retrieval):**

| Measure | Result |
|---|---:|
| Questions | 25 |
| Mean Raw Recall@5 | 57.33% |
| Mean Context Recall | 79.67% |
| Mean Context Precision | 65.80% |
| Perfect final context | 10/25 |
| Baseline category recall / precision | 100.00% / 100.00% |
| Paraphrase category recall / precision | 70.00% / 44.00% |
| Questions with missing or extra chunks | 15 |

**Automated regression result:** `python -m pytest tests/ -v` — **70 passed, 2 skipped** (72 collected). Skipped tests are optional database-backed dashboard checks. Passing unit tests do not imply perfect retrieval quality.

**Known limitations:** Some Turkish paraphrases are missed; rule selection is incomplete; generic relationship terms may select an unrelated join caveat; multiple requested metrics are reduced to one primary metric; complex or ambiguous requests need additional handling. These limitations are documented rather than optimized further before the first end-to-end MVP.

**Artifacts:** `scripts/evaluate_retrieval.py`, `artifacts/evaluations/schema_benchmark.json`, `artifacts/evaluations/schema_robustness_evaluation.json`, `artifacts/evaluations/schema_robustness_evaluation.csv`, `tests/test_retrieval_benchmark.py`, `tests/test_retrieval_evaluation.py`.

**Detailed evidence:** `docs/schema_rag_validation_results.md`.

### Module 2 — MVP Closure

**Implementation and evaluation status:** Complete. **Git release tag:** Pending creation/verification (`v0.2.0-schema-rag`).

Module 2 delivers schema/metric/rule retrieval and dependency-enriched context for the next module. It does not implement LLM-based SQL generation, SQL execution, or an end-user conversational interface.

**Deferred to future iterations:** Expanded Turkish paraphrase coverage, advanced rule/relationship routing, multi-metric retrieval, ambiguity detection, and broader live integration coverage.

**Next:** Module 3 — Text-to-SQL Engine. Generated SQL must be validated and executed only with appropriately restricted read-only access; unsupported or ambiguous requests must not silently become unrestricted queries.

---

## Key Technical Decisions

| Decision | Reason |
|---|---|
| PostgreSQL | Relational analytics and future pgvector integration |
| SQLAlchemy | Python database connectivity |
| Chunked CSV ingestion | More manageable processing of large files |
| Explicit datetime conversion | Ensure correct PostgreSQL timestamp typing |
| ZIP prefixes as strings | Preserve leading zeros |
| Data validation before foreign keys | Detect inconsistent relationships before enforcing constraints |
| Raw data excluded from Git | Avoid unnecessary large files in the repository |
| Separate Git commits for features and tests | Maintain traceable development history |
| YAML business semantics | Make KPI definitions, join caveats, and metric dependencies explicit |
| Multilingual MiniLM embeddings | Support Turkish natural-language schema retrieval |
| PostgreSQL pgvector | Keep vector search alongside relational business data |
| Dependency-aware enrichment | Retrieve tables required by matched metrics even when vector search omits them |

---

## Next Steps

1. Confirm Module 2 documentation and benchmark outputs are committed, with a clean working tree.
2. Run `python -m pytest tests/ -q` as the final regression check.
3. Create and push the annotated Module 2 tag `v0.2.0-schema-rag` after validation.
4. Begin Module 3 — Text-to-SQL Engine, starting with a constrained, read-only SQL generation and validation flow.

## Development Principles

- Implement and verify one functional component at a time.
- Keep raw data separate from application code.
- Never commit database credentials.
- Record technical problems and their resolutions.
- Commit tested milestones with descriptive messages.
- Update this development log after each significant milestone.
