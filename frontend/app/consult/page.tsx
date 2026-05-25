"use client";

import { useEffect, useState } from "react";
import { DecisionBadge } from "@/components/badge";
import { api } from "@/lib/api";
import type { ConsultResponse, ConsultCitation, Decision } from "@/lib/types";

type Ctx = {
  batchId: string;
  decision: Decision;
  season: string;
  targetCfpp: number;
  blend: { lgo: number; hgo: number; lco: number; kero: number; bio: number };
  baselineCfpp: number;
};

const SEASON_LABEL: Record<string, string> = { winter: "동절기", deep_winter: "혹한기" };

type Msg = {
  role: "user" | "ai";
  text: string;
  citations?: ConsultCitation[];
  usedLlm?: boolean;
  model?: string | null;
};

const SUGGESTIONS = [
  "LCO 비율이 높을 때 WAFI를 더 넣어야 하나요?",
  "혹한기 탱크 이력이 있을 때 안전 마진은?",
  "현재 케이스에서 위험 신호가 있나요?",
];

const TYPE_LABEL: Record<string, string> = {
  case: "CASE",
  process: "PROC",
  production: "PROD",
  feedstock: "FEED",
  rule: "RULE",
  doc: "DOC",
};
const TYPE_CLASS: Record<string, string> = {
  case: "src-case",
  process: "src-doc",
  production: "src-doc",
  feedstock: "src-doc",
  rule: "src-rule",
  doc: "src-doc",
};

export default function ConsultPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string>("");
  const [ctx, setCtx] = useState<Ctx | null>(null);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("consult_context");
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && parsed.blend && typeof parsed.blend.lgo === "number") {
        setCtx(parsed as Ctx);
      } else {
        // Old/invalid schema — discard
        sessionStorage.removeItem("consult_context");
      }
    } catch {
      sessionStorage.removeItem("consult_context");
    }
  }, []);

  const clearCtx = () => {
    sessionStorage.removeItem("consult_context");
    setCtx(null);
  };

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const r: ConsultResponse = await api.consult({
        query: text,
        top_k: 5,
        season: ctx?.season,
      });
      setMessages((m) => [
        ...m,
        {
          role: "ai",
          text: r.answer,
          citations: r.citations,
          usedLlm: r.used_llm,
          model: r.model,
        },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setMessages((m) => [
        ...m,
        { role: "ai", text: `백엔드 호출 실패: ${msg}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-layout">
      <div className="context-bar">
        <i className="ti ti-file-description" style={{ fontSize: 14, color: "var(--color-text-secondary)" }} />
        {ctx ? (
          <>
            <span style={{ color: "var(--color-text-secondary)", fontSize: 11 }}>Batch</span>
            <span className="ctx-batch">{ctx.batchId}</span>
            <DecisionBadge decision={ctx.decision} />
            <span className="ctx-right">
              LGO {ctx.blend.lgo}% · HGO {ctx.blend.hgo}% · LCO {ctx.blend.lco}% · Kero {ctx.blend.kero}% · Bio {ctx.blend.bio}%
              {" · 목표 CFPP "}{ctx.targetCfpp}°C
              {" · "}{SEASON_LABEL[ctx.season] ?? ctx.season}
              {" · 베이스라인 "}{ctx.baselineCfpp.toFixed(1)}°C
            </span>
            <button
              onClick={clearCtx}
              title="컨텍스트 해제"
              style={{ marginLeft: 8, background: "transparent", border: "none", cursor: "pointer", color: "var(--color-text-secondary)" }}
            >
              <i className="ti ti-x" />
            </button>
          </>
        ) : (
          <span style={{ color: "var(--color-text-secondary)", fontSize: 11 }}>
            컨텍스트 없음 — 신규 판단에서 "AI 상담 요청" 버튼을 누르면 자동으로 연동됩니다
          </span>
        )}
      </div>
      <div className="chat-messages">
        {messages.length === 0 && (
          <>
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 8 }}>
              추천 질문
            </div>
            <div className="suggestion-list">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion-btn" onClick={() => send(s)}>
                  <i
                    className="ti ti-message-circle"
                    style={{ fontSize: 14, color: "#BA7517", marginRight: 6 }}
                  />
                  {s}
                </button>
              ))}
            </div>
          </>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg-${m.role}`}>
            <div>
              <div className="bubble" style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
              {m.role === "ai" && (m.usedLlm !== undefined) && (
                <div style={{ fontSize: 10, color: "var(--color-text-secondary)", marginTop: 4, marginLeft: 2 }}>
                  {m.usedLlm
                    ? `LLM 응답 · ${m.model ?? "claude"}`
                    : "RAG 인용 요약 (LLM 미사용 — ANTHROPIC_API_KEY 미설정)"}
                </div>
              )}
              {m.citations && m.citations.length > 0 && (
                <div className="source-tags">
                  {m.citations.map((s) => (
                    <div key={s.doc_id + s.preview.slice(0, 10)} className="src-tag" title={s.preview}>
                      <span className={`src-type ${TYPE_CLASS[s.doc_type] ?? "src-doc"}`}>
                        {TYPE_LABEL[s.doc_type] ?? s.doc_type.toUpperCase()}
                      </span>
                      <span className="src-id">{s.doc_id}</span>
                      <span className="src-desc">
                        {s.section_title ?? s.preview.slice(0, 60)}
                        {" · "}
                        {(s.similarity_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--color-text-secondary)", fontSize: 13 }}>
            <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
            RAG 검색 + LLM 응답 생성 중...
          </div>
        )}
        {error && !loading && (
          <div style={{ fontSize: 11, color: "#A32D2D" }}>
            <i className="ti ti-alert-octagon" style={{ marginRight: 4 }} />
            {error}
          </div>
        )}
      </div>
      <div className="chat-input-row">
        <input
          placeholder="질문을 입력하세요... (Enter)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") send(input);
          }}
          disabled={loading}
        />
        <button className="btn-primary" onClick={() => send(input)} disabled={loading}>
          <i className="ti ti-send" />
        </button>
      </div>
    </div>
  );
}
