"""
End-to-end ChromaDB indexing for the Blending Master RAG system.

Loads chunks from `build_documents`, `build_cases`, `build_heuristics` and
upserts them into two collections:

- `primary_rag`   — A·B·C documents + D cases (56 chunks total)
- `secondary_rag` — E heuristics (35 chunks)

The script is **idempotent**: re-running upserts by ID without creating
duplicates. To force a full rebuild, delete `rag/chroma_db/`.

Usage:
    python -m rag.indexing.index_all [--reset]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import List, Sequence, Tuple

import chromadb
from chromadb.config import Settings

from rag.embeddings.voyage_embedder import get_embedder
from rag.indexing.build_cases import build_case_chunks
from rag.indexing.build_documents import Chunk, build_all_documents
from rag.indexing.build_heuristics import build_heuristic_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DB_PATH = PROJECT_ROOT / "rag" / "chroma_db"

PRIMARY_COLLECTION = "primary_rag"
SECONDARY_COLLECTION = "secondary_rag"

UPSERT_BATCH_SIZE = 32


def _split_chunks(chunks: Sequence[Chunk]) -> Tuple[List[str], List[str], List[dict]]:
    ids = [c.id for c in chunks]
    docs = [c.document for c in chunks]
    metas = [dict(c.metadata) for c in chunks]
    return ids, docs, metas


def _upsert_in_batches(collection, chunks: Sequence[Chunk], label: str) -> None:
    """ChromaDB upsert with batching to avoid request size limits."""
    total = len(chunks)
    for start in range(0, total, UPSERT_BATCH_SIZE):
        batch = chunks[start : start + UPSERT_BATCH_SIZE]
        ids, docs, metas = _split_chunks(batch)
        collection.upsert(ids=ids, documents=docs, metadatas=metas)
        end = min(start + UPSERT_BATCH_SIZE, total)
        print(f"  [{label}] upserted {end}/{total}")


def _reset_chroma_dir() -> None:
    if CHROMA_DB_PATH.exists():
        print(f"Removing existing {CHROMA_DB_PATH}")
        shutil.rmtree(CHROMA_DB_PATH)


def index_all(reset: bool = False) -> dict:
    """Build all chunks and upsert into ChromaDB. Returns count summary."""
    if reset:
        _reset_chroma_dir()

    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

    print(f"=== RAG Indexing Pipeline ===")
    print(f"ChromaDB path: {CHROMA_DB_PATH}")

    embedder = get_embedder()
    print(f"Embedder: {embedder.name()}")

    client = chromadb.PersistentClient(
        path=str(CHROMA_DB_PATH),
        settings=Settings(anonymized_telemetry=False),
    )

    # Build chunks
    print()
    print("Building chunks...")
    t0 = time.time()
    doc_chunks = build_all_documents()
    case_chunks = build_case_chunks()
    heuristic_chunks = build_heuristic_chunks()
    print(f"  documents: {len(doc_chunks)}")
    print(f"  cases:     {len(case_chunks)}")
    print(f"  heuristics: {len(heuristic_chunks)}")
    print(f"  build elapsed: {time.time() - t0:.2f}s")

    primary_chunks = list(doc_chunks) + list(case_chunks)
    secondary_chunks = list(heuristic_chunks)

    # Primary collection
    print()
    print(f"=> Indexing {PRIMARY_COLLECTION} ({len(primary_chunks)} chunks)")
    primary = client.get_or_create_collection(
        name=PRIMARY_COLLECTION,
        embedding_function=embedder,
        metadata={"hnsw:space": "cosine"},
    )
    t1 = time.time()
    _upsert_in_batches(primary, primary_chunks, "primary")
    print(f"  primary indexed in {time.time() - t1:.2f}s")

    # Secondary collection
    print()
    print(f"=> Indexing {SECONDARY_COLLECTION} ({len(secondary_chunks)} chunks)")
    secondary = client.get_or_create_collection(
        name=SECONDARY_COLLECTION,
        embedding_function=embedder,
        metadata={"hnsw:space": "cosine"},
    )
    t2 = time.time()
    _upsert_in_batches(secondary, secondary_chunks, "secondary")
    print(f"  secondary indexed in {time.time() - t2:.2f}s")

    # Verification
    print()
    print("=== Verification ===")
    primary_count = primary.count()
    secondary_count = secondary.count()
    print(f"  {PRIMARY_COLLECTION}.count() = {primary_count}")
    print(f"  {SECONDARY_COLLECTION}.count() = {secondary_count}")

    # Sample query
    print()
    print("=== Sample Query (smoke test) ===")
    sample_query = "혹한기 LCO 비율이 높은 케이스에서 WAFI 효과"
    print(f"Query: {sample_query!r}")

    # Use embed_queries for asymmetric retrieval
    if hasattr(embedder, "embed_queries"):
        query_embedding = embedder.embed_queries([sample_query])[0]
        results = primary.query(
            query_embeddings=[query_embedding],
            n_results=5,
        )
    else:  # pragma: no cover
        results = primary.query(query_texts=[sample_query], n_results=5)

    print(f"Top-5 from {PRIMARY_COLLECTION}:")
    for i, (doc_id, distance) in enumerate(
        zip(results["ids"][0], results["distances"][0]), start=1
    ):
        meta = results["metadatas"][0][i - 1]
        title = meta.get("section_title") or meta.get("case_id") or doc_id
        print(f"  {i}. [{distance:.3f}] {doc_id} — {title}")

    return {
        "primary_count": primary_count,
        "secondary_count": secondary_count,
        "embedder": embedder.name(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Index RAG data into ChromaDB.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing chroma_db directory before indexing.",
    )
    args = parser.parse_args()

    summary = index_all(reset=args.reset)

    expected_primary = 56  # 21 docs + 35 cases
    expected_secondary = 35

    if summary["primary_count"] != expected_primary:
        print(
            f"WARN: primary count mismatch — got {summary['primary_count']}, "
            f"expected {expected_primary}",
            file=sys.stderr,
        )
        return 1
    if summary["secondary_count"] != expected_secondary:
        print(
            f"WARN: secondary count mismatch — got {summary['secondary_count']}, "
            f"expected {expected_secondary}",
            file=sys.stderr,
        )
        return 1

    print()
    print(f"OK — counts match (primary={expected_primary}, secondary={expected_secondary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
