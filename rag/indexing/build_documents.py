"""
Build A·B·C documents into RAG chunks.

Walks `data/documents/{A-process,B-production,C-feedstock}/`, parses YAML
frontmatter, and produces chunk records suitable for ChromaDB indexing.

Each markdown file becomes a single chunk (R4 default = section-level).
Files larger than `MAX_CHUNK_TOKENS` are sub-chunked by H2 boundaries.

Returns a list of `Chunk` dataclasses with id, document text, and metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_ROOT = PROJECT_ROOT / "data" / "documents"

# Sub-chunking threshold (tokens, approximate via word count × 1.3)
MAX_CHUNK_TOKENS = 1000

# Frontmatter delimiter
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$",
    re.DOTALL,
)


@dataclass
class Chunk:
    """Single RAG chunk with metadata for ChromaDB."""

    id: str
    document: str
    metadata: Dict[str, str] = field(default_factory=dict)


def _approximate_tokens(text: str) -> int:
    """Rough token count: word count × 1.3 (Korean tends ~1 token per char,
    English ~0.75 per word). Heuristic acceptable for chunking decision."""
    words = text.split()
    return int(len(words) * 1.3)


def _parse_frontmatter(raw: str) -> tuple[Dict, str]:
    """Split YAML frontmatter from body. Returns ({}, raw) if absent."""
    match = FRONTMATTER_PATTERN.match(raw)
    if not match:
        return {}, raw
    yaml_text, body = match.group(1), match.group(2)
    try:
        meta = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, body


def _split_by_h2(body: str) -> List[tuple[str, str]]:
    """Split body by H2 headers (`## ...`). Returns [(subtitle, sub-body)]."""
    parts: List[tuple[str, str]] = []
    current_title = ""
    current_lines: List[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current_lines:
                parts.append((current_title, "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        parts.append((current_title, "\n".join(current_lines).strip()))
    return parts


def _build_chunk(
    section_id: str,
    document_text: str,
    frontmatter: Dict,
    subsection: Optional[str] = None,
) -> Chunk:
    chunk_id = f"doc:{section_id}"
    if subsection:
        # Slugify subsection for ID
        slug = re.sub(r"[^\w가-힣-]+", "-", subsection).strip("-")[:50]
        chunk_id = f"doc:{section_id}#{slug}"

    metadata: Dict[str, str] = {
        "doc_type": str(frontmatter.get("doc_type", "unknown")),
        "section_id": section_id,
        "section_title": str(frontmatter.get("title", "")),
        "lang": str(frontmatter.get("lang", "ko")),
        "version": str(frontmatter.get("version", "1.0")),
        "source": str(frontmatter.get("source", "synthetic")),
    }
    if subsection:
        metadata["subsection"] = subsection
    return Chunk(id=chunk_id, document=document_text, metadata=metadata)


def build_chunks_from_file(path: Path) -> List[Chunk]:
    """Parse one markdown file into one or more chunks.

    Strategy: single chunk if approximate token count ≤ MAX_CHUNK_TOKENS,
    otherwise split by H2 sections.
    """
    raw = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(raw)
    section_id = fm.get("section_id") or path.stem.split("-", 1)[-1]

    if _approximate_tokens(body) <= MAX_CHUNK_TOKENS:
        return [_build_chunk(section_id, body.strip(), fm)]

    chunks: List[Chunk] = []
    for subtitle, sub_body in _split_by_h2(body):
        if not sub_body.strip():
            continue
        chunks.append(_build_chunk(section_id, sub_body, fm, subsection=subtitle))
    if not chunks:  # H2 split produced nothing (rare); fall back to single
        chunks = [_build_chunk(section_id, body.strip(), fm)]
    return chunks


def build_all_documents() -> List[Chunk]:
    """Walk all subdirectories of data/documents/ and build chunks.

    Returns all chunks in deterministic order (sorted by file path).
    """
    md_files = sorted(DOCUMENTS_ROOT.glob("*/*.md"))
    chunks: List[Chunk] = []
    for path in md_files:
        try:
            chunks.extend(build_chunks_from_file(path))
        except Exception as exc:  # surface parse errors clearly
            raise RuntimeError(f"Failed to build chunks from {path}: {exc}") from exc
    return chunks


def main() -> None:
    chunks = build_all_documents()
    print(f"Built {len(chunks)} document chunks")

    # Group by doc_type for inspection
    by_type: Dict[str, List[Chunk]] = {}
    for c in chunks:
        by_type.setdefault(c.metadata["doc_type"], []).append(c)
    for doc_type, items in by_type.items():
        print(f"  {doc_type}: {len(items)} chunks")

    # Sample
    sample = chunks[0]
    print()
    print(f"Sample chunk:")
    print(f"  id: {sample.id}")
    print(f"  metadata: {sample.metadata}")
    print(f"  document (first 200 chars): {sample.document[:200]!r}")


if __name__ == "__main__":
    main()
