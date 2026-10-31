
from dataclasses import dataclass
from typing import Any

from app.backend.llm_client import OllamaClient
from app.backend.sql_prompt_builder import build_sql_messages
from scripts.search_schema import search_schema


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
            raise ValueError("top_k must be at least 1.")

        self.llm_client = (
            llm_client if llm_client is not None else OllamaClient()
        )
        self.top_k = top_k

    def generate(self, question: str) -> SQLGenerationResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must not be empty.")

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

        sql = response.content.strip()

        if not sql:
            raise ValueError("LLM returned an empty SQL response.")

        return SQLGenerationResult(
            question=question,
            sql=sql,
            model=response.model,
            selected_chunk_ids=[
                chunk["chunk_id"] for chunk in selected_results
            ],
            dependency_chunk_ids=[
                chunk["chunk_id"] for chunk in dependency_results
            ],
        )
