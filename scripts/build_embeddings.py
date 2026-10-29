"""Generate local multilingual embeddings for schema chunks.

Usage: python scripts/build_embeddings.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_chunks(path: Path) -> list[dict]:
    chunks = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Expected a nonempty JSON list of chunks")
    ids = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, dict) or not isinstance(chunk.get("id"), str) or not isinstance(chunk.get("text"), str):
            raise ValueError(f"Chunk {index} must have string 'id' and 'text' fields")
        if not chunk["id"].strip() or not chunk["text"].strip():
            raise ValueError(f"Chunk {index} has an empty id or text")
        ids.append(chunk["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs")
    return chunks


def validate_embeddings(vectors: np.ndarray, expected_rows: int, expected_dims: int = 384) -> None:
    if vectors.shape != (expected_rows, expected_dims):
        raise ValueError(f"Expected {(expected_rows, expected_dims)}, got {vectors.shape}")
    if not np.isfinite(vectors).all():
        raise ValueError("Embedding vectors contain NaN or infinity")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-4):
        raise ValueError("Embedding vectors are not L2 normalized")


def build_embeddings(chunks_path: Path, output_dir: Path, model_name: str = MODEL_NAME) -> tuple[Path, Path]:
    from sentence_transformers import SentenceTransformer

    chunks = load_chunks(chunks_path)
    model = SentenceTransformer(model_name)
    vectors = np.asarray(model.encode(
        [chunk["text"] for chunk in chunks],
        batch_size=16,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ), dtype=np.float32)
    validate_embeddings(vectors, len(chunks))

    output_dir.mkdir(parents=True, exist_ok=True)
    vectors_path = output_dir / "schema_embeddings.npy"
    metadata_path = output_dir / "schema_embeddings_metadata.json"
    np.save(vectors_path, vectors, allow_pickle=False)
    metadata = {
        "model": model_name,
        "dimensions": vectors.shape[1],
        "normalized": True,
        "chunks_source": str(chunks_path.relative_to(PROJECT_ROOT)) if chunks_path.is_relative_to(PROJECT_ROOT) else str(chunks_path),
        "chunk_ids": [chunk["id"] for chunk in chunks],
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return vectors_path, metadata_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, default=PROJECT_ROOT / "artifacts" / "schema_chunks.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "artifacts")
    args = parser.parse_args()
    vectors_path, metadata_path = build_embeddings(args.chunks, args.output_dir)
    vectors = np.load(vectors_path, allow_pickle=False)
    print(f"Embeddings shape: {vectors.shape}")
    print(f"Saved vectors: {vectors_path}")
    print(f"Saved metadata: {metadata_path}")


if __name__ == "__main__":
    main()
