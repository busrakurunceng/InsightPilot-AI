# InsightPilot AI

### Agentic Conversational Business Intelligence Platform

InsightPilot AI is an incremental AI engineering project aiming to make e-commerce business data accessible through natural-language questions, validated SQL, and analytical visualizations.

**Current deliverable (Modules 1–2):** a validated PostgreSQL-backed Streamlit business intelligence dashboard and an MVP Schema RAG / semantic retrieval layer. **Text-to-SQL, conversational querying, and autonomous agent workflows are not implemented yet.**

## Project Objectives

- Translate natural-language business questions into SQL (planned for Module 3).
- Retrieve schema, metric, and business-rule context using Schema RAG (MVP implemented).
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
| Semantic retrieval | pgvector, sentence-transformers embeddings | In use (Module 2) |
| SQL validation | SQLGlot | Planned |
| API | FastAPI | Planned |
| Deployment | Docker, GitHub Actions | Planned |

## Dataset

This project uses the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), comprising nine CSV files: customers, orders, order items, order payments, order reviews, products, sellers, geolocation, and product category translations.

The local PostgreSQL database is named `insightpilot_db`. The nine source tables contain **1,550,922 rows in total**. Raw datasets and local credentials are not committed to Git.

> **Data setup prerequisite:** Download the dataset from Kaggle and load the nine CSVs into the matching PostgreSQL tables using the project's data-loading workflow. Cloning the repository and installing Python dependencies alone will not populate the database. Refer to the repository's `scripts/`, `app/database/`, and `docs/` for the data-foundation work; confirm the relevant import instructions before running a fresh setup.

## Current Architecture

Module 1's dashboard and Module 2's Schema RAG are implemented as separate, reusable paths within the same Python repository. There is no standalone HTTP API yet.

```text
Dashboard path:
Streamlit UI (app/frontend/main.py)
    -> Analytics / parameterized SQL (app/backend/analytics.py)
    -> Database connection (app/backend/db.py)
    -> PostgreSQL (insightpilot_db)

Schema RAG path (currently available through scripts, not the dashboard UI):
Natural-language question
    -> Embedding + pgvector retrieval (scripts/search_schema.py)
    -> Intent / rule-based context selection (app/backend/)
    -> Metric and rule dependency enrichment (app/backend/)
    -> Schema / metric / rule context for future Text-to-SQL

Semantic source: semantic/business_semantics.yaml
Schema source: docs/schema_catalog.json
Generated chunks / embeddings: artifacts/
```

The RAG layer does **not** generate or execute LLM-authored SQL. The dashboard continues to use application-defined SQL.

### Repository layout (selected paths)

```text
app/
  backend/       # Analytics, database access, retrieval selection and dependencies
  database/      # Database schema, constraints, indexes and SQL references
  frontend/      # Streamlit dashboard
semantic/         # YAML business semantics
scripts/          # Data preparation, embedding, retrieval and evaluation utilities
artifacts/        # Generated retrieval inputs and evaluation outputs
tests/            # Automated tests
docs/             # Validation evidence and development log
```

This is a relevant-file overview, not an exhaustive directory listing.

## Schema RAG — Module 2 MVP

- Extracted metadata for nine tables, 52 columns, and six physical foreign keys.
- Defined five business metrics, four business rules, and a logical category-translation relationship.
- Generated 18 schema chunks (nine tables, five metrics, four rules).
- Generated 384-dimensional multilingual MiniLM embeddings and stored 18 records in PostgreSQL with pgvector.
- Implemented semantic Top-5 retrieval, intent/rule-based context selection, and dependency enrichment.
- Evaluated retrieval using 25 labeled questions across baseline, paraphrase, business semantics, relationships, and complex categories.

| Retrieval measure | 25-question benchmark |
|---|---:|
| Mean Raw Recall@5 | 57.33% |
| Mean final Context Recall | 79.67% |
| Mean final Context Precision | 65.80% |
| Perfect final contexts | 10/25 |

These are **retrieval-context metrics**, not SQL accuracy or end-to-end question-answering accuracy. Baseline questions achieved 100% final context recall and precision; paraphrases, multiple metrics, complex joins, and specialized rules remain limited. See `docs/schema_rag_validation_results.md` for evidence and known limitations.

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

## Tests and Retrieval Evaluation

Run the complete automated test suite from the repository root:

```powershell
python -m pytest tests/ -q
```

**Last observed:** `70 passed, 2 skipped` (30 October 2026). The two skipped cases are optional database-backed dashboard integration tests.

To run those optional checks against the **complete, unchanged** local Olist database:

```powershell
$env:RUN_DB_TESTS = "1"
python -m pytest tests/test_dashboard_kpis.py -v
Remove-Item Env:RUN_DB_TESTS
```

To rerun the labeled retrieval benchmark, start PostgreSQL and ensure the `schema_embeddings` table contains the 18 indexed chunks, then run:

```powershell
python scripts/evaluate_retrieval.py
```

The benchmark definition is `artifacts/evaluations/schema_benchmark.json`; the evaluation writes `schema_robustness_evaluation.json` and `.csv` in the same directory. Results depend on the configured database, embeddings, and retrieval implementation.

## Development Roadmap

| Module | Focus | Status |
|---|---|---|
| 1 | Data Foundation & Dashboard | Completed — `v0.1.0-data-dashboard` |
| 2 | Schema RAG & Semantic Layer | MVP implemented and evaluated; release closure pending Git tag |
| 3 | Text-to-SQL Engine | Planned |
| 4 | Business Analytics | Planned |
| 5 | LangGraph Agentic Workflows | Planned |
| 6 | Evaluation & Testing | Planned (Module 1 regression tests already implemented) |
| 7 | API, CI/CD & Deployment | Planned |
| 8 | Final Documentation & Portfolio | Planned |

See `docs/development_log.md`, `docs/kpi_validation_results.md`, `docs/index_performance.md`, and `docs/schema_rag_validation_results.md` for implementation history and validation evidence.

## Security Considerations

- Keep database passwords in environment variables or local `.env`, excluded from Git.
- Exclude raw Olist CSV files from version control.
- Future LLM-generated SQL must use restricted read-only database access and SQL validation safeguards.
- **Current dashboard SQL is application-defined; LLM-generated SQL execution is not enabled.**

## License

A project license has not yet been selected.

---

**Project status:** Modules 1–2 implemented (Module 2 MVP closure pending release tag); Module 3 — Text-to-SQL is next.

**Author:** Büşra Kurun
