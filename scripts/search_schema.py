
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.backend.context_selector import select_context
from app.backend.schema_dependencies import (
    load_semantics,
    metric_dependencies,
)
from app.backend.schema_relevance import (
    rule_dependencies,
    select_primary_metric,
    select_relevant_rule,
)


load_dotenv(PROJECT_ROOT / ".env")

MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


def search_schema(question: str, top_k: int = 5):
    if not question.strip():
        raise ValueError("Soru boş olamaz.")

    if top_k < 1:
        raise ValueError("top_k en az 1 olmalıdır.")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL bulunamadı.")

    model = SentenceTransformer(MODEL_NAME)

    query_embedding = model.encode(
        question,
        normalize_embeddings=True,
    )

    vector_string = "[" + ",".join(
        str(float(value))
        for value in query_embedding
    ) + "]"

    engine = create_engine(database_url)

    sql = text("""
        SELECT
            chunk_id,
            chunk_type,
            content,
            metadata,
            1 - (
                embedding <=> CAST(:query_vector AS vector)
            ) AS similarity
        FROM public.schema_embeddings
        ORDER BY
            embedding <=> CAST(:query_vector AS vector),
            chunk_id
        LIMIT :top_k
    """)

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                sql,
                {
                    "query_vector": vector_string,
                    "top_k": top_k,
                },
            ).mappings().all()

        return enrich_context(
            rows,
            engine,
            question=question,
        )

    finally:
        engine.dispose()


def enrich_context(results, engine, question=None):
    """
    Semantic sonuçları seçer ve gerekli bağımlılıkları ekler.

    question=None:
        Eski davranış korunur.

    question verildiğinde:
        1. Context selection
        2. Metric/rule dependency enrichment
    """
    semantics = load_semantics()

    raw_results = [
        dict(row)
        for row in results
    ]

    if question is None:
        semantic_results = raw_results

        selected_metrics = [
            row["chunk_id"]
            for row in semantic_results
            if row["chunk_type"] == "metric"
        ]

        selected_rule = None

    else:
        semantic_results = select_context(
            question,
            raw_results,
        )

        primary_metric = select_primary_metric(
            question,
            raw_results,
        )

        selected_metrics = (
            [primary_metric]
            if primary_metric is not None
            and any(
                row["chunk_id"] == primary_metric
                for row in semantic_results
            )
            else []
        )

        selected_rule = select_relevant_rule(
            question,
            raw_results,
        )

        if selected_rule is not None and any(
            row["chunk_id"] == selected_rule
            for row in semantic_results
        ):
            # İlişki sorularında rule selection öncelikli.
            selected_metrics = []
        else:
            selected_rule = None

    existing_ids = {
        row["chunk_id"]
        for row in semantic_results
    }

    dependency_ids = []
    seen_dependencies = set()

    def add_dependency(chunk_id):
        if chunk_id in existing_ids:
            return

        if chunk_id in seen_dependencies:
            return

        seen_dependencies.add(chunk_id)
        dependency_ids.append(chunk_id)

    for metric_id in selected_metrics:
        metric_name = metric_id.removeprefix("metric:")

        dependencies = metric_dependencies(
            metric_name,
            semantics,
        )

        for chunk_id in dependencies:
            add_dependency(chunk_id)

    if selected_rule is not None:
        for chunk_id in rule_dependencies(selected_rule):
            add_dependency(chunk_id)

    if not dependency_ids:
        return semantic_results, []

    query = text("""
        SELECT
            chunk_id,
            chunk_type,
            content,
            metadata
        FROM public.schema_embeddings
        WHERE chunk_id = ANY(:chunk_ids)
    """)

    with engine.connect() as connection:
        rows = connection.execute(
            query,
            {"chunk_ids": dependency_ids},
        ).mappings().all()

    rows_by_id = {
        row["chunk_id"]: dict(row)
        for row in rows
    }

    missing_ids = [
        chunk_id
        for chunk_id in dependency_ids
        if chunk_id not in rows_by_id
    ]

    if missing_ids:
        raise ValueError(
            "PostgreSQL'de bağımlılık chunk'ları bulunamadı: "
            f"{missing_ids}"
        )

    dependency_results = [
        rows_by_id[chunk_id]
        for chunk_id in dependency_ids
    ]

    return semantic_results, dependency_results


def main():
    if len(sys.argv) < 2:
        print(
            'Kullanım: python scripts/search_schema.py "Sorunuz"'
        )
        return

    question = " ".join(sys.argv[1:])

    print(f"\nSoru: {question}")
    print("-" * 60)

    semantic_results, dependency_results = search_schema(
        question
    )

    print("\n=== SELECTED SEMANTIC CONTEXT ===")

    if not semantic_results:
        print("Semantic context bulunamadı.")

    for index, result in enumerate(
        semantic_results,
        start=1,
    ):
        print(
            f"{index}. {result['chunk_id']} "
            f"(similarity={result['similarity']:.4f})"
        )

    print("\n=== DEPENDENCY ENRICHMENT ===")

    if not dependency_results:
        print("Ek bağımlılık bulunmadı.")

    for index, result in enumerate(
        dependency_results,
        start=1,
    ):
        print(f"{index}. {result['chunk_id']}")

    unique_ids = {
        result["chunk_id"]
        for result in (
            semantic_results + dependency_results
        )
    }

    print("\n=== SUMMARY ===")
    print(f"Selected semantic chunks: {len(semantic_results)}")
    print(f"Dependency chunks: {len(dependency_results)}")
    print(f"Total unique chunks: {len(unique_ids)}")


if __name__ == "__main__":
    main()
