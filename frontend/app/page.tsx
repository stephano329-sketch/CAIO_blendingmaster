"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

type Stats = { today_batch_count: number; month_judge_count: number; month_saving_man_won: number };
type LogRow = {
  date: string;
  log_id: string;
  pred_cfpp: number;
  wafi_suggested: number;
  actual_cfpp: number | null;
  actual_wafi: number | null;
  decision: string;
  selected_scenario: string | null;
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
type EditField = "cfpp" | "wafi";

const SCENARIO_COLOR: Record<string, string> = {
  min_cost: "#185FA5",
  balanced: "#BA7517",
  safe: "#3B6D11",
};
const SCENARIO_LABEL: Record<string, string> = {
  min_cost: "비용최소",
  balanced: "균형",
  safe: "안전우선",
};

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [logs, setLogs] = useState<LogRow[] | null>(null);
  const [batches, setBatches] = useState<Batch[] | null>(null);
  const [error, setError] = useState<string>("");
  const [editing, setEditing] = useState<{ logId: string; field: EditField } | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [saving, setSaving] = useState(false);

  const refresh = () => {
    Promise.all([api.dashboardStats(), api.dashboardRecentLogs(10), api.listBatches({ limit: 200 })])
      .then(([s, l, b]) => {
        setStats(s);
        setLogs(l);
        setBatches(b as Batch[]);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(() => {
    refresh();
  }, []);

  // ===== Derived analytics =====
  const analytics = useMemo(() => {
    if (!batches) return null;

    const withActual = batches.filter((b) => b.actual_cfpp != null && b.predicted_cfpp_after_wafi != null);
    const mae = withActual.length
      ? withActual.reduce((s, b) => s + Math.abs((b.actual_cfpp as number) - (b.predicted_cfpp_after_wafi as number)), 0) / withActual.length
      : null;

    const withWafiActual = batches.filter((b) => b.actual_wafi != null && b.selected_wafi_ppm != null);
    const wafiSavingPct = withWafiActual.length
      ? (withWafiActual.reduce(
          (s, b) => s + ((b.selected_wafi_ppm as number) - (b.actual_wafi as number)) / Math.max(b.selected_wafi_ppm as number, 1),
          0,
        ) /
          withWafiActual.length) *
        100
      : null;

    const scenarioCounts: Record<string, number> = { min_cost: 0, balanced: 0, safe: 0 };
    batches.forEach((b) => {
      if (b.selected_scenario && b.selected_scenario in scenarioCounts) scenarioCounts[b.selected_scenario]++;
    });
    const scenarioTotal = scenarioCounts.min_cost + scenarioCounts.balanced + scenarioCounts.safe;

    // 14일 CFPP 라인 (날짜순)
    const sorted = [...batches].sort((a, b) => a.created_at.localeCompare(b.created_at));
    const last14 = sorted.slice(-14).map((b) => ({
      date: b.created_at.slice(5, 10),
      log_id: b.log_id,
      pred: b.predicted_cfpp_after_wafi,
      actual: b.actual_cfpp,
      target: b.target_cfpp,
    }));

    // WAFI 막대 (제안 vs 실측)
    const last14Wafi = sorted.slice(-14).map((b) => ({
      date: b.created_at.slice(5, 10),
      suggested: b.selected_wafi_ppm ?? 0,
      actual: b.actual_wafi ?? 0,
    }));

    // 파이프라인 카운트 (오늘 기준)
    const today = new Date().toISOString().slice(0, 10);
    const todays = batches.filter((b) => b.created_at.slice(0, 10) === today);
    const pipeline = {
      judged: todays.length,
      selected: todays.filter((b) => b.selected_scenario != null).length,
      measured: todays.filter((b) => b.actual_cfpp != null).length,
      shipped: todays.filter((b) => b.actual_cfpp != null && b.actual_wafi != null).length,
    };

    // 알림 (목표 미달 / WAFI 과투입)
    const recent = sorted.slice(-30);
    const missTarget = recent.filter((b) => b.actual_cfpp != null && b.actual_cfpp > b.target_cfpp);
    const wafiOver = recent.filter(
      (b) => b.actual_wafi != null && b.selected_wafi_ppm != null && b.actual_wafi - b.selected_wafi_ppm >= 30,
    );

    // AI 인사이트 (간단 룰)
    let insight = "최근 데이터 부족 — 더 많은 batch가 누적되면 인사이트가 생성됩니다.";
    const lcoHeavy = recent.filter((b) => (b.blend_components?.LCO ?? 0) >= 0.3);
    if (lcoHeavy.length >= 3) {
      const cTypeRate =
        lcoHeavy.filter((b) => b.selected_wafi_type === "C").length / lcoHeavy.length;
      if (cTypeRate >= 0.5) {
        insight = `최근 LCO 30% 이상 배치 ${lcoHeavy.length}건 중 ${Math.round(cTypeRate * 100)}%가 WAFI Type C를 채택했습니다.`;
      } else {
        insight = `LCO 30% 이상 배치 ${lcoHeavy.length}건에서 WAFI 타입 분포가 분산되어 있습니다 — 의사결정 패턴 재검토 권장.`;
      }
    } else if (recent.length >= 5 && mae != null) {
      insight = `최근 ${recent.length}건 평균 예측 오차 ${mae.toFixed(2)}°C — 모델 신뢰 구간 안정적.`;
    }

    return {
      mae,
      wafiSavingPct,
      scenarioCounts,
      scenarioTotal,
      last14,
      last14Wafi,
      pipeline,
      missTarget,
      wafiOver,
      insight,
    };
  }, [batches]);

  const startEdit = (logId: string, field: EditField, current: number | null) => {
    setEditing({ logId, field });
    setEditValue(current != null ? String(current) : "");
  };
  const cancelEdit = () => {
    setEditing(null);
    setEditValue("");
  };
  const saveEdit = async () => {
    if (!editing || saving) return;
    const v = parseFloat(editValue);
    if (isNaN(v)) {
      cancelEdit();
      return;
    }
    setSaving(true);
    try {
      const body = editing.field === "cfpp" ? { actual_cfpp: v } : { actual_wafi: v };
      await api.patchOutcome(editing.logId, body);
      cancelEdit();
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      cancelEdit();
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {/* ===== KPI Strip (6 cards) ===== */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
          gap: 10,
          marginBottom: 14,
        }}
      >
        <KpiCard
          label="오늘 처리 Batch"
          value={stats?.today_batch_count ?? "-"}
          unit="건"
          accent
          icon="ti-calendar-stats"
        />
        <KpiCard
          label="이번 달 판단"
          value={stats?.month_judge_count ?? "-"}
          unit="건"
          icon="ti-clipboard-check"
        />
        <KpiCard
          label="이번 달 절감액(추정)"
          value={stats?.month_saving_man_won?.toLocaleString() ?? "-"}
          unit="만원"
          accent
          icon="ti-currency-won"
        />
        <KpiCard
          label="예측 정확도 (MAE)"
          value={analytics?.mae != null ? analytics.mae.toFixed(2) : "-"}
          unit="°C"
          icon="ti-target"
          tone="blue"
          hint="실측 vs 예측 평균오차"
        />
        <KpiCard
          label="WAFI 절감률"
          value={analytics?.wafiSavingPct != null ? analytics.wafiSavingPct.toFixed(1) : "-"}
          unit="%"
          icon="ti-leaf"
          tone={analytics?.wafiSavingPct && analytics.wafiSavingPct > 0 ? "green" : "default"}
          hint="제안 대비 실투입 평균"
        />
        <KpiCard
          label="시나리오 분포"
          icon="ti-chart-pie"
          customBody={
            <ScenarioMiniBar counts={analytics?.scenarioCounts} total={analytics?.scenarioTotal ?? 0} />
          }
        />
      </div>

      {/* ===== Alert + Insight + Pipeline ===== */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1.2fr",
          gap: 10,
          marginBottom: 14,
        }}
      >
        <AlertCard analytics={analytics} />
        <InsightCard insight={analytics?.insight} />
        <PipelineCard pipeline={analytics?.pipeline} />
      </div>

      {/* ===== Chart Grid 2x2 ===== */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
          marginBottom: 14,
        }}
      >
        <ChartCard title="최근 14건 CFPP 예측 vs 실측" subtitle="목표선 대비 모델 적중도">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={analytics?.last14 ?? []} margin={{ top: 10, right: 16, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
              <Tooltip contentStyle={{ fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="target" stroke="#999" strokeDasharray="4 4" name="목표" dot={false} />
              <Line type="monotone" dataKey="pred" stroke="#185FA5" name="예측" dot={{ r: 2 }} />
              <Line type="monotone" dataKey="actual" stroke="#BA7517" name="실측" dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="WAFI 제안 vs 실투입" subtitle="ppm 비교 — 절감 추세">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={analytics?.last14Wafi ?? []} margin={{ top: 10, right: 16, bottom: 0, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip contentStyle={{ fontSize: 11 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="suggested" fill="#185FA5" name="제안" />
              <Bar dataKey="actual" fill="#BA7517" name="실투입" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* ===== 기존 로그 테이블 (인라인 편집) ===== */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">최근 의사결정 로그</span>
          <span className="card-sub">{logs ? `최근 ${logs.length}건` : ""}</span>
        </div>
        {error && (
          <div style={{ padding: 14, fontSize: 12, color: "#A32D2D" }}>
            <i className="ti ti-alert-octagon" style={{ marginRight: 6 }} />
            {error}
          </div>
        )}
        {!error && logs && logs.length === 0 && (
          <div style={{ padding: 24, textAlign: "center", fontSize: 13, color: "var(--color-text-secondary)" }}>
            아직 기록된 의사결정이 없습니다. 신규 판단을 실행하면 여기 표시됩니다.
          </div>
        )}
        {!error && logs && logs.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table className="log-table" style={{ tableLayout: "fixed", width: "100%" }}>
              <colgroup>
                <col style={{ width: 100 }} />
                <col style={{ width: 130 }} />
                <col style={{ width: 100 }} />
                <col style={{ width: 110 }} />
                <col style={{ width: 110 }} />
                <col style={{ width: 150 }} />
                <col style={{ width: 150 }} />
              </colgroup>
              <thead>
                <tr>
                  <th>날짜</th>
                  <th>로그 ID</th>
                  <th>시나리오</th>
                  <th>예측 CFPP</th>
                  <th>WAFI 제안</th>
                  <th className="group-head">결과 · 실측 CFPP</th>
                  <th className="group-head">결과 · WAFI 투입</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.log_id}>
                    <td className="c-muted">{l.date}</td>
                    <td className="mono" style={{ color: "var(--color-text-primary)", fontSize: 11 }}>
                      {l.log_id}
                    </td>
                    <td>
                      {l.selected_scenario ? (
                        <span
                          style={{
                            fontSize: 10,
                            padding: "2px 6px",
                            borderRadius: 3,
                            color: "#fff",
                            background: SCENARIO_COLOR[l.selected_scenario] ?? "#666",
                          }}
                        >
                          {SCENARIO_LABEL[l.selected_scenario] ?? l.selected_scenario}
                        </span>
                      ) : (
                        <span style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>—</span>
                      )}
                    </td>
                    <td className="mono c-blue">{l.pred_cfpp.toFixed(1)}°C</td>
                    <td className="mono c-amber">{l.wafi_suggested.toFixed(0)} ppm</td>
                    <td
                      className="mono group-cell"
                      style={{ color: "var(--color-text-primary)", cursor: "pointer" }}
                      onClick={() =>
                        editing?.logId !== l.log_id || editing.field !== "cfpp"
                          ? startEdit(l.log_id, "cfpp", l.actual_cfpp)
                          : undefined
                      }
                      title="클릭해서 실측 CFPP 입력"
                    >
                      {editing?.logId === l.log_id && editing.field === "cfpp" ? (
                        <input
                          autoFocus
                          type="number"
                          step="0.1"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") saveEdit();
                            else if (e.key === "Escape") cancelEdit();
                          }}
                          onBlur={saveEdit}
                          disabled={saving}
                          style={{
                            width: "70%",
                            padding: "2px 4px",
                            fontSize: 12,
                            border: "1px solid #BA7517",
                            borderRadius: 3,
                            fontFamily: "var(--font-mono)",
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : l.actual_cfpp != null ? (
                        <>{l.actual_cfpp.toFixed(1)}°C</>
                      ) : (
                        <span style={{ color: "var(--color-text-secondary)" }}>— 클릭 입력</span>
                      )}
                    </td>
                    <td
                      className="mono group-cell c-amber"
                      style={{ cursor: "pointer" }}
                      onClick={() =>
                        editing?.logId !== l.log_id || editing.field !== "wafi"
                          ? startEdit(l.log_id, "wafi", l.actual_wafi)
                          : undefined
                      }
                      title="클릭해서 실측 WAFI 입력"
                    >
                      {editing?.logId === l.log_id && editing.field === "wafi" ? (
                        <input
                          autoFocus
                          type="number"
                          step="10"
                          min={0}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") saveEdit();
                            else if (e.key === "Escape") cancelEdit();
                          }}
                          onBlur={saveEdit}
                          disabled={saving}
                          style={{
                            width: "70%",
                            padding: "2px 4px",
                            fontSize: 12,
                            border: "1px solid #BA7517",
                            borderRadius: 3,
                            fontFamily: "var(--font-mono)",
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      ) : l.actual_wafi != null ? (
                        <>
                          {l.actual_wafi.toFixed(0)} ppm
                          {l.actual_wafi !== l.wafi_suggested && (
                            <span style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>
                              {" "}
                              ({l.actual_wafi > l.wafi_suggested ? "+" : ""}
                              {(l.actual_wafi - l.wafi_suggested).toFixed(0)})
                            </span>
                          )}
                        </>
                      ) : (
                        <span style={{ color: "var(--color-text-secondary)" }}>— 클릭 입력</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!error && !logs && (
          <div style={{ padding: 14, fontSize: 12, color: "var(--color-text-secondary)" }}>
            불러오는 중...
          </div>
        )}
      </div>
    </>
  );
}

// ============= Sub-components =============

function KpiCard({
  label, value, unit, accent, icon, tone, hint, customBody,
}: {
  label: string;
  value?: string | number;
  unit?: string;
  accent?: boolean;
  icon?: string;
  tone?: "blue" | "green" | "default";
  hint?: string;
  customBody?: React.ReactNode;
}) {
  const toneColor =
    tone === "blue" ? "#185FA5" : tone === "green" ? "#3B6D11" : accent ? "#BA7517" : "var(--color-text-primary)";
  return (
    <div
      style={{
        background: accent ? "linear-gradient(135deg, #FAEEDA 0%, #fff 100%)" : "var(--color-background-primary)",
        border: accent ? "1px solid #E8C99A" : "0.5px solid var(--color-border-tertiary)",
        borderRadius: 8,
        padding: "12px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        minHeight: 78,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        {icon && <i className={`ti ${icon}`} style={{ fontSize: 13, color: toneColor }} />}
        <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>{label}</span>
      </div>
      {customBody ?? (
        <div style={{ fontSize: 22, fontWeight: 600, color: toneColor, fontFamily: "var(--font-mono)" }}>
          {value}
          {unit && <span style={{ fontSize: 11, fontWeight: 400, marginLeft: 3, color: "var(--color-text-secondary)" }}>{unit}</span>}
        </div>
      )}
      {hint && <div style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>{hint}</div>}
    </div>
  );
}

function ScenarioMiniBar({
  counts,
  total,
}: {
  counts?: Record<string, number>;
  total: number;
}) {
  if (!counts || total === 0) {
    return <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>데이터 없음</div>;
  }
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 2 }}>
      <div style={{ display: "flex", height: 14, borderRadius: 3, overflow: "hidden" }}>
        {(["min_cost", "balanced", "safe"] as const).map((k) =>
          counts[k] > 0 ? (
            <div
              key={k}
              style={{
                width: `${(counts[k] / total) * 100}%`,
                background: SCENARIO_COLOR[k],
              }}
              title={`${SCENARIO_LABEL[k]} ${counts[k]}건`}
            />
          ) : null,
        )}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "var(--color-text-secondary)" }}>
        {(["min_cost", "balanced", "safe"] as const).map((k) => (
          <span key={k} style={{ color: SCENARIO_COLOR[k], fontWeight: 600 }}>
            {SCENARIO_LABEL[k]} {counts[k]}
          </span>
        ))}
      </div>
    </div>
  );
}

function AlertCard({ analytics }: { analytics: { missTarget: Batch[]; wafiOver: Batch[] } | null }) {
  const miss = analytics?.missTarget.length ?? 0;
  const over = analytics?.wafiOver.length ?? 0;
  const hasAlert = miss > 0 || over > 0;
  return (
    <div
      className="card"
      style={{
        padding: "12px 14px",
        borderLeft: hasAlert ? "3px solid #C0392B" : "3px solid #3B6D11",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <i
          className={`ti ${hasAlert ? "ti-alert-triangle" : "ti-shield-check"}`}
          style={{ fontSize: 14, color: hasAlert ? "#C0392B" : "#3B6D11" }}
        />
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)" }}>
          오늘의 주의 알림
        </span>
      </div>
      {!hasAlert && (
        <div style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
          최근 30건 — 목표 미달 / WAFI 과투입 없음.
        </div>
      )}
      {hasAlert && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {miss > 0 && (
            <div style={{ fontSize: 11, color: "#C0392B" }}>
              <strong>{miss}건</strong> · CFPP 실측이 목표치 미달
            </div>
          )}
          {over > 0 && (
            <div style={{ fontSize: 11, color: "#B7791F" }}>
              <strong>{over}건</strong> · WAFI 제안 대비 +30ppm 이상 과투입
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InsightCard({ insight }: { insight?: string }) {
  return (
    <div
      className="card"
      style={{
        padding: "12px 14px",
        borderLeft: "3px solid #185FA5",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <i className="ti ti-bulb" style={{ fontSize: 14, color: "#185FA5" }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)" }}>
          AI 인사이트
        </span>
      </div>
      <div style={{ fontSize: 11, color: "var(--color-text-primary)", lineHeight: 1.6 }}>
        {insight ?? "분석 중..."}
      </div>
    </div>
  );
}

function PipelineCard({
  pipeline,
}: {
  pipeline?: { judged: number; selected: number; measured: number; shipped: number };
}) {
  const stages = [
    { key: "judged", label: "판단 완료", icon: "ti-clipboard-check" },
    { key: "selected", label: "시나리오 선택", icon: "ti-cursor-text" },
    { key: "measured", label: "실측 입력", icon: "ti-ruler-measure" },
    { key: "shipped", label: "출하 완료", icon: "ti-truck-delivery" },
  ] as const;
  return (
    <div className="card" style={{ padding: "12px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
        <i className="ti ti-route" style={{ fontSize: 14, color: "#BA7517" }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)" }}>
          오늘의 Batch 파이프라인
        </span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        {stages.map((s, i) => (
          <div key={s.key} style={{ display: "flex", alignItems: "center", flex: 1, gap: 4 }}>
            <div
              style={{
                flex: 1,
                background: "var(--color-background-secondary)",
                borderRadius: 4,
                padding: "6px 4px",
                textAlign: "center",
                border: "0.5px solid var(--color-border-tertiary)",
              }}
            >
              <i className={`ti ${s.icon}`} style={{ fontSize: 12, color: "#BA7517", display: "block", marginBottom: 2 }} />
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
                {pipeline ? pipeline[s.key] : "-"}
              </div>
              <div style={{ fontSize: 9, color: "var(--color-text-secondary)" }}>{s.label}</div>
            </div>
            {i < stages.length - 1 && (
              <i className="ti ti-chevron-right" style={{ fontSize: 12, color: "var(--color-text-secondary)" }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)" }}>{title}</div>
        {subtitle && <div style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>{subtitle}</div>}
      </div>
      {children}
    </div>
  );
}
