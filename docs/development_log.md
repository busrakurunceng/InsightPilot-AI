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

**Status:** Partially completed

Created `app/database/constraints.sql`.

Successfully added and verified four foreign key relationships:

1. `orders.customer_id` → `customers.customer_id`
2. `order_items.order_id` → `orders.order_id`
3. `order_items.product_id` → `products.product_id`
4. `order_items.seller_id` → `sellers.seller_id`

**Remaining work:** Validate and define the appropriate relationships for `order_payments` and `order_reviews`, and implement database indexes.

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

---

## Next Steps

1. Complete remaining foreign key checks and constraints.
2. Add indexes for frequently queried columns.
3. Implement analytical SQL queries for business KPIs.
4. Build the initial Streamlit dashboard.
5. Complete Module 1 and create the `v0.1.0-data-dashboard` release tag.

---

## Development Principles

- Implement and verify one functional component at a time.
- Keep raw data separate from application code.
- Never commit database credentials.
- Record technical problems and their resolutions.
- Commit tested milestones with descriptive messages.
- Update this development log after each significant milestone.
