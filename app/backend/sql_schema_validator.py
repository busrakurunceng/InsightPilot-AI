
"""Validate SQL against the actual PostgreSQL schema.

This module performs a non-executing EXPLAIN after the
application-level SQL security validator has approved
the statement.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.backend.sql_validator import validate_sql


class SQLSchemaValidationError(ValueError):
    """Raised when SQL cannot be planned against the database."""


def validate_sql_schema(
    sql: str,
    *,
    engine: Engine,
    allowed_tables: set[str] | frozenset[str],
    timeout_ms: int = 5000,
) -> None:
    """Check that PostgreSQL can resolve the validated SQL.

    EXPLAIN without ANALYZE does not execute the SELECT.
    The transaction is explicitly read-only.
    """

    if timeout_ms < 1:
        raise ValueError("timeout_ms must be positive.")

    # Never send unapproved SQL to PostgreSQL.
    validation = validate_sql(
        sql,
        allowed_tables=set(allowed_tables),
    )

    explain_sql = (
        "EXPLAIN (FORMAT JSON) "
        + validation.sql.rstrip(";")
    )

    try:
        with engine.connect() as connection:
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
                    {"timeout": str(timeout_ms)},
                )

                connection.execute(
                    text(explain_sql)
                )

    except Exception as exc:
        raise SQLSchemaValidationError(
            "SQL could not be validated against "
            "the PostgreSQL schema."
        ) from exc
