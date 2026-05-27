"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type CaseDetail = {
  case_id: string;
  season: string;
  target_cfpp: number;
  blend_components: Record<string, number>;
  key_metrics: Record<string, number | string>;
};

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

const SEASON_LABEL: Record<string, string> = { winter: "동절기", deep_winter: "혹한기" };

const SCENARIO_LABEL: Record<string, string> = {
  min_cost: "비용 최소",
  balanced: "균형",
  safe: "안전 우선",
};

const SCENARIO_COLOR: Record<string, { bg: string; fg: string; border: string }> = {
  min_cost: { bg: "#E6F1FB", fg: "#0C447C", border: "#4A9AD4" },
  balanced: { bg: "#FAEEDA", fg: "#854F0B", border: "#EF9F27" },
  safe: { bg: "#EAF3DE", fg: "#2A5A08", border: "#7BC23A" },
};

const BLEND_CODE: Record<string, string> = {
  lgo: "LGO",
  hgo: "HGO",
  lco: "LCO",
  kero: "Kero",
  biodiesel: "Bio",
};

function formatDate(iso: string) {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return iso;
  }
}

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

  return (
    <div className="case-tip" style={{ left, top }}>
      {blend.length > 0 && (
        <>
          <div className="case-tip-section">블렌딩 구성 (%)</div>
          <table>
            <thead>
              <tr>{blend.map(([k]) => <th key={k}>{BLEND_CODE[k] ?? k.toUpperCase()}</th>)}</tr>
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

export default function JournalPage() {
  const [batches, setBatches] = useState<Batch[] | null>(null);
  const [error, setError] = useState<string>("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [caseCache, setCaseCache] = useState<Record<string, CaseDetail>>({});
  const [hover, setHover] = useState<{ c: CaseDetail; x: number; y: number } | null>(null);
  const PAGE_SIZE = 10;

  useEffect(() => {
    api
      .listBatches({ limit: 200 })
      .then((rows) => setBatches(rows as Batch[]))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const onHover = async (e: React.MouseEvent<HTMLElement>, caseId: string) => {
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
      // ignore
    }
  };

  if (error) {
    return (
      <div className="card" style={{ padding: 14, color: "#A32D2D", fontSize: 12 }}>
        <i className="ti ti-alert-octagon" style={{ marginRight: 6 }} />
        {error}
      </div>
    );
  }
  if (!batches) {
    return (
      <div style={{ padding: 14, fontSize: 12, color: "var(--color-text-secondary)" }}>
        불러오는 중...
      </div>
    );
  }

  const total = batches.length;
  const q = search.toLowerCase().trim();
  const filtered = batches.filter((b) => {
    if (!q) return true;
    const hay = (b.log_id + " " + b.season + " " + (b.selected_scenario ?? "")).toLowerCase();
    return hay.includes(q);
  });

  return (
    <>
      {hover && <CaseTooltip c={hover.c} x={hover.x} y={hover.y} />}
      <div className="kb-stat-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="stat-card accent">
          <div className="stat-label">총 배합 일지</div>
          <div className="stat-val">
            {total}<span className="stat-unit">건</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">실측 입력 완료</div>
          <div className="stat-val">
            {batches.filter((b) => b.actual_cfpp != null || b.actual_wafi != null).length}
            <span className="stat-unit">건</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">시나리오 채택 완료</div>
          <div className="stat-val">
            {batches.filter((b) => b.selected_scenario).length}
            <span className="stat-unit">건</span>
          </div>
        </div>
      </div>

      <div className="kb-filter-bar">
        <span className="kb-filter-label">검색</span>
        <input
          className="kb-search"
          type="text"
          placeholder="로그 ID, 계절, 시나리오 라벨로 검색..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
        />
        <span className="kb-count">
          {filtered.length}/{total} 건
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="card">
          <div className="kb-empty">
            <i
              className="ti ti-book-2"
              style={{ fontSize: 28, color: "var(--color-text-secondary)", marginBottom: 8, display: "block" }}
            />
            {batches.length === 0
              ? "아직 기록된 배합 일지가 없습니다. 신규 판단을 실행하면 여기 표시됩니다."
              : "조건에 맞는 배합 일지가 없습니다."}
          </div>
        </div>
      ) : (
        <>
          {filtered
            .slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
            .map((b) => <BatchCard key={b.log_id} b={b} onHover={onHover} setHover={setHover} />)}
          {filtered.length > PAGE_SIZE && (
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
                {page + 1} / {Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))}
              </span>
              <button
                className="btn-secondary"
                disabled={(page + 1) * PAGE_SIZE >= filtered.length}
                onClick={() => setPage((p) => p + 1)}
                style={{ opacity: (page + 1) * PAGE_SIZE >= filtered.length ? 0.5 : 1 }}
              >
                다음 →
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}

function BatchCard({
  b,
  onHover,
  setHover,
}: {
  b: Batch;
  onHover: (e: React.MouseEvent<HTMLElement>, caseId: string) => void;
  setHover: (v: null) => void;
}) {
  const blendEntries = Object.entries(b.blend_components || {});
  const scenarioLabel = b.selected_scenario ? SCENARIO_LABEL[b.selected_scenario] ?? b.selected_scenario : "—";
  const scColor = b.selected_scenario
    ? SCENARIO_COLOR[b.selected_scenario]
    : { bg: "var(--color-background-secondary)", fg: "var(--color-text-secondary)", border: "var(--color-border-secondary)" };
  const marginText = b.margin_to_target != null
    ? `${b.margin_to_target >= 0 ? "+" : ""}${b.margin_to_target.toFixed(1)}°C`
    : "—";

  return (
    <div className="kb-card" style={{ borderLeftColor: "#BA7517" }}>
      <div className="kb-card-head">
        <span className="kb-card-id">{b.log_id}</span>
        <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
          {SEASON_LABEL[b.season] ?? b.season}
        </span>
        <span
          style={{
            fontSize: 10,
            padding: "2px 7px",
            borderRadius: 4,
            background: scColor.bg,
            color: scColor.fg,
            border: `0.5px solid ${scColor.border}`,
            fontWeight: 500,
          }}
        >
          {scenarioLabel}
        </span>
        <div className="kb-card-meta">
          <span style={{ fontFamily: "var(--font-mono)" }}>{formatDate(b.created_at)}</span>
        </div>
      </div>
      <div className="kb-card-body">
        <div className="kb-section">
          <span className="kb-section-label">블렌딩</span>
          <div className="kb-section-body">
            <div className="kb-comp-line">
              {blendEntries.map(([k, v], i, arr) => (
                <span key={k}>
                  {BLEND_CODE[k] ?? k.toUpperCase()}{" "}
                  <strong style={{ color: "var(--color-text-primary)" }}>
                    {(v * 100).toFixed(1)}%
                  </strong>
                  {i < arr.length - 1 && " ·"}
                </span>
              ))}
            </div>
          </div>
        </div>
        <div className="kb-section">
          <span className="kb-section-label">CFPP · WAFI</span>
          <div className="kb-section-body">
            <div className="kb-metrics-line">
              <span>목표 <span className="v" style={{ color: "#185FA5" }}>{b.target_cfpp.toFixed(1)}°C</span></span>
              <span>베이스라인 <span className="v" style={{ color: "#185FA5" }}>{b.predicted_cfpp_baseline.toFixed(1)}°C</span></span>
              {b.predicted_cfpp_after_wafi != null && (
                <span>WAFI 후 예측 <span className="v" style={{ color: "#854F0B" }}>{b.predicted_cfpp_after_wafi.toFixed(1)}°C</span></span>
              )}
              {b.selected_wafi_ppm != null && (
                <span>WAFI <span className="v" style={{ color: "#BA7517" }}>{b.selected_wafi_ppm.toFixed(0)} ppm ({b.selected_wafi_type ?? "-"})</span></span>
              )}
              <span>마진 <span className="v" style={{ color: b.margin_to_target != null && b.margin_to_target >= 0 ? "#3B6D11" : "#A32D2D" }}>{marginText}</span></span>
            </div>
          </div>
        </div>
        <div className="kb-section">
          <span className="kb-section-label">실측</span>
          <div className="kb-section-body">
            <div className="kb-metrics-line">
              <span>
                CFPP 실측값{" "}
                <span className="v" style={{ color: b.actual_cfpp != null ? "#854F0B" : "var(--color-text-secondary)" }}>
                  {b.actual_cfpp != null ? `${b.actual_cfpp.toFixed(1)}°C` : "—"}
                </span>
                {b.actual_cfpp != null && (() => {
                  const pred = b.predicted_cfpp_after_wafi ?? b.predicted_cfpp_baseline;
                  const diff = b.actual_cfpp - pred;
                  return (
                    <span style={{ marginLeft: 4, color: "var(--color-text-secondary)" }}>
                      (예측차이 {diff >= 0 ? "+" : ""}{diff.toFixed(1)}°C)
                    </span>
                  );
                })()}
              </span>
              <span>
                WAFI 실투입{" "}
                <span className="v" style={{ color: b.actual_wafi != null ? "#BA7517" : "var(--color-text-secondary)" }}>
                  {b.actual_wafi != null ? `${b.actual_wafi.toFixed(0)} ppm` : "—"}
                </span>
                {b.actual_wafi != null && b.selected_wafi_ppm != null && (() => {
                  const diff = b.actual_wafi - b.selected_wafi_ppm;
                  return (
                    <span style={{ marginLeft: 4, color: "var(--color-text-secondary)" }}>
                      (예측차이 {diff >= 0 ? "+" : ""}{diff.toFixed(0)} ppm)
                    </span>
                  );
                })()}
              </span>
            </div>
          </div>
        </div>
        {b.similar_case_ids.length > 0 && (
          <div className="kb-section">
            <span className="kb-section-label">유사 사례</span>
            <div className="kb-tag-list">
              {b.similar_case_ids.map((id) => (
                <span
                  key={id}
                  className="kb-tag"
                  style={{ cursor: "help" }}
                  onMouseEnter={(e) => onHover(e, id)}
                  onMouseLeave={() => setHover(null)}
                >
                  {id}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
