"""Upload validated schema embeddings to PostgreSQL pgvector.

Run: python scripts/upload_embeddings.py
Requires DATABASE_URL in .env (or the process environment).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]


def prepare_rows(chunks: list[dict], vectors: np.ndarray, metadata: dict) -> list[dict]:
    if vectors.ndim != 2 or vectors.shape[1] != 384 or len(vectors) != len(chunks):
        raise ValueError("Expected one 384-dimensional embedding per chunk")
    if not np.isfinite(vectors).all():
        raise ValueError("Embeddings contain NaN or infinity")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4):
        raise ValueError("Embeddings must be normalized")
    ids = [c["id"] for c in chunks]
    if len(ids) != len(set(ids)) or not all(isinstance(i, str) and i for i in ids):
        raise ValueError("Chunk IDs must be nonempty and unique")
    if metadata.get("chunk_ids") != ids or metadata.get("dimensions") != 384:
        raise ValueError("Embedding metadata does not match chunk IDs/order or dimensions; rebuild embeddings")
    rows = []
    for chunk, vector in zip(chunks, vectors):
        if not isinstance(chunk.get("text"), str) or not chunk["text"].strip():
            raise ValueError("Chunk text must be nonempty")
        if not isinstance(chunk.get("kind"), str) or not chunk["kind"].strip():
            raise ValueError("Chunk kind must be nonempty")
        rows.append({
            "chunk_id": chunk["id"],
            "chunk_type": chunk["kind"],
            "content": chunk["text"],
            "metadata": json.dumps({**{k: v for k, v in chunk.items() if k != "text"}, "model": metadata.get("model")}, ensure_ascii=False),
            "embedding": "[" + ",".join(format(float(v), ".9g") for v in vector) + "]",
        })
    return rows


def main() -> None:
    load_dotenv(ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL missing. Add it to .env (do not commit .env).")
    folder = ROOT / "artifacts"
    chunks = json.loads((folder / "schema_chunks.json").read_text(encoding="utf-8"))
    metadata = json.loads((folder / "schema_embeddings_metadata.json").read_text(encoding="utf-8"))
    vectors = np.load(folder / "schema_embeddings.npy", allow_pickle=False)
    rows = prepare_rows(chunks, vectors, metadata)
    engine = create_engine(url)
    with engine.begin() as connection:
        available = connection.execute(text("SELECT to_regclass('public.schema_embeddings')")).scalar_one()
        if available is None:
            raise RuntimeError("public.schema_embeddings not found; create it in pgAdmin first")
        for row in rows:
            connection.execute(text("""
                INSERT INTO public.schema_embeddings
                    (chunk_id, chunk_type, content, metadata, embedding)
                VALUES (:chunk_id, :chunk_type, :content,
                        CAST(:metadata AS jsonb), CAST(:embedding AS vector))
                ON CONFLICT (chunk_id) DO UPDATE SET
                    chunk_type = EXCLUDED.chunk_type,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    embedding = EXCLUDED.embedding
            """), row)
        total = connection.execute(text("SELECT count(*) FROM public.schema_embeddings")).scalar_one()
    print(f"Uploaded/updated: {len(rows)} chunks")
    print(f"Total rows in schema_embeddings: {total}")
    if total != len(rows):
        print("Note: table also contains other rows; UPSERT does not delete obsolete chunks.")


if __name__ == "__main__":
    main()
