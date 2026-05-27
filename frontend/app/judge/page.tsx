"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { DecisionBadge } from "@/components/badge";
import { api } from "@/lib/api";
import type { JudgeRequest, JudgeResponse, Season, TankHistory, WafiType, SimilarCase } from "@/lib/types";

const CHECK_PRIORITY_LABELS: Record<string, string> = {
  retest: "검사 재확인",
  tank_history: "탱크 이력 확인",
  blend_ratio: "블렌딩 비율 재검증",
  additive_dose: "첨가제 투입량 조정",
  process_condition: "공정 조건 점검",
};

type Step = "input" | "loading" | "result" | "error";

type NumKey =
  | "lgo" | "hgo" | "lco" | "kero" | "bio"
  | "cp" | "pp" | "density"
  | "nPar1015" | "nPar1620" | "nPar21" | "aromatic" | "sulfur" | "cetane"
  | "targetCfpp";

type FormState = Record<NumKey, string> & {
  priority: "cost" | "balanced" | "safe";
  season: Season;
  tankHistory: TankHistory;
  wafiType: WafiType;
};

const INITIAL: FormState = {
  lgo: "50", hgo: "12", lco: "15", kero: "20", bio: "3",
  cp: "-8", pp: "-10", density: "0.845",
  nPar1015: "10.5", nPar1620: "9.4", nPar21: "2.3",
  aromatic: "24.5", sulfur: "8.5", cetane: "49.1",
  wafiType: "A",
  targetCfpp: "-23",
  priority: "balanced", season: "deep_winter", tankHistory: "clean",
};

const num = (v: string) => {
  const n = parseFloat(v);
  return isNaN(n) ? 0 : n;
};

const FIELDS: [NumKey, string, string][] = [
  ["lgo", "LGO (경질 경유)", "%"],
  ["hgo", "HGO (중질 경유)", "%"],
  ["lco", "LCO (접촉분해 경유)", "%"],
  ["kero", "케로신", "%"],
  ["bio", "바이오디젤", "%"],
];

// [key, label, unit, step, allowNegative]
const PROP_FIELDS: [NumKey, string, string, number, boolean][] = [
  ["cp", "Cloud Point (참고용)", "°C", 1, true],
  ["pp", "Pour Point (참고용)", "°C", 1, true],
  ["density", "밀도 (15°C)", "g/cm³", 0.001, false],
  ["nPar1015", "n-파라핀 C10–C15", "wt%", 0.1, false],
  ["nPar1620", "n-파라핀 C16–C20", "wt%", 0.1, false],
  ["nPar21", "n-파라핀 C21+", "wt%", 0.1, false],
  ["aromatic", "방향족 함량", "wt%", 0.1, false],
  ["sulfur", "황분", "ppm", 0.1, false],
  ["cetane", "세탄 지수", "", 0.1, false],
];

const SCEN_BASE: Record<string, { label: string; color: string }> = {
  min_cost: { label: "비용 최소", color: "#185FA5" },
  balanced: { label: "균형", color: "#BA7517" },
  safe: { label: "안전 우선", color: "#3B6D11" },
};

// Maps form priority (cost/balanced/safe) -> scenario label key (min_cost/balanced/safe)
const PRIORITY_TO_LABEL: Record<FormState["priority"], string> = {
  cost: "min_cost",
  balanced: "balanced",
  safe: "safe",
};

function priorityToBackend(p: FormState["priority"]): JudgeRequest["priority"] {
  return p === "cost" ? "cost" : p === "safe" ? "safety" : "balance";
}

function buildRequest(form: FormState): JudgeRequest {
  const sum = num(form.lgo) + num(form.hgo) + num(form.lco) + num(form.kero) + num(form.bio);
  const f = (v: string) => (sum > 0 ? num(v) / sum : 0);
  return {
    blend_components: {
      lgo: f(form.lgo),
      hgo: f(form.hgo),
      lco: f(form.lco),
      kero: f(form.kero),
      biodiesel: f(form.bio),
    },
    key_metrics: {
      density_15c: num(form.density) * 1000, // g/cm³ -> kg/m³
      n_paraffin_c10_c15: num(form.nPar1015),
      n_paraffin_c16_c20: num(form.nPar1620),
      n_paraffin_c21_plus: num(form.nPar21),
      aromatic_content: num(form.aromatic),
      sulfur_ppm: num(form.sulfur),
      cetane_index: num(form.cetane),
      wafi_type: form.wafiType,
      wafi_ppm: 0,
    },
    target_cfpp: num(form.targetCfpp),
    season: form.season,
    tank_history_flag: form.tankHistory,
    priority: priorityToBackend(form.priority),
  };
}

