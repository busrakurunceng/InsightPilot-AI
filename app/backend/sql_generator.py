
import re
from dataclasses import dataclass

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

    # The response must start with a recognized fence.
    if OPENING_FENCE_PATTERN.fullmatch(
        opening_line
    ) is None:
        return cleaned

    # The response must end with one closing fence.
    if closing_line != "```":
        return cleaned

    content_lines = lines[1:-1]

    # Any additional fence means the response is
    # ambiguous or contains multiple code blocks.
    if any("```" in line for line in content_lines):
        return cleaned

    sql = "\n".join(content_lines).strip()

    return sql


@dataclass(frozen=True)
class SQLGenerationResult:
    question: str
    sql: str
    model: str
    selected_chunk_ids: list[str]
    dependency_chunk_ids: list[str]


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
        )
