"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";
import type { ConsultResponse, ConsultCitation } from "@/lib/types";

type Batch = {
  log_id: string;
  created_at: string;
  season: string;
  blend_components: Record<string, number>;
  target_cfpp: number;
  predicted_cfpp_baseline: number;
  selected_scenario: string | null;
  selected_wafi_ppm: number | null;
  selected_wafi_type: string | null;
  predicted_cfpp_after_wafi: number | null;
  margin_to_target: number | null;
  check_priority: string[];
  similar_case_ids: string[];
  actual_cfpp: number | null;
  actual_wafi: number | null;
};

type Ctx = {
  batchId: string;
  season: string;
  targetCfpp: number;
  blend: { lgo: number; hgo: number; lco: number; kero: number; bio: number };
  baselineCfpp: number;
};

function batchToCtx(b: Batch): Ctx {
  const bc = b.blend_components || {};
  return {
    batchId: b.log_id,
    season: b.season,
    targetCfpp: b.target_cfpp,
    blend: {
      lgo: Math.round((bc.lgo ?? 0) * 100),
      hgo: Math.round((bc.hgo ?? 0) * 100),
      lco: Math.round((bc.lco ?? 0) * 100),
      kero: Math.round((bc.kero ?? 0) * 100),
      bio: Math.round((bc.biodiesel ?? 0) * 100),
    },
    baselineCfpp: b.predicted_cfpp_baseline,
  };
}

function formatBatchDate(iso: string) {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return iso;
  }
}

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

type CaseDetail = {
  case_id: string;
  season: string;
  target_cfpp: number;
  blend_components: Record<string, number>;
  key_metrics: Record<string, number | string>;
};

