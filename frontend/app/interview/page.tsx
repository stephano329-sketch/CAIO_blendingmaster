"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { DecisionBadge } from "@/components/badge";
import { Q2_OPTS, Q3_OPTS, Q4_OPTS, type Decision } from "@/lib/demo-data";
import { useUser } from "@/components/user-context";
import { api } from "@/lib/api";

type Answers = { q1: string | null; q2: string[]; q3: string[]; q4: string[]; q5: string };

type IVCase = {
  case_id: string;
  season: string;          // backend code: "winter" | "deep_winter"
  blend_components: Record<string, string>;
  cfpp: number;
  cp: number;
  pp: number;
  ai_draft_decision: string;
};

const SEASON_LABEL: Record<string, string> = { winter: "동절기", deep_winter: "혹한기" };

const AI_DRAFT_HINT: Record<string, string> = {
  normal: "기준 내 안착 추정",
  caution: "경계값·이력 영향 기반 주의 추정",
  risk: "기준 미달 또는 위험 패턴 감지",
};

export default function InterviewPage() {
  const [answers, setAnswers] = useState<Answers>({ q1: null, q2: [], q3: [], q4: [], q5: "" });
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>("");
  const [iv, setIv] = useState<IVCase | null>(null);
  const [loadingCase, setLoadingCase] = useState(true);
  const router = useRouter();
  const { user } = useUser();

  const fetchCase = async () => {
    setLoadingCase(true);
    setError("");
    try {
      const c = await api.nextInterviewCase();
      setIv(c as IVCase);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingCase(false);
    }
  };

  useEffect(() => {
    fetchCase();
  }, []);

  const reset = () => {
    setAnswers({ q1: null, q2: [], q3: [], q4: [], q5: "" });
    setSaved(false);
    fetchCase();
  };

  if (saved) {
    return (
      <div className="saved-screen">
        <i className="ti ti-check" style={{ fontSize: 48, color: "#3B6D11" }} />
        <div style={{ fontSize: 16, fontWeight: 500, color: "#3B6D11" }}>경험치 저장 완료</div>
        <div style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          JSON + 벡터 인덱스로 경험치 DB에 저장되었습니다.
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          <button className="btn-secondary" onClick={() => router.push("/kb")}>
            경험치 DB 확인
          </button>
          <button className="btn-primary" onClick={reset}>
            다음 케이스 →
          </button>
        </div>
      </div>
    );
  }

  const toggle = (key: keyof Answers, val: string, max: number) => {
    setAnswers((a) => {
      if (key === "q1") return { ...a, q1: val };
      if (key === "q5") return a;
      const arr = a[key] as string[];
      if (arr.includes(val)) return { ...a, [key]: arr.filter((x) => x !== val) };
      if (arr.length < max) return { ...a, [key]: [...arr, val] };
      return a;
    });
  };

  const qLabels = ["Q1. 판단", "Q2. 근거", "Q3. 우선순위", "Q4. 리스크", "Q5. 메모"];
  const done = [
    !!answers.q1,
    answers.q2.length > 0,
    answers.q3.length > 0,
    answers.q4.length > 0,
    !!answers.q5,
  ];

  const optBtn = (
    key: keyof Answers,
    val: string,
    label: string,
    max: number,
    selClass?: string,
  ) => {
    const a = answers[key];
    const sel = Array.isArray(a) ? a.includes(val) : a === val;
    const defaultClass =
      val === "normal" ? "sel-normal"
      : val === "caution" ? "sel-caution"
      : val === "risk" ? "sel-risk"
      : "sel-default";
    const cls = sel ? selClass || defaultClass : "";
    return (
      <button key={val} className={`opt-btn ${cls}`} onClick={() => toggle(key, val, max)}>
        {sel && <i className="ti ti-check" style={{ fontSize: 11 }} />}
        {label}
      </button>
    );
  };

  const save = async () => {
    if (!answers.q1 || saving || !iv) return;
    setSaving(true);
    setError("");
    try {
      await api.createKnowledge({
        case_id: iv.case_id,
        season: iv.season,
        blend_components: iv.blend_components,
        cfpp: iv.cfpp,
        cp: iv.cp,
        pp: iv.pp,
        ai_draft_decision: iv.ai_draft_decision,
        q1_decision: answers.q1,
        q2_reasons: answers.q2,
        q3_priorities: answers.q3,
        q4_risks: answers.q4,
        q5_memo: answers.q5,
        author: user,
      });
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loadingCase && !iv) {
    return (
      <div style={{ padding: 14, fontSize: 12, color: "var(--color-text-secondary)" }}>
        다음 케이스 불러오는 중...
      </div>
    );
  }

  if (!iv) {
    return (
      <div className="card" style={{ padding: 14, color: "#A32D2D", fontSize: 12 }}>
        <i className="ti ti-alert-octagon" style={{ marginRight: 6 }} />
        {error || "케이스를 불러올 수 없습니다."}
      </div>
    );
  }

  return (
    <div className="iv-layout">
      <div className="iv-top">
        <div className="iv-case-card">
          <div className="case-meta">
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 500, color: "var(--color-text-primary)" }}>
              {iv.case_id}
            </span>
            <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
              {SEASON_LABEL[iv.season] ?? iv.season}
            </span>
          </div>
          <div className="comp-grid">
            {Object.entries(iv.blend_components).map(([k, v]) => (
              <div key={k} className="comp-item">
                <div className="comp-label">{k}</div>
                <div className="comp-val">{v}</div>
              </div>
            ))}
          </div>
          <div className="metrics-row">
            <div className="metric-item">
              <div className="m-label">CFPP</div>
              <div className="m-val" style={{ color: "#854F0B" }}>{iv.cfpp.toFixed(1)}°C</div>
            </div>
            <div className="metric-item">
              <div className="m-label">CP</div>
              <div className="m-val" style={{ color: "#185FA5" }}>{iv.cp.toFixed(1)}°C</div>
            </div>
            <div className="metric-item">
              <div className="m-label">PP</div>
              <div className="m-val" style={{ color: "#185FA5" }}>{iv.pp.toFixed(1)}°C</div>
            </div>
          </div>
          <div className="ai-draft-box">
            <div style={{ fontSize: 10, color: "var(--color-text-secondary)", marginBottom: 5 }}>
              AI 초안 판단
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <DecisionBadge decision={iv.ai_draft_decision as Decision} />
              <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                {AI_DRAFT_HINT[iv.ai_draft_decision] ?? "기준 기반 추정"}
              </span>
            </div>
          </div>
        </div>

        <div className="iv-progress-card">
          <div
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: "var(--color-text-primary)",
              marginBottom: 12,
              paddingBottom: 10,
              borderBottom: "0.5px solid var(--color-border-tertiary)",
            }}
          >
            진행 상태
          </div>
          <div className="iv-progress-items">
            {qLabels.map((lbl, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 9 }}>
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    border: `0.5px solid ${done[i] ? "#BA7517" : "var(--color-border-secondary)"}`,
                    background: done[i] ? "#BA7517" : "transparent",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {done[i] ? (
                    <i className="ti ti-check" style={{ fontSize: 10, color: "#fff" }} />
                  ) : (
                    <span style={{ fontSize: 10, color: "var(--color-text-secondary)", fontWeight: 500 }}>
                      {i + 1}
                    </span>
                  )}
                </div>
                <span
                  style={{
                    fontSize: 12,
                    color: done[i] ? "var(--color-text-primary)" : "var(--color-text-secondary)",
                    fontWeight: done[i] ? 500 : 400,
                  }}
                >
                  {lbl}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="iv-q-list">
        <div className="iv-q-block">
          <div className="q-section-title">Q1. 판단</div>
          <div className="opt-group">
            {optBtn("q1", "normal", "정상", 1, "sel-normal")}
            {optBtn("q1", "caution", "주의", 1, "sel-caution")}
            {optBtn("q1", "risk", "위험", 1, "sel-risk")}
          </div>
        </div>
        <div className="iv-q-block">
          <div className="q-section-title">
            Q2. 판단 근거{" "}
            <span style={{ color: "var(--color-text-secondary)", fontWeight: 400 }}>(최대 2개)</span>
          </div>
          <div className="opt-group">{Q2_OPTS.map(([v, l]) => optBtn("q2", v, l, 2))}</div>
        </div>
        <div className="iv-q-block">
          <div className="q-section-title">
            Q3. 확인 우선순위{" "}
            <span style={{ color: "var(--color-text-secondary)", fontWeight: 400 }}>(Top 3)</span>
          </div>
          <div className="opt-group">{Q3_OPTS.map(([v, l]) => optBtn("q3", v, l, 3))}</div>
        </div>
        <div className="iv-q-block">
          <div className="q-section-title">Q4. 리스크 포인트</div>
          <div className="opt-group">{Q4_OPTS.map(([v, l]) => optBtn("q4", v, l, 9))}</div>
        </div>
        <div className="iv-q-block">
          <div className="q-section-title">Q5. 한 줄 기준 메모</div>
          <textarea
            className="q5-textarea"
            placeholder="판단 기준을 1~2문장으로 요약..."
            value={answers.q5}
            onChange={(e) => setAnswers({ ...answers, q5: e.target.value })}
          />
        </div>
      </div>

      <div className="iv-actions">
        <button className="btn-secondary" style={{ fontSize: 12, padding: "6px 12px" }}>
          세션 종료
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {error && (
            <span style={{ fontSize: 11, color: "#A32D2D" }}>
              <i className="ti ti-alert-octagon" style={{ marginRight: 4 }} />
              {error}
            </span>
          )}
          <button
            className={answers.q1 ? "btn-primary" : "btn-secondary"}
            style={{ fontSize: 12, padding: "6px 14px", opacity: saving ? 0.6 : 1 }}
            onClick={save}
            disabled={saving || !answers.q1}
          >
            {saving ? "저장 중..." : "저장 → 다음 케이스"}
          </button>
        </div>
      </div>
    </div>
  );
}
