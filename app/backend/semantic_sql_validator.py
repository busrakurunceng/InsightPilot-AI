
from dataclasses import dataclass

import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class SemanticValidationResult:
    valid: bool
    issues: list[str]


def validate_grouping_requirement(
    sql: str,
    required_dimension: str | None = None,
) -> SemanticValidationResult:
    """
    Check whether a generated SQL query preserves
    a required grouping dimension.

    This is a structural validation prototype.
    """
    if not required_dimension:
        return SemanticValidationResult(
            valid=True,
            issues=[],
        )

    try:
        expression = sqlglot.parse_one(
            sql,
            read="postgres",
        )
    except sqlglot.errors.ParseError:
        return SemanticValidationResult(
            valid=False,
            issues=["SQL could not be parsed."],
        )

    issues = []

    group = expression.args.get("group")

    if group is None:
        issues.append(
            "The query is missing GROUP BY for "
            f"required dimension: {required_dimension}"
        )
    else:
        grouped_columns = {
            column.name.lower()
            for group_expression in group.expressions
            for column in group_expression.find_all(
                exp.Column
            )
        }

        dimension_name = required_dimension.split(".")[-1]

        if dimension_name.lower() not in grouped_columns:
            issues.append(
                "The required dimension is not "
                f"grouped: {required_dimension}"
            )

    return SemanticValidationResult(
        valid=not issues,
        issues=issues,
    )
