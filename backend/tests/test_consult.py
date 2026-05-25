"""Integration tests for /consult — require the primary ChromaDB index to exist.

Run `python -m rag.indexing.index_documents` first (or skip these tests).
"""
import pytest

from backend.engine.rag_retriever import get_retriever


def _index_available() -> bool:
    try:
        return get_retriever().count() > 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _index_available(),
    reason="primary ChromaDB collection is empty — run rag.indexing.index_documents",
)


def test_consult_basic(client):
    r = client.post(
        "/consult",
        json={"query": "혹한기 WAFI 투입 전략", "top_k": 5},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "answer" in body
    assert isinstance(body["citations"], list)
    assert body["retrieved_count"] >= 1
    assert "used_llm" in body


def test_consult_filtered_by_doc_type(client):
    r = client.post(
        "/consult",
        json={"query": "LCO 영향", "top_k": 3, "doc_type": "feedstock"},
    )
    assert r.status_code == 200
    body = r.json()
    for c in body["citations"]:
        assert c["doc_type"] == "feedstock"


def test_consult_validation_error(client):
    r = client.post("/consult", json={"query": "", "top_k": 5})
    assert r.status_code == 422
