
import re
from dataclasses import dataclass, field

from app.backend.llm_client import OllamaClient
from app.backend.sql_prompt_builder import build_sql_messages
from scripts.search_schema import search_schema


OPENING_FENCE_PATTERN = re.compile(
    r"```(?:sql|postgresql)?",
    flags=re.IGNORECASE,
)


def normalize_sql_response(response: str) -> str:
    """
    Remove Markdown formatting only when the response
    contains exactly one complete SQL code block.

    Multiple, nested, or malformed code blocks are
    preserved for rejection by the SQL validator.
    """
    if not isinstance(response, str):
        raise TypeError("SQL response must be a string.")

    cleaned = response.strip()
    lines = cleaned.splitlines()

    if len(lines) < 3:
        return cleaned

    opening_line = lines[0].strip()
    closing_line = lines[-1].strip()

    if OPENING_FENCE_PATTERN.fullmatch(
        opening_line
    ) is None:
        return cleaned

    if closing_line != "```":
        return cleaned

    content_lines = lines[1:-1]

    if any("```" in line for line in content_lines):
        return cleaned

    return "\n".join(content_lines).strip()


@dataclass(frozen=True)
class SQLGenerationResult:
    question: str
    sql: str
    model: str
    selected_chunk_ids: list[str]
    dependency_chunk_ids: list[str]
    messages: list[dict[str, str]] = field(
        default_factory=list,
        repr=False,
        compare=False,
    )


class SQLGenerator:
    """Generate PostgreSQL SQL using Schema RAG and Ollama."""

    def __init__(
        self,
        llm_client: OllamaClient | None = None,
        top_k: int = 5,
    ):
        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1."
            )

        self.llm_client = (
            llm_client
            if llm_client is not None
            else OllamaClient()
        )

        self.top_k = top_k

    def generate(
        self,
        question: str,
    ) -> SQLGenerationResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                "Question must not be empty."
            )

        question = question.strip()

        selected_results, dependency_results = search_schema(
            question,
            top_k=self.top_k,
        )

        messages = build_sql_messages(
            question,
            selected_results,
            dependency_results,
        )

        response = self.llm_client.chat(
            messages,
            temperature=0.0,
        )

        sql = normalize_sql_response(
            response.content
        )

        if not sql:
            raise ValueError(
                "LLM returned an empty SQL response."
            )

        return SQLGenerationResult(
            question=question,
            sql=sql,
            model=response.model,
            selected_chunk_ids=[
                chunk["chunk_id"]
                for chunk in selected_results
            ],
            dependency_chunk_ids=[
                chunk["chunk_id"]
                for chunk in dependency_results
            ],
            messages=[
                dict(message)
                for message in messages
            ],
        )


    def regenerate(
        self,
        previous: SQLGenerationResult,
        issues: list[str],
        *,
        validation_type: str = "semantic",
    ) -> SQLGenerationResult:
        """
        Regenerate SQL using the original Schema RAG context.

        Supported validation types:
        - semantic: repair grouping/dimension errors
        - schema: repair invalid database references

        No additional Schema RAG retrieval is performed.
        """
        if not isinstance(previous, SQLGenerationResult):
            raise TypeError(
                "Previous generation must be SQLGenerationResult."
            )

        if not previous.messages:
            raise ValueError(
                "Original SQL prompt context is unavailable."
            )

        if (
            not isinstance(issues, list)
            or not issues
            or not all(
                isinstance(issue, str) and issue.strip()
                for issue in issues
            )
        ):
            raise ValueError(
                "Validation issues must be a non-empty list."
            )

        if validation_type not in {"semantic", "schema"}:
            raise ValueError(
                "Unsupported validation type."
            )

        feedback = "\n".join(
            f"- {issue.strip()}"
            for issue in issues
        )

        messages = [
            dict(message)
            for message in previous.messages
        ]

        messages.append({
            "role": "assistant",
            "content": previous.sql,
        })

        if validation_type == "semantic":
            repair_instructions = (
                "The previous SQL failed semantic validation.\n"
                "Correct the SQL using ONLY the original "
                "schema and business context.\n\n"
                f"Validation issues:\n{feedback}\n\n"
                "Requirements:\n"
                "- Preserve the user's original measure.\n"
                "- Include the required grouping dimension "
                "in SELECT and GROUP BY.\n"
                "- Use documented relationships for JOINs.\n"
                "- Do not introduce unrequested filters.\n"
            )
        else:
            repair_instructions = (
                "The previous SQL failed PostgreSQL schema "
                "validation.\n"
                "Correct invalid table names, column names, "
                "aliases, or relationships using ONLY the "
                "original schema and business context.\n\n"
                f"Validation issues:\n{feedback}\n\n"
                "Requirements:\n"
                "- Use only documented tables and columns.\n"
                "- Do not invent schema objects.\n"
                "- Preserve the user's original measure "
                "and grouping requirements.\n"
                "- Use documented relationships for JOINs.\n"
                "- Do not introduce unrequested filters.\n"
                "- If the original context is insufficient, "
                "return INSUFFICIENT_CONTEXT.\n"
            )

        messages.append({
            "role": "user",
            "content": (
                repair_instructions
                + "- Return exactly one read-only SELECT query.\n"
                + "- Return SQL only, without explanations "
                "or Markdown."
            ),
        })

        response = self.llm_client.chat(
            messages,
            temperature=0.0,
        )

        sql = normalize_sql_response(
            response.content
        )

        if not sql:
            raise ValueError(
                "LLM returned an empty SQL retry response."
            )

        return SQLGenerationResult(
            question=previous.question,
            sql=sql,
            model=response.model,
            selected_chunk_ids=list(
                previous.selected_chunk_ids
            ),
            dependency_chunk_ids=list(
                previous.dependency_chunk_ids
            ),
            messages=[
                dict(message)
                for message in previous.messages
            ],
        )
