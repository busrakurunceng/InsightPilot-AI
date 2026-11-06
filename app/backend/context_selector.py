
from app.backend.question_table_relevance import infer_question_tables
from app.backend.schema_relevance import (
    select_primary_metric,
    select_relevant_rule,
)


def select_context(question: str, semantic_results):
    """
    Select question-relevant chunks from semantic search results.

    Priority:
        1. Explicit relationship rule
        2. Primary business metric
        3. Explicit question-relevant tables
        4. Semantic fallback

    Table dependencies that are missing from raw retrieval
    are loaded separately by enrich_context().
    """
    results = [
        dict(result)
        for result in semantic_results
    ]

    if not results:
        return []

    primary_metric = select_primary_metric(
        question,
        results,
    )

    relevant_rule = select_relevant_rule(
        question,
        results,
    )

    # 1. Explicit relationship intent
    if relevant_rule is not None:
        selected_ids = {relevant_rule}

    # 2. Explicit business metric intent
    elif primary_metric is not None:
        selected_ids = {primary_metric}

    # 3. Explicit table intent
    else:
        question_tables = infer_question_tables(question)

        if not question_tables:
            # Unknown intent: preserve semantic retrieval.
            return results

        selected_ids = {
            f"table:{table_name}"
            for table_name in question_tables
        }

    # Preserve retrieval order and avoid modifying source rows.
    return [
        result
        for result in results
        if result["chunk_id"] in selected_ids
    ]
