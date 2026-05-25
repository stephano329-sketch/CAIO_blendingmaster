"use client";

import { useEffect, useState } from "react";
import { DecisionBadge } from "@/components/badge";
import { api } from "@/lib/api";
import { Q2_LABELS, Q3_LABELS, Q4_LABELS, USERS, type Decision } from "@/lib/demo-data";

type KBRow = {
  entry_id: string;
  case_id: string;
  season: string;
  blend_components: Record<string, string>;
  cfpp: number; cp: number; pp: number;
  ai_draft_decision: string | null;
  q1_decision: string;
  q2_reasons: string[]; q3_priorities: string[]; q4_risks: string[];
  q5_memo: string;
  author: string;
  created_at: string;
};

const SEASON_LABEL: Record<string, string> = { winter: "동절기", deep_winter: "혹한기" };

function userLabel(v: string) {
  return USERS.find((u) => u.value === v)?.label ?? v;
}
function userInitial(v: string) {
  return USERS.find((u) => u.value === v)?.initials ?? "?";
}

function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return iso;
  }
}

export default function KBPage() {
  const [filter, setFilter] = useState<"all" | Decision>("all");
  const [search, setSearch] = useState("");
  const [db, setDb] = useState<KBRow[] | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    api
      .listKnowledge({ limit: 200 })
      .then((rows) => setDb(rows as KBRow[]))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return (
      <div className="card" style={{ padding: 14, color: "#A32D2D", fontSize: 12 }}>
        <i className="ti ti-alert-octagon" style={{ marginRight: 6 }} />
        {error}
      </div>
    );
  }

  if (!db) {
    return (
      <div style={{ padding: 14, fontSize: 12, color: "var(--color-text-secondary)" }}>
        불러오는 중...
      </div>
    );
  }

  const total = db.length;
  const cntNormal = db.filter((r) => r.q1_decision === "normal").length;
  const cntCaution = db.filter((r) => r.q1_decision === "caution").length;
  const cntRisk = db.filter((r) => r.q1_decision === "risk").length;

  const q = search.toLowerCase().trim();
  const filtered = db.filter((r) => {
    if (filter !== "all" && r.q1_decision !== filter) return false;
    if (q) {
      const hay = (r.entry_id + " " + r.case_id + " " + r.q5_memo + " " + r.season).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  const filters: [typeof filter, string, number][] = [
    ["all", "전체", total],
    ["normal", "정상", cntNormal],
    ["caution", "주의", cntCaution],
    ["risk", "위험", cntRisk],
  ];

  return (
    <>
      <div className="kb-stat-grid">
        <div className="stat-card accent">
          <div className="stat-label">총 저장된 경험치</div>
          <div className="stat-val">
            {total}<span className="stat-unit">건</span>
          </div>
        </div>
        <div className="stat-card" style={{ borderLeft: "3px solid #7BC23A" }}>
          <div className="stat-label">정상 판단</div>
          <div className="stat-val" style={{ color: "#3B6D11" }}>
            {cntNormal}<span className="stat-unit">건</span>
          </div>
        </div>
        <div className="stat-card" style={{ borderLeft: "3px solid #E89B2A" }}>
          <div className="stat-label">주의 판단</div>
          <div className="stat-val" style={{ color: "#854F0B" }}>
            {cntCaution}<span className="stat-unit">건</span>
          </div>
        </div>
        <div className="stat-card" style={{ borderLeft: "3px solid #E06060" }}>
          <div className="stat-label">위험 판단</div>
          <div className="stat-val" style={{ color: "#A32D2D" }}>
            {cntRisk}<span className="stat-unit">건</span>
          </div>
        </div>
      </div>

      <div className="kb-filter-bar">
        <span className="kb-filter-label">판단 필터</span>
        {filters.map(([v, l, c]) => (
          <button
            key={v}
            className={`kb-filter-chip ${filter === v ? "active" : ""}`}
            onClick={() => setFilter(v)}
          >
            {l} <span style={{ opacity: 0.7 }}>{c}</span>
          </button>
        ))}
        <input
          className="kb-search"
          type="text"
          placeholder="ID, 메모, 시즌으로 검색..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span className="kb-count">
          {filtered.length}/{total} 건
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="card">
          <div className="kb-empty">
            <i
              className="ti ti-database-off"
              style={{ fontSize: 28, color: "var(--color-text-secondary)", marginBottom: 8, display: "block" }}
            />
            조건에 맞는 경험치가 없습니다.
          </div>
        </div>
      ) : (
        filtered.map((r) => <KBCard key={r.entry_id} r={r} />)
      )}
    </>
  );
}

