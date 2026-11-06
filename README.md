# InsightPilot AI

### Conversational Business Intelligence — Schema RAG, Local Text-to-SQL, and PostgreSQL Analytics

InsightPilot AI is an incremental AI engineering project for asking business questions about e-commerce data in natural language. It combines a validated PostgreSQL data foundation, a Streamlit analytics dashboard, semantic schema retrieval, and a locally hosted LLM that generates SQL for restricted, read-only execution.

**Current status (6 November 2026):** Modules 1 and 2 are complete; Module 3 (Text-to-SQL) has a working end-to-end backend and is undergoing accuracy and semantic-validation improvements. The latest recorded 12-question Text-to-SQL benchmark achieved **11/12 correct (91.67%)**. This is an experimental benchmark result, not a production reliability claim. **Conversational querying through the dashboard and autonomous agent workflows are not yet implemented.**

## What Works Today

- **Business intelligence dashboard:** Streamlit and Plotly visualizations powered by application-defined, validated KPI queries.
- **Schema RAG:** Multilingual embeddings, PostgreSQL pgvector similarity search, intent-aware context selection, and metric/table dependency enrichment.
- **Local Text-to-SQL:** Ollama running `qwen2.5-coder:7b-instruct`, grounded on retrieved schema and business semantics.
- **Safe execution controls:** SQLGlot-based SQL validation, a dedicated PostgreSQL read-only role, read-only transactions, statement timeouts, and bounded result retrieval.
- **Evaluation:** A reproducible 12-question benchmark, reference SQL execution, result comparison, error categorization, and automated tests.
- **Experimental semantic validation:** A grouping-requirement prototype detects some missing or incorrect `GROUP BY` clauses when given an expected dimension. **It is not yet connected to the production Text-to-SQL pipeline.**

## Technology Stack

| Area | Technologies | Status |
|---|---|---|
| Language and data processing | Python 3.11, Pandas, NumPy | Implemented |
| Relational database | PostgreSQL 18, SQLAlchemy, Psycopg | Implemented |
| Dashboard | Streamlit, Plotly | Implemented |
| Schema RAG | pgvector, sentence-transformers, multilingual MiniLM | Implemented |
| Local LLM | Ollama, Qwen2.5-Coder 7B Instruct | Implemented |
| SQL validation | SQLGlot | Implemented |
| Tests and evaluation | pytest, SQL benchmark runner, result comparator | Implemented |
| Agent orchestration | LangGraph | Planned |
| HTTP API | FastAPI | Planned |
| Containerization and CI/CD | Docker, GitHub Actions | Planned |

## Dataset and Business Semantics

The project uses the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Nine source tables contain **1,550,922 rows** in the local `insightpilot_db` database.

| Table | Rows |
|---|---:|
| `customers` | 99,441 |
| `orders` | 99,441 |
| `order_items` | 112,650 |
| `order_payments` | 103,886 |
| `order_reviews` | 99,224 |
| `products` | 32,951 |
| `sellers` | 3,095 |
| `geolocation` | 1,000,163 |
| `product_category_name_translation` | 71 |
| **Total** | **1,550,922** |

The semantic layer (`semantic/business_semantics.yaml`) documents table grains, five business metrics, business rules, and logical relationships. It distinguishes delivered-product sales revenue from payment receipts and warns against joins that multiply monetary values. Data validation reported **13/13 checks passed**; these checks do not establish that all possible data-quality issues are absent.

**Data setup prerequisite:** The Olist CSV files and local credentials are not committed. Download the dataset separately, create the database tables using the repository's SQL definitions, and load the CSVs using the project's ingestion scripts. A Python environment alone is not sufficient to reproduce database-backed results.

## Architecture

```text
Dashboard path (implemented):
Streamlit (app/frontend/main.py)
  -> Application-defined analytics (app/backend/analytics.py)
  -> PostgreSQL (insightpilot_db)

Text-to-SQL backend path (implemented):
Natural-language question
  -> Schema RAG: multilingual embedding + pgvector
  -> Context selection + dependency enrichment
  -> SQL prompt + business semantics
  -> Ollama / Qwen2.5-Coder 7B
  -> SQLGlot SQL safety validation
  -> Read-only PostgreSQL executor
  -> Structured SQL + query result

Evaluation path (implemented):
12-question benchmark + reference SQL
  -> Text-to-SQL service and reference execution
  -> Result comparator
  -> Evaluation report

Semantic grouping validator (prototype only):
SQL + explicitly provided required dimension
  -> GROUP BY structure check
  -> Validation result
  [Not integrated into the Text-to-SQL service yet]
```

