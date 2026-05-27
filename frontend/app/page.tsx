"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

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

type EditField = "cfpp" | "wafi";

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [logs, setLogs] = useState<LogRow[] | null>(null);
  const [error, setError] = useState<string>("");
  const [editing, setEditing] = useState<{ logId: string; field: EditField } | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [saving, setSaving] = useState(false);

  const refresh = () => {
    Promise.all([api.dashboardStats(), api.dashboardRecentLogs(10)])
      .then(([s, l]) => {
        setStats(s);
        setLogs(l);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  };

  useEffect(() => {
    refresh();
  }, []);

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
      <div className="stat-grid">
        <div className="stat-card accent">
          <div className="stat-label">오늘 처리한 Batch</div>
          <div className="stat-val">
            {stats?.today_batch_count ?? "-"}<span className="stat-unit">건</span>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">이번 달 판단</div>
          <div className="stat-val">
            {stats?.month_judge_count ?? "-"}<span className="stat-unit">건</span>
          </div>
        </div>
        <div className="stat-card accent">
          <div className="stat-label">이번 달 절감액(추정)</div>
          <div className="stat-val">
            {stats?.month_saving_man_won.toLocaleString() ?? "-"}<span className="stat-unit">만원</span>
          </div>
        </div>
      </div>
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
                <col style={{ width: 110 }} />
                <col style={{ width: 110 }} />
                <col style={{ width: 150 }} />
                <col style={{ width: 150 }} />
              </colgroup>
              <thead>
                <tr>
                  <th>날짜</th>
                  <th>로그 ID</th>
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
                    <td className="mono c-blue">{l.pred_cfpp.toFixed(1)}°C</td>
                    <td className="mono c-amber">{l.wafi_suggested.toFixed(0)} ppm</td>
                    <td
                      className="mono group-cell"
                      style={{ color: "var(--color-text-primary)", cursor: "pointer" }}
                      onClick={() => editing?.logId !== l.log_id || editing.field !== "cfpp" ? startEdit(l.log_id, "cfpp", l.actual_cfpp) : undefined}
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
                      onClick={() => editing?.logId !== l.log_id || editing.field !== "wafi" ? startEdit(l.log_id, "wafi", l.actual_wafi) : undefined}
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
