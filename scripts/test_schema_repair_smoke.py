
"""
Real PostgreSQL smoke test for Safe SQL Schema Repair.

The SQL generator is mocked, but schema validation
and SQL execution use the real read-only PostgreSQL role.

Run:
    python -m scripts.test_schema_repair_smoke
"""

from unittest.mock import Mock

from app.backend.sql_executor import (
    SQLExecutor,
    get_readonly_engine,
)
from app.backend.sql_generator import (
    SQLGenerationResult,
)
from app.backend.text_to_sql_service import (
    SQLValidationPipelineError,
    TextToSQLService,
)


QUESTION = "Müşterilerin eyaletlerini listele"

INVALID_SQL = (
    "SELECT customers.state "
    "FROM customers"
)

VALID_SQL = (
    "SELECT DISTINCT customers.customer_state "
    "FROM customers"
)


def make_generation(sql: str) -> SQLGenerationResult:
    return SQLGenerationResult(
        question=QUESTION,
        sql=sql,
        model="mock-schema-repair",
        selected_chunk_ids=["customers"],
        dependency_chunk_ids=[],
        messages=[
            {
                "role": "system",
                "content": (
                    "Table customers contains "
                    "customer_state."
                ),
            },
            {
                "role": "user",
                "content": QUESTION,
            },
        ],
    )


def main():
    engine = get_readonly_engine()

    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")

        print("[PASS] PostgreSQL connection")

        executor = SQLExecutor(
            engine=engine,
            allowed_tables={"customers"},
            max_rows=10,
            timeout_ms=5000,
        )

        generator = Mock()
        generator.generate.return_value = (
            make_generation(INVALID_SQL)
        )
        generator.regenerate.return_value = (
            make_generation(VALID_SQL)
        )

        service = TextToSQLService(
            generator=generator,
            executor=executor,
            allowed_tables={"customers"},
        )

        print("\n[1] Testing invalid column reference")

        try:
            service._validate_database_schema(
                INVALID_SQL
            )
        except SQLValidationPipelineError:
            print(
                "[PASS] PostgreSQL rejected "
                "customers.state"
            )
        else:
            raise AssertionError(
                "Invalid SQL unexpectedly passed "
                "PostgreSQL schema validation."
            )

        print("\n[2] Testing Safe SQL Repair")

        result = service.run(QUESTION)

        assert result.sql == VALID_SQL, (
            "Unexpected final SQL."
        )

        assert generator.generate.call_count == 1, (
            "Expected exactly one initial generation."
        )

        assert generator.regenerate.call_count == 1, (
            "Expected exactly one repair attempt."
        )

        retry_kwargs = (
            generator.regenerate.call_args.kwargs
        )

        assert retry_kwargs.get(
            "validation_type"
        ) == "schema", (
            "Expected schema repair."
        )

        assert result.row_count > 0, (
            "Expected at least one database row."
        )

        assert "customer_state" in result.columns, (
            "Expected customer_state column."
        )

        print("[PASS] Exactly one schema repair")
        print("[PASS] Repaired SQL passed validation")
        print("[PASS] Repaired SQL executed successfully")

        print("\nFinal SQL:")
        print(result.sql)

        print("\nReturned rows:")
        for row in result.rows:
            print(row)

        print("\n[SUCCESS] Real PostgreSQL smoke test passed")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
