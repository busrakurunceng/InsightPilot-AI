
"""
InsightPilot-AI Text-to-SQL performance and retry profiler.

Run:
    python -m scripts.profile_text_to_sql

Uses real Ollama and PostgreSQL.
Does not modify application source files.
"""

import time
from contextlib import contextmanager
from unittest.mock import patch

from app.backend import sql_generator as generator_module
from app.backend import text_to_sql_service as service_module
from app.backend.llm_client import OllamaClient
from app.backend.sql_executor import SQLExecutor
from app.backend.sql_generator import SQLGenerator
from app.backend.text_to_sql_service import (
    OLIST_ALLOWED_TABLES,
    TextToSQLService,
)


QUESTION = "Her eyaletteki müşteri sayısı nedir?"

timings = {}
ollama_details = []
retry_details = []
generation_details = []


@contextmanager
def measure(name):
    start = time.perf_counter()

    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        timings.setdefault(name, []).append(elapsed)


def wrap_function(original, name):
    def wrapped(*args, **kwargs):
        with measure(name):
            return original(*args, **kwargs)

    return wrapped


def seconds_from_ns(value):
    if value is None:
        return None

    return value / 1_000_000_000


def format_seconds(value):
    if value is None:
        return "N/A"

    return f"{value:.3f} s"


