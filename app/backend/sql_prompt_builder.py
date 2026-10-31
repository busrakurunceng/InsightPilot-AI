
import json


SYSTEM_PROMPT = """
You are a PostgreSQL SQL generation assistant.

Your task is to generate SQL using the supplied database
schema and business semantics.

Rules:
- Use only tables and columns explicitly provided in the context.
- Respect metric definitions and business rules.
- Do not invent database objects.
- Do not generate INSERT, UPDATE, DELETE, DROP, ALTER,
  CREATE, TRUNCATE, or other data-modifying statements.
- Generate one read-only SELECT query.
- Do not execute SQL.
- If the context is insufficient, return exactly:
  INSUFFICIENT_CONTEXT
- Return SQL only, without Markdown code fences.
""".strip()


def build_sql_messages(question, selected_results, dependency_results):
    """Prepare Ollama messages from the existing Schema RAG output."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty.")

    context = []
    seen_ids = set()

    for chunk in selected_results + dependency_results:
        chunk_id = chunk["chunk_id"]

        if chunk_id in seen_ids:
            continue

        seen_ids.add(chunk_id)

        context.append({
            "chunk_id": chunk_id,
            "chunk_type": chunk["chunk_type"],
            "content": chunk["content"],
            "metadata": chunk.get("metadata", {}),
        })

    if not context:
        raise ValueError("Schema context must not be empty.")

    user_content = (
        f"Business question:\n{question.strip()}\n\n"
        "Database schema and business context:\n"
        f"{json.dumps(context, ensure_ascii=False, default=str)}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
