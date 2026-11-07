
"""Structural semantic validation for SQL grouping dimensions."""

from dataclasses import dataclass

import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class SemanticValidationResult:
    valid: bool
    issues: list[str]


def _table_aliases(expression: exp.Select) -> dict[str, str]:
    """Map table aliases to physical table names."""
    aliases: dict[str, str] = {}

    for table in expression.find_all(exp.Table):
        table_name = table.name.lower()
        alias = table.alias_or_name.lower()

        aliases[alias] = table_name
        aliases[table_name] = table_name

    return aliases


def _matches_dimension(
    column: exp.Expression,
    required_table: str,
    required_column: str,
    aliases: dict[str, str],
    physical_tables: set[str],
) -> bool:
    """Check column identity, including table alias resolution."""
    if not isinstance(column, exp.Column):
        return False

    if column.name.lower() != required_column:
        return False

    qualifier = column.table.lower() if column.table else ""

    if qualifier:
        return aliases.get(qualifier) == required_table

    # An unqualified column is accepted only when the query
    # references exactly one physical table.
    return physical_tables == {required_table}


def validate_grouping_requirement(
    sql: str,
    required_dimension: str | None = None,
) -> SemanticValidationResult:
    """Validate a required grouping dimension in a simple SELECT query.

    Checks:
    - SQL parsing and SELECT structure
    - Required physical table
    - Required dimension in SELECT
    - Required dimension in GROUP BY
    - Table alias resolution

    Complex query shapes are conservatively rejected when a
    required dimension cannot be verified unambiguously.

    This is not a replacement for the SQL security validator.
    """
    if not required_dimension:
        return SemanticValidationResult(valid=True, issues=[])

    if not isinstance(sql, str) or not sql.strip():
        return SemanticValidationResult(
            valid=False,
            issues=["SQL must be a non-empty string."],
        )

    parts = required_dimension.split(".")

    if len(parts) != 2 or not all(parts):
        return SemanticValidationResult(
            valid=False,
            issues=["Required dimension must be table.column."],
        )

    required_table, required_column = (
        part.lower() for part in parts
    )

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError:
        return SemanticValidationResult(
            valid=False,
            issues=["SQL could not be parsed."],
        )

    if (
        len(statements) != 1
        or statements[0] is None
        or not isinstance(statements[0], exp.Select)
    ):
        return SemanticValidationResult(
            valid=False,
            issues=["A single SELECT query is required."],
        )

    expression = statements[0]

    # This validator currently handles a single SELECT scope.
    # Nested queries, CTEs, set operations and derived tables
    # require scope-aware validation in a future version.
    unsupported_types = (
        exp.Subquery,
        exp.With,
        exp.Union,
        exp.Intersect,
        exp.Except,
    )

    if any(
        isinstance(node, unsupported_types)
        for node in expression.walk()
    ):
        return SemanticValidationResult(
            valid=False,
            issues=[
                "Complex query scope is not supported by "
                "the grouping validator."
            ],
        )

    tables = list(expression.find_all(exp.Table))

    if not tables:
        return SemanticValidationResult(
            valid=False,
            issues=["SQL query does not reference a table."],
        )

    physical_tables = {
        table.name.lower()
        for table in tables
    }

    aliases = _table_aliases(expression)
    issues: list[str] = []

    if required_table not in physical_tables:
        issues.append(
            f"Required table is missing: {required_table}"
        )

    # A projection must expose the actual dimension column.
    # SELECT * and computed expressions are not treated as
    # proof that the dimension is present.
    selected_columns: list[exp.Expression] = []

    for projection in expression.expressions:
        if isinstance(projection, exp.Alias):
            selected_columns.append(projection.this)
        else:
            selected_columns.append(projection)

    has_selected_dimension = any(
        _matches_dimension(
            column,
            required_table,
            required_column,
            aliases,
            physical_tables,
        )
        for column in selected_columns
    )

    if not has_selected_dimension:
        issues.append(
            "Required dimension is missing from SELECT: "
            f"{required_dimension}"
        )

    group = expression.args.get("group")

    if group is None or not group.expressions:
        issues.append(
            "The query is missing GROUP BY for "
            f"required dimension: {required_dimension}"
        )
    else:
        has_grouped_dimension = any(
            _matches_dimension(
                column,
                required_table,
                required_column,
                aliases,
                physical_tables,
            )
            for column in group.expressions
        )

        if not has_grouped_dimension:
            issues.append(
                "The required dimension is not grouped: "
                f"{required_dimension}"
            )

    return SemanticValidationResult(
        valid=not issues,
        issues=issues,
    )
