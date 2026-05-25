"""Index data/documents/ (A,B,C) + data/synthetic/cases.json into ChromaDB.

Usage:
    python -m rag.indexing.index_documents [--reset]

The first run downloads the default ONNX embedding model (~80MB).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import chromadb

from rag.config import (
    CHROMA_DB_PATH,
    PRIMARY_COLLECTION,
    SECONDARY_COLLECTION,
    DOC_TYPE_PROCESS,
    DOC_TYPE_PRODUCTION,
    DOC_TYPE_FEEDSTOCK,
    DOC_TYPE_CASE,
)
from rag.indexing.chunker import chunk_markdown

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "data" / "documents"
CASES_PATH = PROJECT_ROOT / "data" / "synthetic" / "cases.json"

FOLDER_TO_TYPE = {
    "A-process": DOC_TYPE_PROCESS,
    "B-production": DOC_TYPE_PRODUCTION,
    "C-feedstock": DOC_TYPE_FEEDSTOCK,
}


def _safe_meta(v):
    """ChromaDB metadata only accepts scalar types — coerce lists/dicts to strings."""
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, list):
        return ",".join(str(x) for x in v)
    return str(v)


def index_markdown_docs(collection) -> int:
    total = 0
    for folder, doc_type in FOLDER_TO_TYPE.items():
        folder_path = DOCS_ROOT / folder
        if not folder_path.exists():
            print(f"[index] skipped {folder} — not found")
            continue
        for md_path in sorted(folder_path.glob("*.md")):
            content = md_path.read_text(encoding="utf-8")
            chunks = chunk_markdown(content)
            if not chunks:
                continue
            ids = [f"{md_path.stem}__{c.chunk_index:03d}" for c in chunks]
            docs = [c.text for c in chunks]
            metas = [
                {
                    "doc_id": md_path.stem,
                    "doc_type": doc_type,
                    "section_title": c.section_title,
                    "source_path": str(md_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                }
                for c in chunks
            ]
            collection.upsert(ids=ids, documents=docs, metadatas=metas)
            print(f"[index] {md_path.name:35s} -> {len(chunks):3d} chunks ({doc_type})")
            total += len(chunks)
    return total


def index_cases(collection) -> int:
    if not CASES_PATH.exists():
        print(f"[index] cases.json not found at {CASES_PATH}")
        return 0
    with CASES_PATH.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    ids, docs, metas = [], [], []
    for c in cases:
        cid = c["case_id"]
        ctx = c.get("context", {})
        km = ctx.get("key_metrics", {})

        text_parts = [
            c.get("narrative", ""),
            f"판단: {c.get('decision', '')}",
            f"주요 이유: {', '.join(c.get('reason_codes', []) or ['-'])}",
            f"확인 우선순위: {', '.join(c.get('check_priority', []) or ['-'])}",
            f"리스크 코드: {', '.join(c.get('risk_codes', []) or ['-'])}",
            f"룰 요약: {c.get('rule_summary', '')}",
        ]
        text = "\n".join(p for p in text_parts if p)

        ids.append(f"case__{cid}")
        docs.append(text)
        metas.append(
            {
                "doc_id": cid,
                "doc_type": DOC_TYPE_CASE,
                "season": ctx.get("season", ""),
                "decision": c.get("decision", ""),
                "tank_history_flag": ctx.get("tank_history_flag", ""),
                "target_cfpp": float(ctx.get("target_cfpp", 0.0)),
                "wafi_ppm": float(km.get("wafi_ppm", 0.0) or 0.0),
                "wafi_type": _safe_meta(km.get("wafi_type", "")),
                "reason_codes": _safe_meta(c.get("reason_codes")),
                "risk_codes": _safe_meta(c.get("risk_codes")),
            }
        )

    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas)
        print(f"[index] cases.json -> {len(ids)} cases")
    return len(ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete and recreate the collection")
    args = parser.parse_args()

    CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

    if args.reset:
        for name in (PRIMARY_COLLECTION, SECONDARY_COLLECTION):
            try:
                client.delete_collection(name)
                print(f"[index] dropped collection {name}")
            except Exception:
                pass

    primary = client.get_or_create_collection(
        PRIMARY_COLLECTION,
        metadata={"description": "A-process + B-production + C-feedstock + D-cases"},
    )
    # Ensure secondary exists so /interview/* can add to it later
    client.get_or_create_collection(
        SECONDARY_COLLECTION,
        metadata={"description": "E - veteran tacit knowledge from interviews"},
    )

    print(f"[index] ChromaDB path: {CHROMA_DB_PATH}")
    print(f"[index] primary collection size (before): {primary.count()}")

    n_docs = index_markdown_docs(primary)
    n_cases = index_cases(primary)

    print(f"[index] === total indexed: {n_docs} doc-chunks + {n_cases} cases")
    print(f"[index] primary collection size (after):  {primary.count()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