function KBCard({ r }: { r: KBRow }) {
  return (
    <div className={`kb-card kb-${r.q1_decision}`}>
      <div className="kb-card-head">
        <span className="kb-card-id">{r.entry_id}</span>
        <span style={{ fontSize: 11, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>
          {r.case_id}
        </span>
        <DecisionBadge decision={r.q1_decision as Decision} />
        <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
          {SEASON_LABEL[r.season] ?? r.season}
        </span>
        <div className="kb-card-meta">
          <span className="kb-author">
            <span className="kb-author-avatar">{userInitial(r.author)}</span>
            {userLabel(r.author)}
          </span>
          <span style={{ fontFamily: "var(--font-mono)" }}>{formatDate(r.created_at)}</span>
        </div>
      </div>
      <div className="kb-card-body">
        <div className="kb-section">
          <span className="kb-section-label">케이스</span>
          <div className="kb-section-body">
            <div className="kb-comp-line">
              {Object.entries(r.blend_components).map(([k, v], i, arr) => (
                <span key={k}>
                  {k} <strong style={{ color: "var(--color-text-primary)" }}>{v}</strong>
                  {i < arr.length - 1 && " ·"}
                </span>
              ))}
            </div>
            <div className="kb-metrics-line">
              <span>CFPP <span className="v" style={{ color: "#854F0B" }}>{r.cfpp}°C</span></span>
              <span>CP <span className="v" style={{ color: "#185FA5" }}>{r.cp}°C</span></span>
              <span>PP <span className="v" style={{ color: "#185FA5" }}>{r.pp}°C</span></span>
              {r.ai_draft_decision && (
                <span>AI 초안 <DecisionBadge decision={r.ai_draft_decision as Decision} /></span>
              )}
            </div>
          </div>
        </div>
        <div className="kb-section">
          <span className="kb-section-label">판단 근거</span>
          <div className="kb-tag-list">
            {r.q2_reasons.length ? (
              r.q2_reasons.map((c) => (
                <span key={c} className="kb-tag">{Q2_LABELS[c] ?? c}</span>
              ))
            ) : (
              <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>—</span>
            )}
          </div>
        </div>
        <div className="kb-section">
          <span className="kb-section-label">확인 우선순위</span>
          <div className="kb-prio">
            {r.q3_priorities.length ? (
              r.q3_priorities.map((c, i) => (
                <div key={c} className="kb-prio-row">
                  <div className="kb-prio-num">{i + 1}</div>
                  <span>{Q3_LABELS[c] ?? c}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>—</span>
            )}
          </div>
        </div>
        <div className="kb-section">
          <span className="kb-section-label">리스크</span>
          <div className="kb-tag-list">
            {r.q4_risks.length ? (
              r.q4_risks.map((c) => (
                <span key={c} className="kb-tag risk">{Q4_LABELS[c] ?? c}</span>
              ))
            ) : (
              <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>—</span>
            )}
          </div>
        </div>
        <div className="kb-section">
          <span className="kb-section-label">기준 메모</span>
          <div className="kb-memo">
            {r.q5_memo || (
              <span style={{ color: "var(--color-text-secondary)" }}>메모 없음</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
