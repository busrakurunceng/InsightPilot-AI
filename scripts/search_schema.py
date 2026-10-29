
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# 1. PROJE AYARLARI
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.backend.schema_dependencies import (
    load_semantics,
    metric_dependencies,
)

load_dotenv(PROJECT_ROOT / ".env")

MODEL_NAME = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


# ============================================================
# 2. SEMANTIC SEARCH
# ============================================================

def search_schema(question: str, top_k: int = 5):
    """
    Kullanıcı sorusuyla en alakalı schema chunk'larını bulur
    ve gerekli metrik/tablo bağımlılıklarıyla zenginleştirir.

    Returns:
        semantic_results: Vektör aramasıyla bulunan kayıtlar
        dependency_results: YAML bağımlılıklarıyla eklenen kayıtlar
    """

    if not question.strip():
        raise ValueError("Soru boş olamaz.")

    if top_k < 1:
        raise ValueError("top_k en az 1 olmalıdır.")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL bulunamadı.")

    # Kullanıcı sorusunu embedding'e dönüştür.
    model = SentenceTransformer(MODEL_NAME)

    query_embedding = model.encode(
        question,
        normalize_embeddings=True,
    )

    # pgvector'ın kabul ettiği vektör biçimi.
    vector_string = "[" + ",".join(
        str(float(value)) for value in query_embedding
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

        return enrich_context(rows, engine)

    finally:
        engine.dispose()


# ============================================================
# 3. DEPENDENCY-AWARE CONTEXT ENRICHMENT
# ============================================================

def enrich_context(results, engine):
    """
    Semantic search sonuçlarında bulunan metriklerin
    bağımlılıklarını business_semantics.yaml üzerinden çözer.

    Eksik chunk'ları PostgreSQL'den getirir.

    Orijinal semantic search sonuçlarını değiştirmez.
    """

    semantics = load_semantics()

    semantic_results = [
        dict(row) for row in results
    ]

    existing_ids = {
        row["chunk_id"]
        for row in semantic_results
    }

    dependency_ids = []
    seen_dependencies = set()

    # Her semantic sonucu incele.
    for result in semantic_results:

        if result["chunk_type"] != "metric":
            continue

        metric_name = result["chunk_id"].removeprefix(
            "metric:"
        )

        dependencies = metric_dependencies(
            metric_name,
            semantics,
        )

        # Zaten bulunan chunk'ları tekrar ekleme.
        for dependency_id in dependencies:

            if dependency_id in existing_ids:
                continue

            if dependency_id in seen_dependencies:
                continue

            seen_dependencies.add(dependency_id)
            dependency_ids.append(dependency_id)

    # Ek bağımlılık yoksa veritabanına tekrar sorgu atma.
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

    # Beklenen bağımlılıkların tamamı mevcut mu?
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

    # Bağımlılıkları belirlediğimiz sırayla döndür.
    dependency_results = [
        rows_by_id[chunk_id]
        for chunk_id in dependency_ids
    ]

    return semantic_results, dependency_results


# ============================================================
# 4. SONUÇLARI EKRANA YAZDIR
# ============================================================

def main():

    if len(sys.argv) < 2:
        print(
            'Kullanım: python scripts/search_schema.py '
            '"Sorunuz"'
        )
        return

    question = " ".join(sys.argv[1:])

    print(f"\nSoru: {question}")
    print("-" * 60)

    semantic_results, dependency_results = search_schema(
        question
    )

    # Semantic search sonuçları
    print("\n=== SEMANTIC SEARCH RESULTS ===")

    if not semantic_results:
        print("Semantic search sonucu bulunamadı.")

    for index, result in enumerate(
        semantic_results,
        start=1,
    ):
        print(
            f"{index}. {result['chunk_id']} "
            f"(similarity={result['similarity']:.4f})"
        )

    # Dependency enrichment sonuçları
    print("\n=== DEPENDENCY ENRICHMENT ===")

    if not dependency_results:
        print("Ek bağımlılık bulunmadı.")

    for index, result in enumerate(
        dependency_results,
        start=1,
    ):
        print(f"{index}. {result['chunk_id']}")

    # Genel özet
    print("\n=== SUMMARY ===")
    print(f"Semantic results: {len(semantic_results)}")
    print(f"Dependency results: {len(dependency_results)}")

    unique_ids = {
        result["chunk_id"]
        for result in semantic_results + dependency_results
    }

    print(f"Total unique chunks: {len(unique_ids)}")


# ============================================================
# 5. PROGRAMIN BAŞLANGIÇ NOKTASI
# ============================================================

if __name__ == "__main__":
    main()
