
from app.backend.schema_relevance import (
    select_primary_metric,
    select_relevant_rule,
)


def select_context(question: str, semantic_results):
    """
    Semantic search sonuçlarından soruyla doğrudan
    ilgili olan chunk'ları seçer.

    Senaryolar:
    1. Metric intent -> primary metric
    2. Relationship intent -> relevant rule
    3. Unknown intent -> semantic fallback

    Dependency enrichment bu fonksiyonun dışında yapılır.
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

    # İlişki sorularına öncelik veriyoruz.
    if relevant_rule is not None:
        selected_ids = {relevant_rule}

    elif primary_metric is not None:
        selected_ids = {primary_metric}

    else:
        # Bilinmeyen intent: bilgi kaybını önlemek için
        # semantic sonuçları değiştirmiyoruz.
        return results

    return [
        result
        for result in results
        if result["chunk_id"] in selected_ids
    ]
