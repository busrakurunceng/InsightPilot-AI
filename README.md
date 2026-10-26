# InsightPilot AI

### Agentic Conversational Business Intelligence Platform

InsightPilot AI is an end-to-end AI engineering project designed to make business data accessible through natural language.

The platform aims to enable users to ask analytical questions, automatically generate and validate SQL queries, retrieve relevant business context, and visualize insights through an interactive dashboard.

The project is being developed incrementally, with a working and testable deliverable at the end of each major development phase.

## Project Objectives

- Transform natural-language business questions into SQL queries.
- Use Retrieval-Augmented Generation (RAG) to understand database schemas and business metrics.
- Execute validated SQL queries against PostgreSQL.
- Generate analytical summaries and interactive visualizations.
- Implement multi-step analytical workflows using agentic AI.
- Evaluate query accuracy, retrieval quality, security, and system performance.

## Technology Stack

| Category | Technologies |
|---|---|
| Programming | Python |
| Database | PostgreSQL |
| Data Processing | Pandas, NumPy |
| Database Integration | SQLAlchemy, Psycopg |
| Dashboard | Streamlit, Plotly |
| LLM Orchestration (Planned) | LangChain, LangGraph |
| Semantic Retrieval (Planned) | pgvector, Embeddings |
| SQL Validation (Planned) | SQLGlot |
| API (Planned) | FastAPI |
| Testing | Pytest |
| Deployment (Planned) | Docker, GitHub Actions |

## Dataset

The project uses the **Brazilian E-Commerce Public Dataset by Olist**, available on Kaggle.

Dataset: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

The dataset contains nine CSV files covering customers, orders, order items, payments, reviews, products, sellers, geolocation, and product category translations.

Raw datasets are excluded from version control.

## System Architecture

The planned architecture follows this general workflow:

**User Question → Semantic Retrieval → LLM-Based SQL Generation → SQL Validation → PostgreSQL → Analytics → Visualization**

Future versions will introduce LangGraph-based multi-step workflows for more complex business questions.

## Development Roadmap

| Phase | Module | Status |
|---|---|---|
| 1 | Data Foundation & Initial Dashboard | In Progress |
| 2 | Schema RAG & Semantic Layer | Planned |
| 3 | Text-to-SQL Engine | Planned |
| 4 | Analytics & Visualization MVP | Planned |
| 5 | Agentic Analytical Workflows | Planned |
| 6 | Evaluation & Testing | Planned |
| 7 | API, Containerization & Deployment | Planned |
| 8 | Documentation & Final Release | Planned |

## Current Progress

Completed:

- Initialized the Python development environment.
- Downloaded and explored the Olist dataset.
- Created an initial data exploration report.
- Installed and configured PostgreSQL 18.
- Created the `insightpilot_db` database.
- Successfully tested Python-to-PostgreSQL connectivity.
- Initialized the Git repository and published the project on GitHub.

Next milestone: Design PostgreSQL tables, import the dataset, validate data integrity, and build the first analytical dashboard.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/busrakurunceng/InsightPilot-AI.git
cd InsightPilot-AI
```

Create and activate a virtual environment on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project dependencies required for the current development stage:

```bash
pip install pandas numpy sqlalchemy "psycopg[binary]" streamlit plotly python-dotenv pytest
```

Configure PostgreSQL connection settings in a local `.env` file:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=insightpilot_db
DB_USER=postgres
DB_PASSWORD=your_local_password
```

Test the database connection:

```bash
python -m scripts.test_database
```

**Note:** The application is still under active development. Full setup and execution instructions will be added as the project progresses. Do not use the PostgreSQL superuser for LLM-generated queries.

## Security Considerations

- Database credentials are stored in environment variables.
- Local `.env` files are excluded from Git.
- Raw datasets are excluded from version control.
- Future Text-to-SQL execution will use restricted, read-only database access.
- SQL validation and execution safeguards will be implemented before enabling LLM-generated queries.

## License

A project license has not yet been selected.

---

**Project Status:** Active Development

**Author:** Büşra Kurun