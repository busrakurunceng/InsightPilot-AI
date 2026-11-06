
import json

from app.backend.schema_dependencies import load_semantics


SYSTEM_PROMPT = """
You are a PostgreSQL SQL generation assistant.

Generate one read-only SQL SELECT query that answers
the user's business question.

SCHEMA GROUNDING:
- Use only tables and columns explicitly supplied in context.
- Respect supplied business metrics and business semantics.
- Do not invent tables, columns, or relationships.
- Do not introduce filters that the question does not request.
- Use exact database values when supplied in business semantics.

QUESTION INTERPRETATION:
- Identify the requested measure, filters, dimensions,
  and aggregation before writing SQL.
- If the user asks for a breakdown "by" a dimension,
  include the dimension in SELECT and GROUP BY.
- If a requested dimension belongs to another table,
  use a documented relationship to join the tables.
- Preserve the grain of the requested measure.
- Do not replace a grouped result with a single total.
- Avoid unnecessary joins that could duplicate rows.

ORDER STATUS:
- When filtering by order status, use the documented
  status column and exact status values.
- Do not assume that a non-null delivery timestamp
  is equivalent to a delivered order status.
- Do not translate database enum values into English
  variants with different spelling or capitalization.

SAFETY:
- Generate exactly one read-only SELECT statement.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER,
  CREATE, TRUNCATE, or other data-modifying statements.
- Do not execute SQL.
- If the supplied context is insufficient, return exactly:
  INSUFFICIENT_CONTEXT
- Return SQL only, without Markdown code fences.
""".strip()


def build_business_context(context, semantics):
    """
    Include only business definitions relevant to tables
    already present in the selected schema context.

    This does not authorize use of additional tables
    or columns outside the retrieved schema chunks.
    """
    table_names = {
        chunk["chunk_id"].removeprefix("table:")
        for chunk in context
        if chunk["chunk_type"] == "table"
    }

    table_definitions = {}

    for table_name in sorted(table_names):
        definition = semantics.get("tables", {}).get(
            table_name
        )

        if definition is not None:
            table_definitions[table_name] = definition

    relationships = []

    for relationship in semantics.get(
        "logical_relationships", []
    ):
        left = relationship.get("left", "")
        right = relationship.get("right", "")

        left_table = left.split(".", 1)[0]
        right_table = right.split(".", 1)[0]

        if (
            left_table in table_names
            and right_table in table_names
        ):
            relationships.append(relationship)

    return {
        "tables": table_definitions,
        "logical_relationships": relationships,
    }


def build_sql_messages(
    question,
    selected_results,
    dependency_results,
):
    """
    Build Ollama messages using Schema RAG and
    relevant YAML business semantics.
    """
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

    semantics = load_semantics()

    business_context = build_business_context(
        context,
        semantics,
    )

    user_content = (
        f"Business question:\n{question.strip()}\n\n"
        "Database schema and retrieved context:\n"
        f"{json.dumps(context, ensure_ascii=False, default=str)}"
        "\n\nRelevant business semantics:\n"
        f"{json.dumps(business_context, ensure_ascii=False)}"
    )

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]
