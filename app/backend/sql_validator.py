
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


class SQLValidationError(ValueError):
    """Raised when generated SQL fails validation."""


@dataclass(frozen=True)
class SQLValidationResult:
    sql: str
    referenced_tables: tuple[str, ...]


FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Command,
    exp.Into,
    exp.Merge,
)

ALLOWED_FUNCTIONS = (
    exp.Count,
    exp.Sum,
    exp.Avg,
    exp.Min,
    exp.Max,
    exp.Round,
    exp.Abs,
    exp.Coalesce,
)


def validate_sql(
    sql: str,
    allowed_tables: set[str],
) -> SQLValidationResult:
    """
    Validate generated PostgreSQL SQL without executing it.

    This is an application-level validation layer.
    It does not replace read-only database permissions.
    """

    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("SQL must not be empty.")

    if not allowed_tables:
        raise SQLValidationError(
            "An explicit table allowlist is required."
        )

    normalized_allowed_tables = {
        table.lower()
        for table in allowed_tables
    }

    if sql.strip() == "INSUFFICIENT_CONTEXT":
        raise SQLValidationError(
            "The model did not generate SQL."
        )

    try:
        statements = sqlglot.parse(
            sql,
            read="postgres",
            error_level="RAISE",
        )
    except (ParseError, ValueError) as exc:
        raise SQLValidationError(
            f"Invalid PostgreSQL SQL: {exc}"
        ) from exc

    if len(statements) != 1 or statements[0] is None:
        raise SQLValidationError(
            "Exactly one SQL statement is required."
        )

    statement = statements[0]

    if not isinstance(statement, exp.Select):
        raise SQLValidationError(
            "Only SELECT statements are allowed."
        )

    # Validate SQL operations and functions.
    for node in statement.walk():
        if isinstance(node, FORBIDDEN_EXPRESSIONS):
            raise SQLValidationError(
                "Forbidden SQL operation detected."
            )

        if isinstance(node, exp.Func):
            if type(node) not in ALLOWED_FUNCTIONS:
                raise SQLValidationError(
                    f"SQL function not allowed: {node.sql_name()}"
                )

        if isinstance(node, exp.Lock):
            raise SQLValidationError(
                "Locking clauses are not allowed."
            )

    # Collect CTE aliases.
    cte_names = {
        cte.alias.lower()
        for cte in statement.find_all(exp.CTE)
    }

    # Prevent CTE aliases from shadowing physical tables.
    if cte_names & normalized_allowed_tables:
        raise SQLValidationError(
            "CTE names cannot shadow allowed database tables."
        )

    referenced_tables = set()

    for table in statement.find_all(exp.Table):
        table_name = table.name.lower()

        # Reject cross-database references.
        if table.catalog:
            raise SQLValidationError(
                "Catalog-qualified tables are not allowed."
            )

        # Only the public schema is permitted.
        if table.db and table.db.lower() != "public":
            raise SQLValidationError(
                "Only the public schema is allowed."
            )

        # CTE aliases are not physical database tables.
        if table_name in cte_names:
            if table.db:
                raise SQLValidationError(
                    "Schema-qualified CTE references are not allowed."
                )
            continue

        # Validate physical table access.
        if table_name not in normalized_allowed_tables:
            raise SQLValidationError(
                f"Table not allowed: {table_name}"
            )

        referenced_tables.add(table_name)

    if not referenced_tables:
        raise SQLValidationError(
            "At least one allowed database table is required."
        )

    return SQLValidationResult(
        sql=sql.strip(),
        referenced_tables=tuple(sorted(referenced_tables)),
    )
