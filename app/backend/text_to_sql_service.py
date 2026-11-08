
from dataclasses import dataclass
from typing import Any

from app.backend.question_dimension_mapper import (
    infer_question_dimension,
)
from app.backend.semantic_sql_validator import (
    validate_grouping_requirement,
)
from app.backend.sql_executor import SQLExecutor
from app.backend.sql_generator import SQLGenerator
from app.backend.sql_validator import validate_sql


OLIST_ALLOWED_TABLES = frozenset({
    "customers",
    "orders",
    "order_items",
    "order_payments",
    "order_reviews",
    "products",
    "sellers",
    "geolocation",
    "product_category_name_translation",
})


class TextToSQLError(RuntimeError):
    """Base error for the Text-to-SQL pipeline."""


class InsufficientContextError(TextToSQLError):
    """The model could not generate a supported query."""


class SQLGenerationPipelineError(TextToSQLError):
    """SQL generation failed."""


class SQLValidationPipelineError(TextToSQLError):
    """Generated SQL failed security validation."""


class SQLSemanticValidationPipelineError(SQLValidationPipelineError):
    """Generated SQL does not satisfy a required dimension."""


class SQLExecutionPipelineError(TextToSQLError):
    """Validated SQL could not be executed."""


@dataclass(frozen=True)
class TextToSQLResult:
    question: str
    sql: str
    model: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    selected_chunk_ids: list[str]
    dependency_chunk_ids: list[str]


class TextToSQLService:
    """Orchestrate SQL generation, validation, retry and execution."""

    def __init__(
        self,
        generator: SQLGenerator | None = None,
        executor: SQLExecutor | None = None,
        allowed_tables: set[str] | frozenset[str] = OLIST_ALLOWED_TABLES,
    ):
        if not allowed_tables:
            raise ValueError("Table allowlist must not be empty.")

        self.allowed_tables = frozenset(allowed_tables)

        self.generator = (
            generator if generator is not None
            else SQLGenerator()
        )

        self.executor = (
            executor if executor is not None
            else SQLExecutor(
                allowed_tables=set(self.allowed_tables)
            )
        )

        if frozenset(self.executor.allowed_tables) != self.allowed_tables:
            raise ValueError(
                "Service and executor table allowlists must match."
            )

    def _validate_security(self, sql: str):
        try:
            return validate_sql(
                sql,
                allowed_tables=set(self.allowed_tables),
            )
        except Exception as exc:
            raise SQLValidationPipelineError(
                "Generated SQL did not pass security validation."
            ) from exc

    def _validate_semantics(
        self,
        sql: str,
        required_dimension: str | None,
    ) -> list[str]:
        if required_dimension is None:
            return []

        try:
            result = validate_grouping_requirement(
                sql,
                required_dimension=required_dimension,
            )
        except Exception as exc:
            raise SQLSemanticValidationPipelineError(
                "Semantic SQL validation failed."
            ) from exc

        return result.issues

    def run(self, question: str) -> TextToSQLResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must not be empty.")

        question = question.strip()

        # 1. Initial SQL generation.
        try:
            generation = self.generator.generate(question)
        except Exception as exc:
            raise SQLGenerationPipelineError(
                "SQL generation failed."
            ) from exc

        sql = generation.sql.strip()

        if sql.upper() == "INSUFFICIENT_CONTEXT":
            raise InsufficientContextError(
                "Insufficient schema or business context."
            )

        # 2. Security validation always runs first.
        validation = self._validate_security(sql)

        # 3. Infer the required grouping dimension.
        try:
            required_dimension = infer_question_dimension(question)
        except Exception as exc:
            raise SQLSemanticValidationPipelineError(
                "Could not determine semantic grouping requirements."
            ) from exc

        # 4. Validate semantic grouping requirements.
        issues = self._validate_semantics(
            validation.sql,
            required_dimension,
        )

        # 5. Retry exactly once for semantic mismatches.
        if issues:
            try:
                generation = self.generator.regenerate(
                    generation,
                    issues=issues,
                )
            except Exception as exc:
                raise SQLGenerationPipelineError(
                    "SQL regeneration failed."
                ) from exc

            retry_sql = generation.sql.strip()

            if retry_sql.upper() == "INSUFFICIENT_CONTEXT":
                raise InsufficientContextError(
                    "Insufficient context after SQL regeneration."
                )

            # The regenerated SQL must pass security checks too.
            validation = self._validate_security(retry_sql)

            retry_issues = self._validate_semantics(
                validation.sql,
                required_dimension,
            )

            if retry_issues:
                raise SQLSemanticValidationPipelineError(
                    "SQL regeneration did not satisfy "
                    f"the required dimension ({required_dimension}): "
                    + "; ".join(retry_issues)
                )

        # 6. Execute only fully validated SQL.
        try:
            execution = self.executor.execute(validation.sql)
        except Exception as exc:
            raise SQLExecutionPipelineError(
                "Validated SQL execution failed."
            ) from exc

        return TextToSQLResult(
            question=question,
            sql=validation.sql,
            model=generation.model,
            columns=execution.columns,
            rows=execution.rows,
            row_count=execution.row_count,
            truncated=execution.truncated,
            selected_chunk_ids=generation.selected_chunk_ids,
            dependency_chunk_ids=generation.dependency_chunk_ids,
        )
