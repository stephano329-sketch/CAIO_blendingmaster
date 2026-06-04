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
    "당신은 'Blending Master' AI 컨설턴트입니다. 한국 정유사의 경유 품질·블렌딩 의사결정을 보조합니다.\n\n"
    "응답은 반드시 아래 3개 섹션 마크다운 구조를 그대로 따르세요. 섹션 헤더와 이모지를 그대로 사용하세요.\n\n"
    "## 📚 RAG 기반 답변\n"
    "- 제공된 컨텍스트(사례·문서 + 베테랑 지식 KB)에서 직접 도출 가능한 내용만 작성합니다.\n"
    "- 인용한 ID를 본문에 표시하세요: 사례 ID(DIESEL-D-XXX), 문서 ID(A-XX, B-XX, C-XX), 베테랑 지식 ID(KB-XXXX).\n"
    "- 베테랑 지식(KB-XXXX) 인용 시 작성자 라벨도 함께 명시(예: \"KB-0003 (이 부장)\")하여 노하우 출처를 분명히 합니다.\n"
    "- 베테랑 KB의 Q1 판단·Q5 메모는 정량 문서 못지않게 중요한 근거로 취급하고, 가능하면 KB를 우선 인용하세요.\n"
    "- 컨텍스트에 답이 전혀 없으면 \"컨텍스트에서 직접 도출 가능한 답변 없음\"이라고 명시하세요.\n\n"
    "## ⚠️ 컨텍스트 한계\n"
    "- 제공된 컨텍스트에 포함되지 않은 정보(정량 공식, 수치 기준, 누락된 조건 등)를 bullet로 명시합니다.\n"
    "- 한계가 없으면 \"주요 정보는 컨텍스트에 모두 포함됨\"이라고 적습니다.\n\n"
    "## 💡 일반 지식 보완 (RAG 외)\n"
    "- 위 한계를 보완하기 위해 모델 학습 지식·업계 통용 기준·일반 화학 원리를 활용해 추가 인사이트를 제공합니다.\n"
    "- 가능한 한 정량적인 범위(예: 일반적으로 X~Y ppm, 통상 ±N°C)를 제시하되, **출처 미검증**임을 명확히 표시하세요.\n"
    "- 각 항목 끝에 (모델 추정) 또는 (업계 통용) 같은 라벨을 붙입니다.\n"
    "- 이 섹션의 내용은 RAG 컨텍스트와 다를 수 있으며, 실제 적용 전 검증이 필요합니다.\n\n"
    "응답 마지막 줄에 다음 안내를 그대로 출력하세요:\n"
    "ℹ️ 최종 의사결정은 담당자가 수행하세요. 일반 지식 보완 섹션은 검증 후 적용하세요."
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
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 1536,
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
                        f"=== 검색된 컨텍스트 (RAG) ===\n{context_block}\n=== 컨텍스트 끝 ===\n\n"
                        "지침대로 3개 섹션(📚 RAG 기반 답변 / ⚠️ 컨텍스트 한계 / 💡 일반 지식 보완) "
                        "구조로 답해 주세요. 일반 지식 보완 섹션에서는 RAG에 없는 정량 기준·업계 통용 수치·"
                        "화학 원리 등을 적극적으로 보완하되, 각 항목 끝에 (모델 추정) 또는 (업계 통용) 라벨을 붙여 "
                        "RAG 인용과 구분되도록 표시하세요."
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
