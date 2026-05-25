"""LLM client wrapper.

If ANTHROPIC_API_KEY is set in the environment, calls Claude via the
official SDK. Otherwise returns a deterministic citation-only summary
so the API stays functional in demo mode.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


@dataclass
class LlmAnswer:
    text: str
    used_llm: bool
    model: str | None = None


SYSTEM_PROMPT = (
    "당신은 'Blending Master' AI 컨설턴트입니다. 한국 정유사의 경유 품질·블렌딩 의사결정을 보조합니다. "
    "사용자 질문에 답할 때 반드시 제공된 컨텍스트(사례·문서)만을 근거로 사용하고, "
    "근거가 부족하면 그 사실을 명시하세요. 환각 금지. "
    "응답에 인용한 사례 ID(DIESEL-D-XXX) 또는 문서 ID(A-XX, B-XX, C-XX)를 본문에 표시하세요. "
    "최종 의사결정은 담당자가 수행한다는 점을 응답 끝에 한 줄로 안내하세요."
)


def _fallback_answer(query: str, snippets: list[dict]) -> str:
    if not snippets:
        return (
            f"질의: \"{query}\"\n\n"
            "근거 문서를 찾지 못했습니다. 질문을 더 구체화하거나 케이스 ID를 함께 제시해 주세요.\n\n"
            "ℹ︎ 최종 의사결정은 담당자가 수행하세요."
        )
    lines = [f"질의: \"{query}\"", "", "관련 근거(요약):"]
    for s in snippets[:5]:
        doc_id = s.get("doc_id", "?")
        section = s.get("section_title") or s.get("decision") or ""
        preview = (s.get("text") or "").strip().replace("\n", " ")
        if len(preview) > 220:
            preview = preview[:220] + "…"
        tag = f"[{doc_id}{' · ' + section if section else ''}]"
        lines.append(f"- {tag} {preview}")
    lines.append("")
    lines.append(
        "※ LLM API 키(ANTHROPIC_API_KEY)가 설정되지 않아 retrieval-only 응답을 제공했습니다."
    )
    lines.append("ℹ︎ 최종 의사결정은 담당자가 수행하세요.")
    return "\n".join(lines)


def generate_answer(
    query: str,
    snippets: list[dict],
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 1024,
) -> LlmAnswer:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return LlmAnswer(text=_fallback_answer(query, snippets), used_llm=False)

    try:
        import anthropic  # noqa: WPS433  (delayed import keeps tests light)

        client = anthropic.Anthropic(api_key=api_key)
        context_block = _format_context(snippets)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"질의:\n{query}\n\n"
                        f"=== 검색된 컨텍스트 ===\n{context_block}\n=== 컨텍스트 끝 ===\n\n"
                        "위 컨텍스트만 사용해 답해 주세요."
                    ),
                }
            ],
        )
        text = "".join(
            getattr(block, "text", "") for block in message.content if getattr(block, "type", "") == "text"
        )
        return LlmAnswer(text=text.strip(), used_llm=True, model=model)
    except Exception as exc:  # noqa: BLE001  (graceful degradation)
        fallback = _fallback_answer(query, snippets)
        return LlmAnswer(
            text=f"{fallback}\n\n(LLM 호출 실패: {exc.__class__.__name__})",
            used_llm=False,
        )


def _format_context(snippets: Iterable[dict]) -> str:
    parts = []
    for s in snippets:
        doc_id = s.get("doc_id", "?")
        doc_type = s.get("doc_type", "?")
        section = s.get("section_title") or s.get("decision") or ""
        head = f"[{doc_id} | {doc_type}{' | ' + section if section else ''}]"
        parts.append(f"{head}\n{s.get('text', '').strip()}")
    return "\n\n---\n\n".join(parts)
