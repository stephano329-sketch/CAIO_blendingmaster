"""ChromaDB-backed RAG retriever for primary collection (docs + cases).

Provides:
    retrieve(query, top_k, filters)   -> list of RetrievedDoc
    retrieve_similar_cases(...)       -> list of RetrievedDoc filtered to doc_type=case
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import chromadb

from rag.config import CHROMA_DB_PATH, PRIMARY_COLLECTION


@dataclass
class RetrievedDoc:
    doc_id: str
    doc_type: str
    text: str
    metadata: dict[str, Any]
    distance: float

    @property
    def similarity_score(self) -> float:
        # Chroma returns L2 squared distance with the default embedding;
        # smaller is closer. Map to a (0,1] score for UI display.
        return float(1.0 / (1.0 + self.distance))


class RagRetriever:
    def __init__(self, db_path=CHROMA_DB_PATH, collection=PRIMARY_COLLECTION) -> None:
        self._client = chromadb.PersistentClient(path=str(db_path))
        self._collection = self._client.get_or_create_collection(collection)

    def count(self) -> int:
        return self._collection.count()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievedDoc]:
        if not query or not query.strip() or self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filters,
        )
        return _flatten(result)

    def retrieve_similar_cases(
        self,
        query: str,
        top_k: int = 3,
        season: str | None = None,
    ) -> list[RetrievedDoc]:
        filters: dict = {"doc_type": "case"}
        if season:
            filters = {"$and": [{"doc_type": "case"}, {"season": season}]}
        return self.retrieve(query=query, top_k=top_k, filters=filters)


def _flatten(result: dict) -> list[RetrievedDoc]:
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    out = []
    for _id, doc, meta, dist in zip(ids, docs, metas, dists):
        meta = meta or {}
        out.append(
            RetrievedDoc(
                doc_id=meta.get("doc_id", _id),
                doc_type=meta.get("doc_type", "unknown"),
                text=doc or "",
                metadata=meta,
                distance=float(dist),
            )
        )
    return out


@lru_cache(maxsize=1)
def get_retriever() -> RagRetriever:
    return RagRetriever()
