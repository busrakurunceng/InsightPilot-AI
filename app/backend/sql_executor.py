
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

from app.backend.sql_validator import validate_sql


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class SQLExecutionError(RuntimeError):
    """Raised when SQL execution fails."""


@dataclass(frozen=True)
class SQLExecutionResult:
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool


def get_readonly_engine() -> Engine:
    """
    Create an engine using the dedicated read-only role.

    Never fall back to the administrator credentials.
    """
    username = os.getenv("READONLY_DB_USER")
    password = os.getenv("READONLY_DB_PASSWORD")

    if not username or not password:
        raise SQLExecutionError(
            "Read-only database credentials are missing."
        )

    url = URL.create(
        drivername="postgresql+psycopg",
        username=username,
        password=password,
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "insightpilot_db"),
    )

    return create_engine(
        url,
        pool_pre_ping=True,
    )


class SQLExecutor:
    def __init__(
        self,
        engine: Engine | None = None,
        allowed_tables: set[str] | None = None,
        max_rows: int = 100,
        timeout_ms: int = 5000,
    ):
        if max_rows < 1:
            raise ValueError("max_rows must be at least 1.")

        if timeout_ms < 1:
            raise ValueError("timeout_ms must be positive.")

        if not allowed_tables:
            raise ValueError(
                "An explicit table allowlist is required."
            )

        self.engine = (
            engine if engine is not None
            else get_readonly_engine()
        )
        self.allowed_tables = allowed_tables
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms

    def execute(self, sql: str) -> SQLExecutionResult:
        """
        Validate and execute SQL in a read-only transaction.
        """

        validation = validate_sql(
            sql,
            allowed_tables=self.allowed_tables,
        )

        try:
            with self.engine.connect() as connection:
                with connection.begin():
                    connection.execute(
                        text("SET TRANSACTION READ ONLY")
                    )

                    connection.execute(
                        text(
                            "SELECT set_config("
                            "'statement_timeout', "
                            ":timeout, true)"
                        ),
                        {"timeout": str(self.timeout_ms)},
                    )

                    # Limit returned rows without changing
                    # the original aggregation semantics.
                    limited_sql = (
                        "SELECT * FROM ("
                        + validation.sql.rstrip(";")
                        + ") AS insightpilot_result "
                        + f"LIMIT {self.max_rows + 1}"
                    )

                    result = connection.execute(
                        text(limited_sql)
                    )

                    columns = list(result.keys())
                    fetched_rows = result.mappings().fetchmany(
                        self.max_rows + 1
                    )

                    truncated = (
                        len(fetched_rows) > self.max_rows
                    )

                    rows = [
                        dict(row)
                        for row in fetched_rows[:self.max_rows]
                    ]

            return SQLExecutionResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                truncated=truncated,
            )

        except Exception as exc:
            raise SQLExecutionError(
                f"SQL execution failed: {exc}"
            ) from exc
