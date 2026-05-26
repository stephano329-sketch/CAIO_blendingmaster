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

function delta(pred: number, actual: number) {
  const d = (actual - pred).toFixed(1);
  const sign = +d > 0 ? "+" : "";
  return (
    <span className={Math.abs(+d) <= 1 ? "delta-ok" : "delta-up"}>
      {sign}
      {d}
    </span>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [logs, setLogs] = useState<LogRow[] | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    Promise.all([api.dashboardStats(), api.dashboardRecentLogs(10)])
      .then(([s, l]) => {
        setStats(s);
        setLogs(l);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

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
                    <td className="mono group-cell" style={{ color: "var(--color-text-primary)" }}>
                      {l.actual_cfpp != null ? (
                        <>
                          {l.actual_cfpp.toFixed(1)}°C&nbsp;{delta(l.pred_cfpp, l.actual_cfpp)}
                        </>
                      ) : (
                        <span style={{ color: "var(--color-text-secondary)" }}>—</span>
                      )}
                    </td>
                    <td className="mono group-cell c-amber">
                      {l.actual_wafi != null ? (
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
                        <span style={{ color: "var(--color-text-secondary)" }}>—</span>
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
