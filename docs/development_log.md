# InsightPilot AI — Development Log

## Project Overview

**Project:** InsightPilot AI — Agentic Conversational Business Intelligence Platform  
**Dataset:** Brazilian E-Commerce Public Dataset by Olist  
**Database:** PostgreSQL 18  
**Development Environment:** Python 3.11, VS Code, Windows, pgAdmin  
**Current Phase:** Module 1 — Data Foundation & Dashboard

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

---

## Next Steps

1. Implement the Streamlit business intelligence dashboard.
2. Display core KPI cards, monthly revenue trends, order status distribution, top products, top sellers, and delivery performance.
3. Validate dashboard figures against `docs/kpi_validation_results.md`.
4. Complete Module 1 and create the `v0.1.0-data-dashboard` release tag.


## Development Principles

- Implement and verify one functional component at a time.
- Keep raw data separate from application code.
- Never commit database credentials.
- Record technical problems and their resolutions.
- Commit tested milestones with descriptive messages.
- Update this development log after each significant milestone.
