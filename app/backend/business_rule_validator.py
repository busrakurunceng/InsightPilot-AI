"""Conservative SQLGlot checks for explicitly recognized Olist business intents.

This is not a replacement for security or schema validation. Unrecognized
questions are intentionally left to the existing pipeline.
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp

from app.backend.schema_relevance import normalize_text


def _tokens(question: str) -> set[str]:
    return set(normalize_text(question).split())


def _physical_tables(statement: exp.Select) -> set[str]:
    return {t.name.lower() for t in statement.find_all(exp.Table)}


def _aliases(statement: exp.Select) -> dict[str, str]:
    result = {}
    for table in statement.find_all(exp.Table):
        result[table.alias_or_name.lower()] = table.name.lower()
        result[table.name.lower()] = table.name.lower()
    return result


def _column_is(column: exp.Expression, table: str, name: str,
               aliases: dict[str, str], tables: set[str]) -> bool:
    if not isinstance(column, exp.Column) or column.name.lower() != name:
        return False
    if column.table:
        return aliases.get(column.table.lower()) == table
    return tables == {table}


def validate_business_rules(question: str, sql: str) -> list[str]:
    """Return actionable issues; fail closed for recognized, unverifiable SQL."""
    tokens = _tokens(question)
    distinct_customer = bool(tokens & {"farkli", "tekil", "benzersiz"}) and bool(
        tokens & {"musteri", "musteriler", "musterinin", "musterilerin"}
    )
    item_revenue = bool(tokens & {"gelir", "geliri", "getiren", "satis", "satislari"}) and bool(
        tokens & {"kategori", "kategorisi", "kategorileri", "kategorisinden", "kategorisinde"}
    )
    explicitly_delivered = bool(tokens & {"teslim", "edilmis", "edilen", "delivered"})
    if not distinct_customer and not (item_revenue and not explicitly_delivered):
        return []

    try:
        statements = sqlglot.parse(sql, read="postgres", error_level="RAISE")
    except (sqlglot.errors.ParseError, ValueError):
        return ["Business rule validation could not parse SQL."]
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        return ["Business rule validation requires a single SELECT."]
    stmt = statements[0]
    # Do not certify unsupported nested scopes; avoids alias/WHERE confusion.
    if any(isinstance(node, (exp.Subquery, exp.With, exp.Union, exp.Intersect, exp.Except))
           for node in stmt.walk()):
        return ["Business rule validation cannot verify nested SQL scopes."]
    tables = _physical_tables(stmt)
    aliases = _aliases(stmt)
    issues = []
    if distinct_customer:
        valid_count = any(
            isinstance(node, exp.Count)
            and isinstance(node.this, exp.Distinct)
            and any(_column_is(col, "customers", "customer_unique_id", aliases, tables)
                    for col in node.this.find_all(exp.Column))
            for node in stmt.find_all(exp.Count)
        )
        if not valid_count:
            issues.append(
                "Distinct real customers must be counted as "
                "COUNT(DISTINCT customers.customer_unique_id), joined through "
                "orders.customer_id = customers.customer_id; "
                "orders.customer_id is an order-linked record ID."
            )
    if item_revenue and not explicitly_delivered:
        # A delivered-only predicate is not authorized by this question.
        where = stmt.args.get("where")
        if where is not None:
            for eq in where.find_all(exp.EQ):
                sides = ((eq.left, eq.right), (eq.right, eq.left))
                for col, value in sides:
                    if (_column_is(col, "orders", "order_status", aliases, tables)
                            and isinstance(value, exp.Literal)
                            and value.is_string and value.this.lower() == "delivered"):
                        issues.append(
                            "Remove unrequested orders.order_status = 'delivered' filter. "
                            "For general category product revenue use SUM(order_items.price) "
                            "without an order-status restriction."
                        )
                        break
    return issues
