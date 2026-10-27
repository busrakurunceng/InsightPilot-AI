# InsightPilot AI

### Agentic Conversational Business Intelligence Platform

InsightPilot AI is an incremental AI engineering project aiming to make e-commerce business data accessible through natural-language questions, validated SQL, and analytical visualizations.

**Current deliverable (Module 1):** a working, date-filtered Streamlit business intelligence dashboard backed by PostgreSQL. **Natural-language querying, RAG, and autonomous agent workflows are planned, not implemented yet.**

## Project Objectives

- Translate natural-language business questions into SQL (planned).
- Use Retrieval-Augmented Generation (RAG) to retrieve schema and metric context (planned).
- Validate generated SQL before execution (planned).
- Analyze PostgreSQL data and present results in an interactive dashboard (initial dashboard implemented).
- Develop multi-step analytical workflows using agentic AI (planned).
- Evaluate correctness, security, retrieval quality, and performance throughout development.

## Technology Stack

| Area | Technologies | Status |
|---|---|---|
| Language and data processing | Python, Pandas, NumPy | In use |
| Database | PostgreSQL, SQLAlchemy, Psycopg | In use |
| Dashboard | Streamlit, Plotly | In use |
| Configuration and tests | python-dotenv, Pytest | In use |
| LLM orchestration | LangChain, LangGraph | Planned |
| Semantic retrieval | pgvector, embeddings | Planned |
| SQL validation | SQLGlot | Planned |
| API | FastAPI | Planned |
| Deployment | Docker, GitHub Actions | Planned |

## Dataset

This project uses the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), comprising nine CSV files: customers, orders, order items, order payments, order reviews, products, sellers, geolocation, and product category translations.

The local PostgreSQL database is named `insightpilot_db`. The nine source tables contain **1,550,922 rows in total**. Raw datasets and local credentials are not committed to Git.

> **Data setup prerequisite:** Download the dataset from Kaggle and load the nine CSVs into the matching PostgreSQL tables using the project's data-loading workflow. Cloning the repository and installing Python dependencies alone will not populate the database. Refer to the repository's `scripts/`, `app/database/`, and `docs/` for the data-foundation work; confirm the relevant import instructions before running a fresh setup.

## Current Architecture

```text
Streamlit UI (app/frontend/main.py)
             |
             v
Analytics / parameterized SQL (app/backend/analytics.py)
             |
             v
Database connection (app/backend/db.py)
             |
             v
PostgreSQL (insightpilot_db)
```

The frontend and backend modules currently run within **one Python/Streamlit application**. A separate HTTP backend/API is not part of Module 1.

```text
app/
├── __init__.py
├── backend/
│   ├── __init__.py
│   ├── db.py
│   └── analytics.py
├── database/
│   ├── kpi_queries.sql
│   ├── indexes.sql
│   └── index_benchmarks.sql
└── frontend/
    ├── __init__.py
    └── main.py

tests/
└── test_dashboard_kpis.py

docs/
├── development_log.md
├── index_performance.md
└── kpi_validation_results.md
```

This is a **relevant-file overview**, not an exhaustive directory listing.

## Implemented Dashboard

- Total orders, delivered-product revenue, and average order value (AOV) KPI cards.
- Monthly revenue trend.
- Order-status distribution.
- Top 10 products and top 10 sellers by delivered-product revenue.
- Average delivery time, late-delivery count, and late-delivery rate.
- Global purchase-date filter applied to dashboard metrics and visualizations, including single-day selections.

### Metric Definitions

- **Total orders:** all order statuses, filtered by `orders.order_purchase_timestamp`.
- **Revenue:** sum of `order_items.price` for `delivered` orders; excludes freight and is **not** accounting net revenue.
- **AOV:** delivered-product revenue divided by delivered orders with at least one order item.
- **Monthly revenue:** attributed to the order's **purchase month**, not delivery month.
- **Delivery performance:** delivered orders with the required date fields; an order is late if actual delivery is after the estimated delivery date.

### Full-Dataset Reference Values

| Metric | Validated value |
|---|---:|
| Total orders | 99,441 |
| Delivered-product revenue | R$ 13,221,498.11 |
| AOV | R$ 137.04 |
| Delivered orders with items | 96,478 |
| Delivery records evaluated | 96,470 |
| Average delivery time | 12.56 days |
| Late deliveries | 7,826 |
| Late-delivery rate | 8.11% |

These values are regression references for the **unchanged, complete Olist dataset**, not expected results for a filtered date range.

## Getting Started (Windows PowerShell)

### 1. Clone and create a virtual environment

```powershell
git clone https://github.com/busrakurunceng/InsightPilot-AI.git
cd InsightPilot-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

If the repository's `requirements.txt` is up to date:

```powershell
python -m pip install -r requirements.txt
```

Otherwise, the dependencies needed for the current dashboard and tests include:

```powershell
python -m pip install pandas numpy sqlalchemy "psycopg[binary]" streamlit plotly python-dotenv pytest
```

### 3. Configure PostgreSQL

Create a local `.env` file at the repository root:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=insightpilot_db
DB_USER=your_local_db_user
DB_PASSWORD=your_local_db_password
```

Alternatively, the backend accepts `DATABASE_URL`. Do not commit `.env` or credentials. Ensure PostgreSQL is running and the nine Olist tables have been populated before starting the dashboard.

### 4. Run the dashboard

From the repository root with the virtual environment activated:

```powershell
python -m streamlit run app/frontend/main.py
```

Streamlit displays the local URL in the terminal (typically `http://localhost:8501`).

## Tests

Run unit tests without requiring a database connection:

```powershell
python -m pytest -q tests/test_dashboard_kpis.py
```

Expected for the current four-test suite: **2 passed, 2 skipped**. The two skipped tests are optional PostgreSQL integration tests.

To run all four tests against the **complete, unchanged** local Olist database:

```powershell
$env:RUN_DB_TESTS="1"
python -m pytest -q tests/test_dashboard_kpis.py
Remove-Item Env:RUN_DB_TESTS
```

Last locally reported result: **4 passed**. Integration tests verify reference KPIs and selected-date consistency; they are not intended for modified or partial datasets.

## Development Roadmap

| Module | Focus | Status |
|---|---|---|
| 1 | Data Foundation & Dashboard | Dashboard implemented and tested; final documentation/release in progress |
| 2 | Schema RAG & Semantic Layer | Planned |
| 3 | Text-to-SQL Engine | Planned |
| 4 | Business Analytics | Planned |
| 5 | LangGraph Agentic Workflows | Planned |
| 6 | Evaluation & Testing | Planned (Module 1 regression tests already implemented) |
| 7 | API, CI/CD & Deployment | Planned |
| 8 | Final Documentation & Portfolio | Planned |

See `docs/development_log.md`, `docs/kpi_validation_results.md`, and `docs/index_performance.md` for implementation history, KPI checks, and database index benchmarks.

## Security Considerations

- Keep database passwords in environment variables or local `.env`, excluded from Git.
- Exclude raw Olist CSV files from version control.
- Future LLM-generated SQL must use restricted read-only database access and SQL validation safeguards.
- **Current dashboard SQL is application-defined; LLM-generated SQL execution is not enabled.**

## License

A project license has not yet been selected.

---

**Project status:** Active development — Module 1 release preparation.

**Author:** Büşra Kurun