def main():
    timings.clear()
    ollama_details.clear()
    retry_details.clear()
    generation_details.clear()

    original_search = generator_module.search_schema
    original_prompt = generator_module.build_sql_messages
    original_chat = OllamaClient.chat

    original_security = service_module.validate_sql
    original_semantics = (
        service_module.validate_grouping_requirement
    )
    original_schema = service_module.validate_sql_schema
    original_execute = SQLExecutor.execute

    original_generate = SQLGenerator.generate
    original_regenerate = SQLGenerator.regenerate

    def timed_chat(self, *args, **kwargs):
        with measure("Ollama HTTP"):
            response = original_chat(
                self, *args, **kwargs
            )

        ollama_details.append({
            "model": response.model,
            "total_duration": seconds_from_ns(
                response.total_duration_ns
            ),
            "load_duration": seconds_from_ns(
                response.load_duration_ns
            ),
            "prompt_eval_duration": seconds_from_ns(
                response.prompt_eval_duration_ns
            ),
            "prompt_eval_count": (
                response.prompt_eval_count
            ),
            "eval_duration": seconds_from_ns(
                response.eval_duration_ns
            ),
            "eval_count": response.eval_count,
        })

        return response

    def traced_generate(self, *args, **kwargs):
        with measure("Initial SQL Generation"):
            result = original_generate(
                self, *args, **kwargs
            )

        generation_details.append({
            "type": "initial",
            "sql": result.sql,
        })

        return result

    def traced_regenerate(
        self,
        previous,
        issues,
        *,
        validation_type="semantic",
    ):
        retry_record = {
            "type": validation_type,
            "original_sql": previous.sql,
            "issues": list(issues),
            "repaired_sql": None,
        }

        retry_details.append(retry_record)

        with measure("SQL Regeneration"):
            result = original_regenerate(
                self,
                previous,
                issues=issues,
                validation_type=validation_type,
            )

        retry_record["repaired_sql"] = result.sql

        generation_details.append({
            "type": f"{validation_type}_repair",
            "sql": result.sql,
        })

        return result

    with (
        patch.object(
            generator_module,
            "search_schema",
            wrap_function(
                original_search,
                "Schema RAG",
            ),
        ),
        patch.object(
            generator_module,
            "build_sql_messages",
            wrap_function(
                original_prompt,
                "Prompt Building",
            ),
        ),
        patch.object(
            OllamaClient,
            "chat",
            timed_chat,
        ),
        patch.object(
            SQLGenerator,
            "generate",
            traced_generate,
        ),
        patch.object(
            SQLGenerator,
            "regenerate",
            traced_regenerate,
        ),
        patch.object(
            service_module,
            "validate_sql",
            wrap_function(
                original_security,
                "Security Validation",
            ),
        ),
        patch.object(
            service_module,
            "validate_grouping_requirement",
            wrap_function(
                original_semantics,
                "Semantic Validation",
            ),
        ),
        patch.object(
            service_module,
            "validate_sql_schema",
            wrap_function(
                original_schema,
                "PostgreSQL Schema Validation",
            ),
        ),
        patch.object(
            SQLExecutor,
            "execute",
            wrap_function(
                original_execute,
                "SQL Execution",
            ),
        ),
    ):
        service = TextToSQLService(
            executor=SQLExecutor(
                allowed_tables=set(
                    OLIST_ALLOWED_TABLES
                ),
            ),
        )

        print(f"\nQuestion: {QUESTION}")
        print("Running real Text-to-SQL pipeline...\n")

        start = time.perf_counter()

        try:
            result = service.run(QUESTION)

            print("[SUCCESS] SQL pipeline completed")
            print("\nFinal SQL:")
            print(result.sql)
            print(
                f"\nRows returned: {result.row_count}"
            )

        except Exception as exc:
            print(
                f"[FAILED] {type(exc).__name__}: {exc}"
            )

            if exc.__cause__ is not None:
                print(
                    "Cause:",
                    type(exc.__cause__).__name__,
                    str(exc.__cause__),
                )

        finally:
            timings["TOTAL"] = [
                time.perf_counter() - start
            ]

    print("\n" + "=" * 60)
    print("PERFORMANCE REPORT")
    print("=" * 60)

    for name, values in timings.items():
        print(
            f"{name:32s}"
            f"{sum(values):9.3f} s"
            f"  calls={len(values)}"
        )

    print("\n" + "=" * 60)
    print("SQL GENERATION AND RETRY DIAGNOSTICS")
    print("=" * 60)

    for index, item in enumerate(
        generation_details, start=1
    ):
        print(f"\nGeneration #{index}")
        print("Type:", item["type"])
        print("SQL:")
        print(item["sql"])

    if not retry_details:
        print("\nNo SQL regeneration was required.")

    for index, retry in enumerate(
        retry_details, start=1
    ):
        print(f"\nRetry #{index}")
        print("Validation type:", retry["type"])

        print("\nValidation issues:")
        for issue in retry["issues"]:
            print(f"- {issue}")

        print("\nOriginal SQL:")
        print(retry["original_sql"])

        print("\nRepaired SQL:")
        print(
            retry["repaired_sql"]
            if retry["repaired_sql"] is not None
            else "Repair did not complete."
        )

    print("\n" + "=" * 60)
    print("OLLAMA DETAILED METRICS")
    print("=" * 60)

    for index, detail in enumerate(
        ollama_details, start=1
    ):
        print(f"\nOllama call #{index}")
        print("Model:", detail["model"])

        print(
            "Total duration:",
            format_seconds(
                detail["total_duration"]
            ),
        )

        print(
            "Model load duration:",
            format_seconds(
                detail["load_duration"]
            ),
        )

        print(
            "Prompt evaluation duration:",
            format_seconds(
                detail["prompt_eval_duration"]
            ),
        )

        print(
            "Prompt tokens:",
            detail["prompt_eval_count"],
        )

        print(
            "Token generation duration:",
            format_seconds(
                detail["eval_duration"]
            ),
        )

        print(
            "Generated tokens:",
            detail["eval_count"],
        )

        eval_duration = detail["eval_duration"]
        eval_count = detail["eval_count"]

        if (
            eval_duration is not None
            and eval_duration > 0
            and eval_count is not None
        ):
            tokens_per_second = (
                eval_count / eval_duration
            )

            print(
                "Generation speed:",
                f"{tokens_per_second:.2f} tokens/s",
            )


if __name__ == "__main__":
    main()
