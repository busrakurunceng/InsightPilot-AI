
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
from app.backend.sql_schema_validator import (
    SQLSchemaValidationError,
    validate_sql_schema,
)


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


class SQLSemanticValidationPipelineError(
    SQLValidationPipelineError
):
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
    """
    Orchestrate SQL generation, validation, repair and execution.

    At most one SQL regeneration is permitted per request.

    Security failures are never repaired.
    Every regenerated SQL query is fully revalidated.
    """

    MAX_RETRIES = 1

    SCHEMA_REPAIR_FEEDBACK = (
        "PostgreSQL could not validate the previous SQL "
        "against the database schema. "
        "Check table names, column names, aliases, "
        "JOIN conditions, and GROUP BY references "
        "using only the original documented schema."
    )

    def __init__(
        self,
        generator: SQLGenerator | None = None,
        executor: SQLExecutor | None = None,
        allowed_tables: set[str] | frozenset[str] = (
            OLIST_ALLOWED_TABLES
        ),
    ):
        if not allowed_tables:
            raise ValueError(
                "Table allowlist must not be empty."
            )

        self.allowed_tables = frozenset(
            allowed_tables
        )

        self.generator = (
            generator
            if generator is not None
            else SQLGenerator()
        )

        self.executor = (
            executor
            if executor is not None
            else SQLExecutor(
                allowed_tables=set(
                    self.allowed_tables
                )
            )
        )

        if (
            frozenset(self.executor.allowed_tables)
            != self.allowed_tables
        ):
            raise ValueError(
                "Service and executor table allowlists "
                "must match."
            )

    def _validate_security(self, sql: str):
        """
        Validate SQL structure, read-only requirements,
        and the table allowlist.
        """
        try:
            return validate_sql(
                sql,
                allowed_tables=set(
                    self.allowed_tables
                ),
            )
        except Exception as exc:
            raise SQLValidationPipelineError(
                "Generated SQL did not pass "
                "security validation."
            ) from exc

    def _validate_semantics(
        self,
        sql: str,
        required_dimension: str | None,
    ) -> list[str]:
        """
        Check required grouping dimensions.
        """
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

    def _validate_database_schema(
        self,
        sql: str,
    ) -> None:
        """
        Validate SQL against the actual PostgreSQL schema.

        SQLSchemaValidationError is converted to a
        pipeline error. Unexpected database errors
        are not treated as repairable schema errors.
        """
        try:
            validate_sql_schema(
                sql,
                engine=self.executor.engine,
                allowed_tables=self.allowed_tables,
                timeout_ms=self.executor.timeout_ms,
            )
        except SQLSchemaValidationError as exc:
            raise SQLValidationPipelineError(
                "Generated SQL references an invalid "
                "database object or cannot be planned."
            ) from exc

    def _regenerate(
        self,
        generation,
        issues: list[str],
        validation_type: str,
    ):
        """
        Request one controlled SQL regeneration.

        Retry budgeting is managed by run().
        """
        try:
            if validation_type == "semantic":
                # Preserve compatibility with the
                # existing semantic retry interface.
                return self.generator.regenerate(
                    generation,
                    issues=issues,
                )

            if validation_type == "schema":
                return self.generator.regenerate(
                    generation,
                    issues=issues,
                    validation_type="schema",
                )

            raise ValueError(
                "Unsupported validation type."
            )

        except Exception as exc:
            raise SQLGenerationPipelineError(
                "SQL regeneration failed."
            ) from exc

    @staticmethod
    def _check_insufficient_context(
        sql: str,
        *,
        after_retry: bool = False,
    ) -> None:
        """
        Reject the model's insufficient-context marker.
        """
        if sql.strip().upper() != "INSUFFICIENT_CONTEXT":
            return

        if after_retry:
            raise InsufficientContextError(
                "Insufficient context after "
                "SQL regeneration."
            )

        raise InsufficientContextError(
            "Insufficient schema or business context."
        )

    def run(
        self,
        question: str,
    ) -> TextToSQLResult:
        """
        Generate, validate, optionally repair,
        and execute a read-only SQL query.

        Pipeline:
        1. Generate SQL.
        2. Validate security.
        3. Validate semantics.
        4. Optionally repair semantic errors.
        5. Validate PostgreSQL schema.
        6. Optionally repair schema errors.
        7. Revalidate repaired SQL.
        8. Execute fully validated SQL.

        Maximum regeneration count: 1.
        """
        if (
            not isinstance(question, str)
            or not question.strip()
        ):
            raise ValueError(
                "Question must not be empty."
            )

        question = question.strip()

        retry_count = 0

        # -----------------------------------------
        # 1. Initial SQL generation
        # -----------------------------------------
        try:
            generation = self.generator.generate(
                question
            )
        except Exception as exc:
            raise SQLGenerationPipelineError(
                "SQL generation failed."
            ) from exc

        sql = generation.sql.strip()

        self._check_insufficient_context(sql)

        # -----------------------------------------
        # 2. Security validation
        # -----------------------------------------
        # Unsafe SQL must never be repaired.
        validation = self._validate_security(
            sql
        )

        # -----------------------------------------
        # 3. Determine required dimension
        # -----------------------------------------
        try:
            required_dimension = (
                infer_question_dimension(
                    question
                )
            )
        except Exception as exc:
            raise SQLSemanticValidationPipelineError(
                "Could not determine semantic "
                "grouping requirements."
            ) from exc

        # -----------------------------------------
        # 4. Semantic validation
        # -----------------------------------------
        issues = self._validate_semantics(
            validation.sql,
            required_dimension,
        )

        # -----------------------------------------
        # 5. Optional semantic repair
        # -----------------------------------------
        if issues:
            if retry_count >= self.MAX_RETRIES:
                raise SQLSemanticValidationPipelineError(
                    "SQL retry limit exceeded."
                )

            generation = self._regenerate(
                generation,
                issues=issues,
                validation_type="semantic",
            )

            retry_count += 1

            retry_sql = generation.sql.strip()

            self._check_insufficient_context(
                retry_sql,
                after_retry=True,
            )

            # Every retry must pass security.
            validation = self._validate_security(
                retry_sql
            )

            retry_issues = (
                self._validate_semantics(
                    validation.sql,
                    required_dimension,
                )
            )

            if retry_issues:
                raise SQLSemanticValidationPipelineError(
                    "SQL regeneration did not satisfy "
                    "the required dimension "
                    f"({required_dimension}): "
                    + "; ".join(retry_issues)
                )

        # -----------------------------------------
        # 6. PostgreSQL schema validation
        # -----------------------------------------
        try:
            self._validate_database_schema(
                validation.sql
            )

        except SQLValidationPipelineError:
            # A previous semantic retry already used
            # the only permitted regeneration.
            if retry_count >= self.MAX_RETRIES:
                raise

            # -------------------------------------
            # 7. Optional schema repair
            # -------------------------------------
            generation = self._regenerate(
                generation,
                issues=[
                    self.SCHEMA_REPAIR_FEEDBACK
                ],
                validation_type="schema",
            )

            retry_count += 1

            retry_sql = generation.sql.strip()

            self._check_insufficient_context(
                retry_sql,
                after_retry=True,
            )

            # -------------------------------------
            # 8. Full validation of repaired SQL
            # -------------------------------------

            # 8a. Security
            validation = self._validate_security(
                retry_sql
            )

            # 8b. Semantics
            retry_issues = (
                self._validate_semantics(
                    validation.sql,
                    required_dimension,
                )
            )

            if retry_issues:
                raise SQLSemanticValidationPipelineError(
                    "Schema-repaired SQL did not "
                    "satisfy the required dimension "
                    f"({required_dimension}): "
                    + "; ".join(retry_issues)
                )

            # 8c. Actual PostgreSQL schema
            self._validate_database_schema(
                validation.sql
            )

        # -----------------------------------------
        # 9. Execute fully validated SQL
        # -----------------------------------------
        try:
            execution = self.executor.execute(
                validation.sql
            )
        except Exception as exc:
            raise SQLExecutionPipelineError(
                "Validated SQL execution failed."
            ) from exc

        # -----------------------------------------
        # 10. Return final result
        # -----------------------------------------
        return TextToSQLResult(
            question=question,
            sql=validation.sql,
            model=generation.model,
            columns=execution.columns,
            rows=execution.rows,
            row_count=execution.row_count,
            truncated=execution.truncated,
            selected_chunk_ids=(
                generation.selected_chunk_ids
            ),
            dependency_chunk_ids=(
                generation.dependency_chunk_ids
            ),
        )
