
from dataclasses import dataclass
from typing import Any

from app.backend.sql_generator import SQLGenerator
from app.backend.sql_executor import SQLExecutor
from app.backend.sql_validator import validate_sql


# Explicit physical-table allowlist for the Olist dataset.
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
    """Generated SQL failed validation."""


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
    """Orchestrate SQL generation, validation and execution."""

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

        # Prevent different validation policies between
        # the service and its executor.
        if frozenset(self.executor.allowed_tables) != self.allowed_tables:
            raise ValueError(
                "Service and executor table allowlists must match."
            )

    def run(self, question: str) -> TextToSQLResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must not be empty.")

        question = question.strip()

        # 1. Generate SQL using Schema RAG and Ollama.
        try:
            generation = self.generator.generate(question)
        except Exception as exc:
            raise SQLGenerationPipelineError(
                "SQL generation failed."
            ) from exc

        sql = generation.sql.strip()

        # 2. Handle explicit model abstention.
        if sql.upper() == "INSUFFICIENT_CONTEXT":
            raise InsufficientContextError(
                "Insufficient schema or business context."
            )

        # 3. Validate SQL before database access.
        try:
            validation = validate_sql(
                sql,
                allowed_tables=set(self.allowed_tables),
            )
        except Exception as exc:
            raise SQLValidationPipelineError(
                "Generated SQL did not pass validation."
            ) from exc

        # 4. Execute using the restricted database role.
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