The Text-to-SQL backend is currently exercised through Python services and evaluation scripts; **the Streamlit dashboard does not yet provide a conversational Text-to-SQL interface**. No standalone HTTP API is implemented.

### Selected Repository Layout

```text
app/
  backend/
    analytics.py
    llm_client.py
    sql_prompt_builder.py
    sql_generator.py
    sql_validator.py
    sql_executor.py
    text_to_sql_service.py
    semantic_sql_validator.py
  database/               # Schema, constraints, indexes, KPI SQL
  frontend/               # Streamlit dashboard
semantic/
  business_semantics.yaml
evaluations/
  text_to_sql_benchmark.json
scripts/
  search_schema.py
  validate_benchmark.py
  run_text_to_sql_evaluation.py
tests/
docs/
  development_log.md
  text_to_sql_evaluation.md
  schema_rag_validation_results.md
  data_validation_results.md
artifacts/                  # Generated local artifacts; often Git-ignored
```

This is a selected-path overview, not an exhaustive directory listing.

## Module 1 — Dashboard and Validated KPIs

The dashboard includes order counts, delivered-product revenue, average order value, monthly revenue, order-status distribution, leading products and sellers, and delivery performance, with a purchase-date filter.

| Metric | Full-dataset reference |
|---|---:|
| Total orders | 99,441 |
| Delivered-product revenue, excluding freight | R$ 13,221,498.11 |
| Average order value | R$ 137.04 |
| Delivered orders with items | 96,478 |
| Evaluated delivery records | 96,470 |
| Average delivery time | 12.56 days |
| Late deliveries | 7,826 |
| Late-delivery rate | 8.11% |

These figures apply to the unchanged full Olist dataset, not a filtered date range. Revenue is a product-sales metric, **not** accounting net revenue. See `docs/kpi_validation_results.md`.

## Module 2 — Schema RAG

- Extracted metadata for **nine tables, 52 columns, and six physical foreign keys**.
- Built **18 semantic chunks** (nine table, five metric, four rule chunks).
- Indexed **384-dimensional** multilingual MiniLM embeddings in PostgreSQL pgvector.
- Added question-aware context selection and dependency enrichment.
- Evaluated retrieval on **25 labeled Turkish questions**.

| Retrieval metric | Recorded result |
|---|---:|
| Mean raw Recall@5 | 57.33% |
| Mean final context recall | 79.67% |
| Mean final context precision | 65.80% |
| Perfect final contexts | 10/25 |

These are retrieval-context metrics, **not** SQL accuracy. Results are from the recorded retrieval evaluation and should not be interpreted as measurements of the latest Text-to-SQL pipeline. See `docs/schema_rag_validation_results.md`.

## Module 3 — Text-to-SQL Engine (In Progress)

The backend integrates Schema RAG, a local Ollama LLM, SQL validation, and restricted PostgreSQL execution. Its output includes generated SQL, result rows, and retrieval metadata.

### Benchmark Results

A 12-case Turkish benchmark covers basic counts, filtering, aggregation, joins, and date-based queries. Generated and reference SQL are compared by execution results rather than by SQL string equality.

| Recorded iteration | Correct | Execution accuracy |
|---|---:|---:|
| Initial baseline | 5/12 | 41.67% |
| Context precision improvements | 9/12 | 75.00% |
| Business semantics grounding | **11/12** | **91.67%** |

**Remaining failure — SQL_012:** “Her eyaletteki müşterilerin verdiği sipariş sayısını göster.” The model still generates an overall order count rather than joining customers and grouping by `customer_state`, despite the required schema chunks being retrieved. A prompt-planning revision did not fix this case in an isolated live test.

A separate `semantic_sql_validator.py` prototype can flag a missing required grouping dimension. It **does not infer that dimension from the question, check all join semantics, repair SQL, or run inside the end-to-end service yet**. The 91.67% figure therefore predates integration of any semantic validation or retry mechanism.

### Automated Tests

Latest observed local test run (6 November 2026):

```text
266 passed, 2 skipped in 12.64s
```

Passing unit tests and a small benchmark do not prove production-level accuracy or security.

## Getting Started (Windows PowerShell)

### 1. Clone and create an environment

