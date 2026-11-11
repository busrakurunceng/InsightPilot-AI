
"""
Smoke test for Schema RAG embedding model caching.

Run:
    python -m scripts.test_schema_cache_smoke
"""

import time

from scripts.search_schema import (
    get_embedding_model,
    search_schema,
)


QUESTION = "Her eyaletteki müşteri sayısı nedir?"


def chunk_ids(chunks):
    return [chunk["chunk_id"] for chunk in chunks]


def run_search(label):
    start = time.perf_counter()

    selected, dependencies = search_schema(
        QUESTION,
        top_k=5,
    )

    elapsed = time.perf_counter() - start

    print(
        f"{label}: {elapsed:.3f} s; "
        f"selected={len(selected)}; "
        f"dependencies={len(dependencies)}"
    )

    return selected, dependencies, elapsed


def main():
    get_embedding_model.cache_clear()

    print("\nSchema RAG cache smoke test")
    print(f"Question: {QUESTION}\n")

    first_selected, first_dependencies, first_time = (
        run_search("First search (cold)")
    )

    second_selected, second_dependencies, second_time = (
        run_search("Second search (warm)")
    )

    cache = get_embedding_model.cache_info()

    print(
        f"\nCache: hits={cache.hits}, "
        f"misses={cache.misses}"
    )

    print(
        f"Time saved: "
        f"{first_time - second_time:.3f} s"
    )

    assert cache.misses == 1, (
        "Embedding model should load exactly once."
    )

    assert cache.hits >= 1, (
        "Second search should reuse the embedding model."
    )

    assert chunk_ids(first_selected) == chunk_ids(
        second_selected
    ), "Selected schema chunks changed."

    assert chunk_ids(first_dependencies) == chunk_ids(
        second_dependencies
    ), "Dependency schema chunks changed."

    print(
        "\n[PASS] Same-process model cache "
        "and retrieval results"
    )


if __name__ == "__main__":
    main()
