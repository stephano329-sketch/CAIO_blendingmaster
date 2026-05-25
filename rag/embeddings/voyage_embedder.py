"""
Voyage AI voyage-4 embedder for ChromaDB integration.

This module exposes two embedder classes:

- `VoyageEmbedder`: Production embedder using Voyage AI's voyage-4 model.
  Supports asymmetric retrieval (input_type='document' for indexing,
  'query' for search) which improves Top-K recall by 5–15% over symmetric
  embeddings. Requires `VOYAGE_API_KEY` environment variable.

- `FallbackEmbedder`: ChromaDB default embedder (`all-MiniLM-L6-v2`).
  English-focused; Korean retrieval quality is poor. Use only for local
  pipeline verification when VOYAGE_API_KEY is unavailable. NOT for
  production demo.

Both implementations conform to ChromaDB's `EmbeddingFunction` protocol
(callable taking `Iterable[str]` and returning `List[List[float]]`).
"""

from __future__ import annotations

import os
from typing import Iterable, List, Optional


class VoyageEmbedder:
    """voyage-4 embedder with asymmetric document/query support.

    Plan reference: `.moai/plans/rag-data.md` Decision R1.
    """

    DEFAULT_MODEL = "voyage-4"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        batch_size: int = 32,
    ) -> None:
        api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "VOYAGE_API_KEY env var is required for VoyageEmbedder. "
                "Set it before instantiation, or use FallbackEmbedder for local testing."
            )
        try:
            import voyageai  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "voyageai package not installed. Run: pip install voyageai"
            ) from exc

        import voyageai

        self._client = voyageai.Client(api_key=api_key)
        self._model = model
        self._batch_size = batch_size

    @property
    def model(self) -> str:
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed for indexing. Use this when adding to ChromaDB."""
        return self._embed(texts, input_type="document")

    def embed_queries(self, texts: List[str]) -> List[List[float]]:
        """Embed for search. Use this at query time."""
        return self._embed(texts, input_type="query")

    def _embed(self, texts: List[str], input_type: str) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            result = self._client.embed(
                texts=batch, model=self._model, input_type=input_type
            )
            all_embeddings.extend(result.embeddings)
        return all_embeddings

    # ChromaDB EmbeddingFunction protocol — used at indexing time.
    # ChromaDB's `query_texts` argument also routes through this, which
    # would technically use input_type='document' for queries; for the
    # MVP we accept this minor mismatch since accuracy impact is small.
    # For maximum accuracy, use `embed_queries()` directly with
    # `query_embeddings=` parameter in ChromaDB.
    def __call__(self, input: Iterable[str]) -> List[List[float]]:
        return self.embed_documents(list(input))

    def name(self) -> str:
        return f"voyage-{self._model}"


class FallbackEmbedder:
    """ChromaDB default (`all-MiniLM-L6-v2`) embedder for local pipeline verification.

    Korean retrieval quality is poor (model is English-trained).
    Acceptable for verifying that the indexing pipeline runs end-to-end,
    not for demo or KPI measurement.
    """

    def __init__(self) -> None:
        from chromadb.utils import embedding_functions

        self._inner = embedding_functions.DefaultEmbeddingFunction()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._inner(texts)

    def embed_queries(self, texts: List[str]) -> List[List[float]]:
        return self._inner(texts)

    def __call__(self, input: Iterable[str]) -> List[List[float]]:
        return self._inner(list(input))

    def name(self) -> str:
        return "chromadb-default-MiniLM-L6"


def get_embedder(prefer_voyage: bool = True):
    """Select embedder based on environment availability.

    Returns VoyageEmbedder if VOYAGE_API_KEY is set and `prefer_voyage`
    is True; otherwise returns FallbackEmbedder with a stderr warning.
    """
    if prefer_voyage and os.environ.get("VOYAGE_API_KEY"):
        try:
            return VoyageEmbedder()
        except Exception as exc:  # pragma: no cover
            import sys
            print(
                f"[warn] VoyageEmbedder failed ({exc}); falling back to default.",
                file=sys.stderr,
            )

    import sys
    print(
        "[info] Using FallbackEmbedder (chromadb default, all-MiniLM-L6-v2). "
        "Korean retrieval quality will be poor. "
        "Set VOYAGE_API_KEY for voyage-4 embedding.",
        file=sys.stderr,
    )
    return FallbackEmbedder()


if __name__ == "__main__":
    e = get_embedder()
    sample = ["혹한기 LCO 비율이 높은 케이스에서 WAFI 효과", "동절기 표준 블렌딩"]
    docs = e.embed_documents(sample)
    print(f"Embedder: {e.name()}")
    print(f"Embedded {len(docs)} docs, dimension = {len(docs[0])}")