```powershell
git clone https://github.com/busrakurunceng/InsightPilot-AI.git
cd InsightPilot-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

This assumes the repository's `requirements.txt` reflects the current environment. In particular, the Text-to-SQL modules require `sqlglot`, `sentence-transformers`, and `PyYAML` in addition to the dashboard and database dependencies. Verify the dependency file before reproducing the setup.

### 3. Configure PostgreSQL and Ollama

Create a local `.env` in the repository root and supply credentials for your own database. The exact connection variables used by the application include:

```dotenv
DATABASE_URL=postgresql+psycopg://your_user:your_password@127.0.0.1:5432/insightpilot_db
READONLY_DB_USER=insightpilot_reader
READONLY_DB_PASSWORD=your_readonly_password
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5-coder:7b-instruct
```

The read-only PostgreSQL role must be created and granted the appropriate SELECT permissions separately. Never commit `.env` or real credentials. The existing dashboard may also use `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`; consult `app/backend/db.py` for its active configuration.

Install and start Ollama, then obtain the local model:

```powershell
ollama pull qwen2.5-coder:7b-instruct
```

Ensure PostgreSQL is running, all nine Olist tables are populated, and Schema RAG embeddings have been loaded into `public.schema_embeddings` before running live Text-to-SQL operations.

### 4. Run the dashboard

```powershell
python -m streamlit run app/frontend/main.py
```

The dashboard uses application-defined analytical SQL, not the conversational Text-to-SQL backend.

### 5. Run automated tests

```powershell
python -m pytest -q
```

Optional database-backed dashboard tests can be enabled against a correctly populated local database:

```powershell
$env:RUN_DB_TESTS = "1"
python -m pytest tests/test_dashboard_kpis.py -v
Remove-Item Env:RUN_DB_TESTS
```

### 6. Validate the benchmark references

```powershell
python -m scripts.validate_benchmark
```

### 7. Run the live Text-to-SQL benchmark (optional)

**Back up the existing report before running this command:** the evaluation runner writes to `artifacts/evaluations/text_to_sql_report.json` and may overwrite a prior report.

```powershell
$report = "artifacts/evaluations/text_to_sql_report.json"
if (Test-Path $report) {
    $backup = "artifacts/evaluations/text_to_sql_report_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
    Copy-Item $report $backup
    Write-Host "Backup created: $backup"
}
python -m scripts.run_text_to_sql_evaluation
```

The live evaluation requires the local Ollama model, embeddings, database, and read-only credentials. Results may vary between model runs and environment configurations. Generated evaluation artifacts may be Git-ignored.

## Security and Limitations

- SQLGlot validation restricts accepted SQL to approved read-only query structures and an allowed set of tables/functions.
- PostgreSQL execution uses a dedicated read-only role and read-only transactions; database permissions remain the final access-control boundary.
- Query timeouts and row limits reduce operational risk but do not eliminate all expensive-query risks.
- Semantic correctness is **not** guaranteed by SQL syntax or safety validation.
- The grouping validator is a standalone prototype, not yet enforced in the Text-to-SQL service.
- Turkish paraphrases, multi-metric questions, complex joins, and ambiguous requests require broader evaluation.
- The current benchmark has only 12 cases; the reported accuracy is not a generalization estimate.
- No public API, conversational dashboard integration, agentic workflows, CI/CD pipeline, or production deployment is claimed.

## Development Roadmap

| Module | Focus | Status |
|---|---|---|
| 1 | Data Foundation & Dashboard | Completed — `v0.1.0-data-dashboard` |
| 2 | Schema RAG & Semantic Layer | Completed — `v0.2.0-schema-rag` |
| 3 | Text-to-SQL Engine | End-to-end backend implemented; evaluation and semantic validation in progress |
| 4 | Business Analytics | Planned beyond existing dashboard KPIs |
| 5 | LangGraph Agentic Workflows | Planned |
| 6 | Extended Evaluation & Testing | Planned; baseline evaluation and regression tests already implemented |
| 7 | API, CI/CD & Deployment | Planned |
| 8 | Final Documentation & Portfolio | Planned; documentation maintained incrementally |

## Documentation

- [`docs/development_log.md`](docs/development_log.md) — implementation history, technical decisions, and test milestones.
- [`docs/text_to_sql_evaluation.md`](docs/text_to_sql_evaluation.md) — benchmark results, failure analysis, and limitations.
- [`docs/schema_rag_validation_results.md`](docs/schema_rag_validation_results.md) — retrieval evaluation.
- [`docs/data_validation_results.md`](docs/data_validation_results.md) — data-quality checks.
- [`docs/kpi_validation_results.md`](docs/kpi_validation_results.md) — KPI reconciliation.
- [`docs/index_performance.md`](docs/index_performance.md) — database indexing experiments.

## License

A project license has not yet been selected.

---

**Project status:** Modules 1–2 complete; Module 3 Text-to-SQL backend implemented and being improved. Latest recorded evaluation: 11/12 correct. Latest local test suite: 266 passed, 2 skipped.

**Author:** Büşra Kurun