function CaseTooltip({ c, x, y }: { c: SimilarCase; x: number; y: number }) {
  const cols: { label: string; value: string }[] = [];
  if (c.target_cfpp != null) cols.push({ label: "CFPP", value: c.target_cfpp.toFixed(1) + " °C" });
  if (c.key_metrics?.cfpp != null) cols.push({ label: "실측 CFPP", value: Number(c.key_metrics.cfpp).toFixed(1) + " °C" });
  if (c.key_metrics?.wafi_type) cols.push({ label: "WAFI 종류", value: String(c.key_metrics.wafi_type) });
  if (c.key_metrics?.wafi_ppm != null) cols.push({ label: "WAFI 투입량", value: Number(c.key_metrics.wafi_ppm).toFixed(0) + " ppm" });
  if (c.season) {
    const seasonLabel: Record<string, string> = { winter: "동절기", deep_winter: "혹한기" };
    cols.push({ label: "계절", value: seasonLabel[c.season] ?? c.season });
  }

  const blend = c.blend_components ? Object.entries(c.blend_components) : [];

  // Clamp position to viewport (assume tooltip ~ 380×170)
  const TIP_W = 380, TIP_H = 170, PAD = 8;
  const left = Math.min(Math.max(x, PAD), window.innerWidth - TIP_W - PAD);
  const top = Math.min(y + 10, window.innerHeight - TIP_H - PAD);

  return (
    <div className="case-tip" style={{ left, top }}>
      {blend.length > 0 && (
        <>
          <div className="case-tip-section">블렌딩 구성 (%)</div>
          <table>
            <thead><tr>{blend.map(([k]) => <th key={k}>{k.toUpperCase()}</th>)}</tr></thead>
            <tbody><tr>{blend.map(([k, v]) => (
              <td key={k}>{typeof v === "number" ? (v * 100).toFixed(1) : String(v)}</td>
            ))}</tr></tbody>
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

export default function JudgePage() {
  const [step, setStep] = useState<Step>("input");
  const [selectedLabel, setSelectedLabel] = useState<string>("balanced");
  const [adopted, setAdopted] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(INITIAL);
  const [result, setResult] = useState<JudgeResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [hover, setHover] = useState<{ c: SimilarCase; x: number; y: number } | null>(null);
  const router = useRouter();

  const total = num(form.lgo) + num(form.hgo) + num(form.lco) + num(form.kero) + num(form.bio);
  const ok = total === 100;

  const NON_NEG: NumKey[] = [
    "lgo", "hgo", "lco", "kero", "bio",
    "density", "nPar1015", "nPar1620", "nPar21",
    "aromatic", "sulfur", "cetane",
  ];
  const update = (k: NumKey, v: string) => {
    if (NON_NEG.includes(k) && v.startsWith("-")) return;
    setForm({ ...form, [k]: v });
  };

  const submit = async () => {
    setStep("loading");
    setError("");
    setAdopted(null);
    setSelectedLabel("balanced");
    try {
      const r = await api.judge(buildRequest(form));
      setResult(r);
      setStep("result");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStep("error");
    }
  };

  if (step === "loading") {
    return (
      <div className="loading-spinner">
        <div className="spinner" />
        <div style={{ fontSize: 14, color: "var(--color-text-secondary)" }}>AI 판단 분석 중...</div>
        <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
          XGBoost 예측 + RAG 검색 + 경험치 매칭
        </div>
      </div>
    );
  }

  if (step === "error") {
    return (
      <div className="card">
        <div className="judge-header">
          <i className="ti ti-alert-octagon" style={{ fontSize: 24, color: "#A32D2D", marginTop: 3 }} />
          <div>
            <div style={{ fontSize: 15, fontWeight: 500, color: "#A32D2D", marginBottom: 5 }}>
              백엔드 호출 실패
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)", whiteSpace: "pre-wrap" }}>
              {error}
            </div>
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 8 }}>
              백엔드가 http://localhost:8000 에서 실행 중인지 확인하세요.
            </div>
          </div>
        </div>
        <div className="bottom-actions" style={{ padding: 14 }}>
          <button className="btn-secondary" onClick={() => setStep("input")}>← 다시 입력</button>
          <button className="btn-primary" onClick={submit}>다시 시도</button>
        </div>
      </div>
    );
  }

  if (step === "result" && result) {

    return (
      <>
        {hover && <CaseTooltip c={hover.c} x={hover.x} y={hover.y} />}
        <div className="pred-cfpp-banner" style={{ marginBottom: 14 }}>
          <i className="ti ti-temperature" style={{ fontSize: 16, color: "#185FA5", flexShrink: 0 }} />
          <span className="pred-cfpp-label">현재 Batch의 예측 CFPP (베이스라인)</span>
          <span style={{ fontSize: 12, color: "var(--color-text-secondary)", margin: "0 2px" }}>:</span>
          <span className="pred-cfpp-val">{result.predicted_cfpp_baseline.toFixed(1)}°C</span>
        </div>
        <div className="scen-section-label">WAFI 추천 시나리오</div>
        <div className="scen-grid">
          {result.scenarios.map((sc) => {
            const base = SCEN_BASE[sc.label] ?? { label: sc.label, color: "#185FA5" };
            const isRec = sc.label === PRIORITY_TO_LABEL[form.priority];
            const isSelected = sc.label === selectedLabel;
            const met = sc.margin_to_target >= 0;
            return (
              <div
                key={sc.label}
                className={`scen-card ${isRec ? "rec" : ""} ${isSelected ? "selected" : ""}`}
                onClick={() => setSelectedLabel(sc.label)}
                style={{ cursor: "pointer" }}
              >
                {isRec && <span className="rec-badge">추천</span>}
                {isSelected && (
                  <span
                    style={{
                      position: "absolute",
                      top: -9,
                      right: 10,
                      background: "#3B6D11",
                      color: "#fff",
                      fontSize: 10,
                      padding: "2px 7px",
                      borderRadius: 10,
                      fontWeight: 500,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 3,
                    }}
                  >
                    <i className="ti ti-check" style={{ fontSize: 11 }} />선택됨
                  </span>
                )}
                <div style={{ fontSize: 11, fontWeight: 600, color: met ? "#3B6D11" : "#A32D2D", marginBottom: 6, display: "flex", alignItems: "center", gap: 4 }}>
                  <i className={`ti ${met ? "ti-circle-check" : "ti-circle-x"}`} style={{ fontSize: 13 }} />
                  {met ? "목표 달성" : "목표 미달성"}
                </div>
                <div className="scen-type" style={{ color: base.color }}>
                  {base.label}{isRec ? " (권장)" : ""}
                </div>
                <div className="scen-wafi">
                  {sc.wafi_ppm}
                  <span className="scen-unit">ppm ({sc.wafi_type})</span>
                </div>
                <div className="scen-cfpp">
                  예상 CFPP:{" "}
                  <span style={{ fontFamily: "var(--font-mono)", color: base.color }}>
                    {sc.predicted_cfpp.toFixed(1)}°C
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 4, textAlign: "right" }}>
                  마진 {sc.margin_to_target >= 0 ? "+" : ""}{sc.margin_to_target.toFixed(1)}°C
                </div>
                <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: 8, paddingTop: 8, borderTop: "0.5px dashed var(--color-border-tertiary)", lineHeight: 1.4 }}>
                  {sc.rationale}
                </div>
              </div>
            );
          })}
        </div>
        <div className="two-col">
          <div className="card">
            <div className="card-header"><span className="card-title">확인 우선순위</span></div>
            <div style={{ padding: 14 }}>
              <div className="priority-items">
                {result.check_priority.length === 0 ? (
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>—</div>
                ) : (
                  result.check_priority.map((p, i) => (
                    <div key={i} className="priority-item">
                      <div className="priority-num">{i + 1}</div>
                      <div className="priority-text">{CHECK_PRIORITY_LABELS[p] ?? p}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><span className="card-title">유사 사례 Top {result.similar_cases.length}</span></div>
            <div style={{ padding: 14 }}>
              <div className="similar-list">
                {result.similar_cases.length === 0 ? (
                  <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>유사 사례 없음</div>
                ) : (
                  result.similar_cases.map((c) => (
                    <div
                      key={c.case_id}
                      className="similar-row"
                      style={{ flexDirection: "column", alignItems: "stretch", gap: 4, padding: "10px 0" }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <div className="similar-left">
                          <span
                            className="case-id case-hover"
                            style={{ textDecoration: "underline dotted", textUnderlineOffset: 2 }}
                            onMouseEnter={(e) => {
                              const r = (e.target as HTMLElement).getBoundingClientRect();
                              setHover({ c, x: r.left, y: r.bottom });
                            }}
                            onMouseLeave={() => setHover(null)}
                          >
                            {c.case_id}
                          </span>
                        </div>
                        <div className="similar-right">
                          <span className="sim-pct">유사도 {(c.similarity_score * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                      {c.rule_summary && (
                        <div style={{ fontSize: 11, color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
                          {c.rule_summary}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="bottom-actions">
          <button className="btn-secondary" onClick={() => setStep("input")}>← 다시 입력</button>
          <button
            className="btn-primary"
            onClick={async () => {
              const sc = result.scenarios.find((s) => s.label === selectedLabel);
              const label = SCEN_BASE[selectedLabel]?.label ?? selectedLabel;
              const baseMsg = sc
                ? `${label} 시나리오 채택 — WAFI ${sc.wafi_ppm} ppm (${sc.wafi_type}), 예상 CFPP ${sc.predicted_cfpp.toFixed(1)}°C`
                : `${label} 시나리오 채택`;
              try {
                const created = await api.createDecisionLog({
                  input: buildRequest(form),
                  ai_recommendation: result,
                  selected_scenario: selectedLabel,
                });
                // remember the new log_id so subsequent outcome edits stay in sync
                setResult({ ...result, log_id: created.log_id });
                setAdopted(`${baseMsg} (DB 저장 완료 · ${created.log_id})`);
              } catch (e) {
                setAdopted(baseMsg + ` (DB 저장 실패: ${e instanceof Error ? e.message : String(e)})`);
              }
            }}
          >
            시나리오 선택
          </button>
          <button
            className="btn-secondary"
            style={{ color: "#185FA5", borderColor: "#B5D4F4" }}
            onClick={() => {
              const ctx = {
                batchId: "D-" + new Date().toISOString().slice(2, 16).replace(/\D/g, "").slice(0, 6),
                decision: result.decision,
                season: form.season,
                targetCfpp: num(form.targetCfpp),
                blend: {
                  lgo: num(form.lgo),
                  hgo: num(form.hgo),
                  lco: num(form.lco),
                  kero: num(form.kero),
                  bio: num(form.bio),
                },
                baselineCfpp: result.predicted_cfpp_baseline,
              };
              sessionStorage.setItem("consult_context", JSON.stringify(ctx));
              router.push("/consult");
            }}
          >
            AI 상담 요청
          </button>
        </div>
        {adopted && (
          <div
            style={{
              marginTop: 10,
              padding: "8px 12px",
              fontSize: 12,
              color: "#3B6D11",
              background: "#F4FBE8",
              border: "0.5px solid #97C459",
              borderRadius: "var(--border-radius-md)",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <i className="ti ti-check" style={{ fontSize: 14 }} />
            {adopted}
          </div>
        )}
      </>
    );
  }

  return (
    <>
      <div className="judg-two-col">
        <div className="judg-col">
          <div className="form-section">
            <div
              className="form-section-title"
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
            >
              <span>블렌딩 구성</span>
              <button
                type="button"
                className="btn-secondary"
                title="PoC에서 구현하지 않음"
                style={{ fontSize: 11, padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                <i className="ti ti-clipboard-text" style={{ fontSize: 13 }} />
                제품 배합 계획 불러오기
              </button>
            </div>
            <div className="fields-wrap">
              {FIELDS.map(([k, label, unit]) => (
                <div key={k} className="field">
                  <label>
                    {label} <span style={{ color: "var(--color-text-secondary)" }}>({unit})</span>
                  </label>
                  <input
                    type="number"
                    step={1}
                    min={0}
                    value={form[k]}
                    onChange={(e) => update(k, e.target.value)}
                  />
                </div>
              ))}
            </div>
            <div className="blend-total">
              <span className="blend-total-label">합계</span>
              <span className={`blend-total-val ${ok ? "blend-ok" : "blend-warn"}`}>
                {total} %{ok ? " ✓" : " · 100%가 되어야 합니다"}
              </span>
            </div>
          </div>

          <div className="form-section" style={{ marginTop: 12 }}>
            <div
              className="form-section-title"
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
            >
              <span>판단 조건</span>
              <button
                type="button"
                className="btn-secondary"
                title="PoC에서 구현하지 않음"
                style={{ fontSize: 11, padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                <i className="ti ti-calendar-event" style={{ fontSize: 13 }} />
                제품 운영 계획 불러오기
              </button>
            </div>
            <div className="field">
              <label>
                목표 CFPP <span style={{ color: "var(--color-text-secondary)" }}>(°C)</span>
              </label>
              <input
                type="number"
                value={form.targetCfpp}
                onChange={(e) => update("targetCfpp", e.target.value)}
              />
            </div>
            <div className="field">
              <label>계절</label>
              <select
                value={form.season}
                onChange={(e) => setForm({ ...form, season: e.target.value as Season })}
              >
                <option value="deep_winter">혹한기</option>
                <option value="winter">동절기</option>
              </select>
            </div>
            <div className="field">
              <label>탱크 이력</label>
              <select
                value={form.tankHistory}
                onChange={(e) => setForm({ ...form, tankHistory: e.target.value as TankHistory })}
              >
                <option value="clean">잔류물 없음</option>
                <option value="recent_change">최근 전환</option>
                <option value="mixed">혼합물 잔류</option>
              </select>
            </div>
            <div className="field">
              <label>WAFI 첨가제 종류 <span style={{ color: "var(--color-text-secondary)" }}>(현재 사용 중)</span></label>
              <select
                value={form.wafiType}
                onChange={(e) => setForm({ ...form, wafiType: e.target.value as WafiType })}
              >
                <option value="A">A 타입</option>
                <option value="B">B 타입</option>
                <option value="C">C 타입</option>
                <option value="none">없음</option>
              </select>
            </div>
          </div>
        </div>

        <div className="judg-col">
          <div className="form-section stretch">
            <div
              className="form-section-title"
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
            >
              <span>주요 성상</span>
              <button
                type="button"
                className="btn-secondary"
                title="PoC에서 구현하지 않음"
                style={{ fontSize: 11, padding: "4px 10px", display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                <i className="ti ti-database-import" style={{ fontSize: 13 }} />
                RTDB 분석값 불러오기
              </button>
            </div>
            <div style={{ fontSize: 11, color: "var(--color-text-secondary)", marginTop: -8, marginBottom: 10 }}>
              * CP, PP는 모델 입력에 사용되지 않습니다 (운영 참고용)
            </div>
            <div className="fields-wrap">
              {PROP_FIELDS.map(([k, label, unit, step, allowNeg]) => (
                <div key={k} className="field">
                  <label>
                    {label}{" "}
                    {unit && <span style={{ color: "var(--color-text-secondary)" }}>({unit})</span>}
                  </label>
                  <input
                    type="number"
                    step={step}
                    {...(!allowNeg ? { min: 0 } : {})}
                    value={form[k]}
                    onChange={(e) => update(k, e.target.value)}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      <div className="bottom-actions" style={{ justifyContent: "flex-end" }}>
        <button className="btn-secondary" onClick={() => setForm(INITIAL)}>초기화</button>
        <button className="btn-primary" onClick={submit}>AI 판단 요청 →</button>
      </div>
    </>
  );
}