function CaseTooltip({ c, x, y }: { c: CaseDetail; x: number; y: number }) {
  const blend = Object.entries(c.blend_components || {});
  const cols: { label: string; value: string }[] = [];
  const km = c.key_metrics || {};
  if (c.target_cfpp != null) cols.push({ label: "CFPP", value: c.target_cfpp.toFixed(1) + " °C" });
  const cfppMeasured = km.cfpp_measured ?? km.cfpp;
  if (cfppMeasured != null) cols.push({ label: "실측 CFPP", value: Number(cfppMeasured).toFixed(1) + " °C" });
  if (km.wafi_type) cols.push({ label: "WAFI 종류", value: String(km.wafi_type) });
  if (km.wafi_ppm != null) cols.push({ label: "WAFI 투입량", value: Number(km.wafi_ppm).toFixed(0) + " ppm" });
  if (c.season) cols.push({ label: "계절", value: SEASON_LABEL[c.season] ?? c.season });

  const TIP_W = 380, TIP_H = 170, PAD = 8;
  const left = Math.min(Math.max(x, PAD), window.innerWidth - TIP_W - PAD);
  const top = Math.min(y + 10, window.innerHeight - TIP_H - PAD);

  const CODE_MAP: Record<string, string> = { lgo: "LGO", hgo: "HGO", lco: "LCO", kero: "Kero", biodiesel: "Bio" };

  return (
    <div className="case-tip" style={{ left, top }}>
      {blend.length > 0 && (
        <>
          <div className="case-tip-section">블렌딩 구성 (%)</div>
          <table>
            <thead>
              <tr>{blend.map(([k]) => <th key={k}>{CODE_MAP[k] ?? k.toUpperCase()}</th>)}</tr>
            </thead>
            <tbody>
              <tr>{blend.map(([k, v]) => (
                <td key={k}>{typeof v === "number" ? (v * 100).toFixed(1) : String(v)}</td>
              ))}</tr>
            </tbody>
          </table>
        </>
      )}
      {cols.length > 0 && (
        <>
          <div className="case-tip-section">CFPP · WAFI · 컨텍스트</div>
          <table>
            <thead><tr>{cols.map((col) => <th key={col.label}>{col.label}</th>)}</tr></thead>
            <tbody><tr>{cols.map((col) => <td key={col.label}>{col.value}</td>)}</tr></tbody>
          </table>
        </>
      )}
    </div>
  );
}

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
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>("");
  const [caseCache, setCaseCache] = useState<Record<string, CaseDetail>>({});
  const [hover, setHover] = useState<{ c: CaseDetail; x: number; y: number } | null>(null);

  // Derive ctx from currently selected batch
  const selectedBatch = batches.find((b) => b.log_id === selectedBatchId) ?? null;
  const ctx: Ctx | null = selectedBatch ? batchToCtx(selectedBatch) : null;

  const onCaseHover = async (e: React.MouseEvent<HTMLElement>, caseId: string) => {
    const r = e.currentTarget.getBoundingClientRect();
    const cached = caseCache[caseId];
    if (cached) {
      setHover({ c: cached, x: r.left, y: r.bottom });
      return;
    }
    try {
      const data = await api.getCase(caseId);
      setCaseCache((prev) => ({ ...prev, [caseId]: data as CaseDetail }));
      setHover({ c: data as CaseDetail, x: r.left, y: r.bottom });
    } catch {
      // ignore fetch failure silently — tooltip just won't appear
    }
  };

  useEffect(() => {
    api
      .listBatches({ limit: 50 })
      .then((rows) => {
        const list = rows as Batch[];
        setBatches(list);
        if (list.length === 0) return;
        // If /judge handed off a specific batchId via sessionStorage, prefer it.
        let initial = list[0].log_id;
        try {
          const raw = sessionStorage.getItem("consult_context");
          if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed?.batchId && list.some((b) => b.log_id === parsed.batchId)) {
              initial = parsed.batchId;
            }
            sessionStorage.removeItem("consult_context");
          }
        } catch {
          // ignore
        }
        setSelectedBatchId(initial);
      })
      .catch(() => {
        // Silent: page still works without batches; dropdown will show empty state
      });
  }, []);

  const clearCtx = () => setSelectedBatchId("");

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
      {hover && <CaseTooltip c={hover.c} x={hover.x} y={hover.y} />}
      <div className="context-bar">
        <i className="ti ti-file-description" style={{ fontSize: 14, color: "var(--color-text-secondary)" }} />
        <span style={{ color: "var(--color-text-secondary)", fontSize: 11 }}>Batch</span>
        {batches.length === 0 ? (
          <span style={{ color: "var(--color-text-secondary)", fontSize: 11 }}>
            저장된 배합 일지가 없습니다 — 신규 판단에서 시나리오를 선택하면 여기에 표시됩니다
          </span>
        ) : (
          <>
            <select
              value={selectedBatchId}
              onChange={(e) => setSelectedBatchId(e.target.value)}
              style={{
                fontSize: 11,
                padding: "3px 8px",
                border: "0.5px solid var(--color-border-secondary)",
                borderRadius: 4,
                background: "var(--color-background-secondary)",
                fontFamily: "var(--font-mono)",
                cursor: "pointer",
              }}
            >
              <option value="">(컨텍스트 없음)</option>
              {batches.map((b) => (
                <option key={b.log_id} value={b.log_id}>
                  {b.log_id} · {formatBatchDate(b.created_at)} · {SEASON_LABEL[b.season] ?? b.season}
                </option>
              ))}
            </select>
            {ctx && (
              <>
                <span className="ctx-right">
                  LGO {ctx.blend.lgo}% · HGO {ctx.blend.hgo}% · LCO {ctx.blend.lco}% · Kero {ctx.blend.kero}% · Bio {ctx.blend.bio}%
                  {" · 목표 CFPP "}{ctx.targetCfpp}°C
                  {" · "}{SEASON_LABEL[ctx.season] ?? ctx.season}
                  {" · 베이스라인 "}{ctx.baselineCfpp.toFixed(1)}°C
                </span>
                <button
                  onClick={clearCtx}
                  title="컨텍스트 해제"
                  style={{ marginLeft: 4, background: "transparent", border: "none", cursor: "pointer", color: "var(--color-text-secondary)" }}
                >
                  <i className="ti ti-x" />
                </button>
              </>
            )}
          </>
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
              <div className="bubble">
                {m.role === "ai" ? (
                  <div className="md">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text}</ReactMarkdown>
                  </div>
                ) : (
                  <span style={{ whiteSpace: "pre-wrap" }}>{m.text}</span>
                )}
              </div>
              {m.role === "ai" && (m.usedLlm !== undefined) && (
                <div style={{ fontSize: 10, color: "var(--color-text-secondary)", marginTop: 4, marginLeft: 2 }}>
                  {m.usedLlm
                    ? `LLM 응답 · ${m.model ?? "claude"}`
                    : "RAG 인용 요약 (LLM 미사용 — ANTHROPIC_API_KEY 미설정)"}
                </div>
              )}
              {m.citations && m.citations.length > 0 && (
                <div className="source-tags">
                  {m.citations.map((s) => {
                    const isCase = s.doc_type === "case";
                    return (
                      <div
                        key={s.doc_id + s.preview.slice(0, 10)}
                        className="src-tag"
                        title={isCase ? undefined : s.preview}
                        style={isCase ? { cursor: "help" } : undefined}
                        onMouseEnter={isCase ? (e) => onCaseHover(e, s.doc_id) : undefined}
                        onMouseLeave={isCase ? () => setHover(null) : undefined}
                      >
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
                    );
                  })}
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
