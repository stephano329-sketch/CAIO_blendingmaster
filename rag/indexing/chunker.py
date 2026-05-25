"""Markdown chunker — splits documents by H2/H3 headers with size guard."""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_CHARS = 1200
MIN_CHARS = 80


@dataclass
class Chunk:
    text: str
    section_title: str
    chunk_index: int


_HEADER_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)


def chunk_markdown(content: str) -> list[Chunk]:
    """Split markdown by H2/H3 headers; further split chunks that exceed MAX_CHARS."""
    lines = content.splitlines()

    sections: list[tuple[str, list[str]]] = []
    current_title = "intro"
    current_buf: list[str] = []
    for line in lines:
        m = _HEADER_RE.match(line)
        if m and len(m.group(1)) in (2, 3):
            if current_buf:
                sections.append((current_title, current_buf))
            current_title = m.group(2).strip()
            current_buf = []
        else:
            current_buf.append(line)
    if current_buf:
        sections.append((current_title, current_buf))

    chunks: list[Chunk] = []
    idx = 0
    for title, buf in sections:
        text = "\n".join(buf).strip()
        if not text or len(text) < MIN_CHARS:
            continue
        if len(text) <= MAX_CHARS:
            chunks.append(Chunk(text=text, section_title=title, chunk_index=idx))
            idx += 1
            continue
        for sub in _split_oversized(text, MAX_CHARS):
            chunks.append(Chunk(text=sub, section_title=title, chunk_index=idx))
            idx += 1
    return chunks


def _split_oversized(text: str, max_chars: int) -> list[str]:
    """Split by blank-line paragraphs, then merge greedily up to max_chars."""
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    out: list[str] = []
    buf = ""
    for p in paras:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= max_chars:
            buf = f"{buf}\n\n{p}"
        else:
            out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out
