"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Doc = { doc_id: string; doc_type: string; text: string; metadata: Record<string, unknown> };
type Hit = Doc & { similarity_score: number; distance: number };

const TYPE_LABELS: Record<string, string> = {
  case: "케이스",
  process: "공정",
  production: "생산",
  feedstock: "반제품",
  rule: "룰",
  doc: "문서",
  unknown: "기타",
};
const TYPE_COLORS: Record<string, string> = {
  case: "#185FA5",
  process: "#3B6D11",
  production: "#854F0B",
  feedstock: "#BA7517",
  rule: "#A32D2D",
  doc: "#5B5A55",
  unknown: "#756F61",
};

const PAGE_SIZE = 20;

export default function RagPage() {
  const [types, setTypes] = useState<Record<string, number> | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const [data, setData] = useState<{ total: number; items: Doc[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<Hit[] | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    api.ragTypes().then(setTypes).catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    api
      .ragList({
        doc_type: filter === "all" ? undefined : filter,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      })
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [filter, page]);

  const runSearch = async () => {
    if (!searchQ.trim()) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    setError("");
    try {
      const r = await api.ragSearch(searchQ, 8, filter === "all" ? undefined : filter);
      setSearchResults(r.hits);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQ("");
    setSearchResults(null);
  };

  const totalDocs = types ? Object.values(types).reduce((a, b) => a + b, 0) : 0;
  const filterChips: [string, string, number][] = [
    ["all", "전체", totalDocs],
    ...Object.entries(types ?? {}).map(([k, v]) => [k, TYPE_LABELS[k] ?? k, v] as [string, string, number]),
  ];

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const listItems = searchResults ?? data?.items ?? [];

  return (
    <>
      <div className="kb-stat-grid">
        <div className="stat-card accent">
          <div className="stat-label">총 인덱싱 문서</div>
          <div className="stat-val">
            {totalDocs}<span className="stat-unit">건</span>
          </div>
        </div>
        {Object.entries(types ?? {}).slice(0, 3).map(([k, v]) => (
          <div key={k} className="stat-card" style={{ borderLeft: `3px solid ${TYPE_COLORS[k] ?? "#756F61"}` }}>
            <div className="stat-label">{TYPE_LABELS[k] ?? k}</div>
            <div className="stat-val" style={{ color: TYPE_COLORS[k] ?? "#1F1E1B" }}>
              {v}<span className="stat-unit">건</span>
            </div>
          </div>
        ))}
      </div>

      <div className="kb-filter-bar">
        <span className="kb-filter-label">문서 타입</span>
        {filterChips.map(([v, l, c]) => (
          <button
            key={v}
            className={`kb-filter-chip ${filter === v ? "active" : ""}`}
            onClick={() => { setFilter(v); setPage(0); clearSearch(); }}
          >
            {l} <span style={{ opacity: 0.7 }}>{c}</span>
          </button>
        ))}
        <input
          className="kb-search"
          type="text"
          placeholder="벡터 유사도 검색 (Enter)"
          value={searchQ}
          onChange={(e) => setSearchQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
        />
        {searchResults && (
          <button className="btn-secondary" style={{ padding: "4px 10px", fontSize: 11 }} onClick={clearSearch}>
            검색 해제
          </button>
        )}
      </div>

      {error && (
        <div className="card" style={{ padding: 14, marginBottom: 14, color: "#A32D2D", fontSize: 12 }}>
          <i className="ti ti-alert-octagon" style={{ marginRight: 6 }} />
          {error}
        </div>
      )}

      {(loading || searching) && (
        <div style={{ fontSize: 12, color: "var(--color-text-secondary)", padding: 14 }}>
          {searching ? "벡터 검색 중..." : "불러오는 중..."}
        </div>
      )}

      {!loading && !searching && listItems.length === 0 && (
        <div className="card">
          <div className="kb-empty">
            <i className="ti ti-database-off" style={{ fontSize: 28, color: "var(--color-text-secondary)", marginBottom: 8, display: "block" }} />
            {searchResults ? "검색 결과가 없습니다." : "문서가 없습니다."}
          </div>
        </div>
      )}

      {!loading && !searching && listItems.map((doc) => {
        const isHit = "similarity_score" in doc;
        const hit = doc as Hit;
        const color = TYPE_COLORS[doc.doc_type] ?? "#756F61";
        const isOpen = expanded === doc.doc_id;
        return (
          <div key={doc.doc_id + (isHit ? "-hit" : "")} className="kb-card" style={{ borderLeftColor: color }}>
            <div
              className="kb-card-head"
              style={{ cursor: "pointer" }}
              onClick={() => setExpanded(isOpen ? null : doc.doc_id)}
            >
              <span className="kb-card-id">{doc.doc_id}</span>
              <span
                style={{
                  fontSize: 10,
                  padding: "2px 7px",
                  borderRadius: 4,
                  background: color + "20",
                  color,
                  border: `0.5px solid ${color}`,
                  fontWeight: 500,
                }}
              >
                {TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
              </span>
              {isHit && (
                <span style={{ fontSize: 11, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>
                  유사도 {(hit.similarity_score * 100).toFixed(0)}%
                </span>
              )}
              <div className="kb-card-meta">
                <i className={`ti ti-chevron-${isOpen ? "up" : "down"}`} />
              </div>
            </div>
            {isOpen ? (
              <div className="kb-card-body">
                <div className="kb-section">
                  <span className="kb-section-label">본문</span>
                  <div
                    className="kb-section-body"
                    style={{
                      fontSize: 12,
                      whiteSpace: "pre-wrap",
                      maxHeight: 400,
                      overflowY: "auto",
                      lineHeight: 1.55,
                      fontFamily: "var(--font-sans)",
                    }}
                  >
                    {doc.text || <span style={{ color: "var(--color-text-secondary)" }}>본문 없음</span>}
                  </div>
                </div>
                {Object.keys(doc.metadata).length > 0 && (
                  <div className="kb-section">
                    <span className="kb-section-label">메타데이터</span>
                    <div style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)", whiteSpace: "pre-wrap" }}>
                      {JSON.stringify(doc.metadata, null, 2)}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ padding: "10px 16px", fontSize: 12, color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
                {(doc.text || "").slice(0, 140)}
                {doc.text && doc.text.length > 140 ? "…" : ""}
              </div>
            )}
          </div>
        );
      })}

      {!searchResults && data && data.total > PAGE_SIZE && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginTop: 16 }}>
          <button
            className="btn-secondary"
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            style={{ opacity: page === 0 ? 0.5 : 1 }}
          >
            ← 이전
          </button>
          <span style={{ fontSize: 12, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>
            {page + 1} / {totalPages}
          </span>
          <button
            className="btn-secondary"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            style={{ opacity: page >= totalPages - 1 ? 0.5 : 1 }}
          >
            다음 →
          </button>
        </div>
      )}
    </>
  );
}
