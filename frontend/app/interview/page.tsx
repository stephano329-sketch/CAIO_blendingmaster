"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Q2_OPTS, Q3_OPTS, Q4_OPTS } from "@/lib/demo-data";
import { useUser } from "@/components/user-context";
import { api } from "@/lib/api";
import troubleCasesData from "@/lib/trouble-cases.json";

type Answers = { q1: string | null; q2: string[]; q3: string[]; q4: string[]; q5: string };

type TroubleCase = {
  id: string;
  date: string;
  season: "winter" | "deep_winter";
  situation: string;     // when + what was being made (간단 상황)
  problem: string;       // 무엇이 문제였는지
  cause: string;         // 추정 원인
  resolution: string;    // 어떻게 해결했는지
};

const SEASON_LABEL: Record<string, string> = { winter: "동절기", deep_winter: "혹한기" };

const TROUBLE_CASES: TroubleCase[] = troubleCasesData as TroubleCase[];

export default function InterviewPage() {
  const [answers, setAnswers] = useState<Answers>({ q1: null, q2: [], q3: [], q4: [], q5: "" });
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>("");
  const [caseIdx, setCaseIdx] = useState(0);
  const [extractedIds, setExtractedIds] = useState<Set<string>>(new Set());
  const router = useRouter();
  const { user } = useUser();

  const tc = TROUBLE_CASES[caseIdx];
  const isExtracted = extractedIds.has(tc.id);

  const refreshExtracted = useCallback(async () => {
    try {
      const items = await api.listKnowledge({ limit: 500 });
      setExtractedIds(new Set(items.map((it) => it.case_id)));
    } catch {
      // silent — badge just won't show if API fails
    }
  }, []);

  useEffect(() => {
    refreshExtracted();
  }, [refreshExtracted]);

  const reset = () => {
    setAnswers({ q1: null, q2: [], q3: [], q4: [], q5: "" });
    setSaved(false);
    setCaseIdx((i) => (i + 1) % TROUBLE_CASES.length);
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
    if (!answers.q1 || saving) return;
    setSaving(true);
    setError("");
    try {
      await api.createKnowledge({
        case_id: tc.id,
        season: tc.season,
        blend_components: {},
        cfpp: 0,
        cp: 0,
        pp: 0,
        ai_draft_decision: "caution",
        q1_decision: answers.q1,
        q2_reasons: answers.q2,
        q3_priorities: answers.q3,
        q4_risks: answers.q4,
        q5_memo: answers.q5,
        author: user,
      });
      setExtractedIds((prev) => new Set(prev).add(tc.id));
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="iv-layout">
      <div className="iv-top">
        <div className="iv-case-card" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <i className="ti ti-bulb" style={{ fontSize: 16, color: "#BA7517" }} />
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: "var(--color-text-primary)" }}>
                {tc.id}
              </span>
              <span style={{ fontSize: 11, color: "var(--color-text-secondary)" }}>
                {tc.date} · {SEASON_LABEL[tc.season]}
              </span>
              {isExtracted && (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: "#fff",
                    background: "#3B6D11",
                    padding: "2px 8px",
                    borderRadius: 10,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 3,
                  }}
                >
                  <i className="ti ti-check" style={{ fontSize: 10 }} />
                  지식추출 완료
                </span>
              )}
            </div>
            <span style={{ fontSize: 10, color: "var(--color-text-secondary)" }}>
              {caseIdx + 1} / {TROUBLE_CASES.length}
            </span>
          </div>

          <div style={{ fontSize: 12, color: "var(--color-text-primary)", lineHeight: 1.6, padding: "8px 10px", background: "var(--color-background-secondary)", borderRadius: 4 }}>
            {tc.situation}
          </div>

          <TroubleLine icon="ti-alert-triangle" color="#C0392B" label="문제" text={tc.problem} />
          <TroubleLine icon="ti-search" color="#B7791F" label="추정 원인" text={tc.cause} />
          <TroubleLine icon="ti-check" color="#3B6D11" label="해결" text={tc.resolution} />

          <div style={{ fontSize: 10, color: "var(--color-text-secondary)", marginTop: 4, paddingTop: 8, borderTop: "0.5px dashed var(--color-border-tertiary)" }}>
            위 사례에 대해 아래 Q1~Q5를 답변해 주세요.
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
        <div style={{ display: "flex", gap: 6 }}>
          <button
            className="btn-secondary"
            style={{ fontSize: 12, padding: "6px 12px" }}
            onClick={() => {
              setAnswers({ q1: null, q2: [], q3: [], q4: [], q5: "" });
              setSaved(false);
              setCaseIdx((i) => (i - 1 + TROUBLE_CASES.length) % TROUBLE_CASES.length);
            }}
          >
            ← 이전 사례
          </button>
          <button className="btn-secondary" style={{ fontSize: 12, padding: "6px 12px" }} onClick={reset}>
            다음 사례 →
          </button>
        </div>
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
            {saving ? "저장 중..." : "저장 → 다음 사례"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TroubleLine({ icon, color, label, text }: { icon: string; color: string; label: string; text: string }) {
  return (
    <div style={{ display: "flex", gap: 6 }}>
      <i className={`ti ${icon}`} style={{ fontSize: 12, color, marginTop: 3, flexShrink: 0 }} />
      <div style={{ fontSize: 12, lineHeight: 1.6, color: "var(--color-text-primary)" }}>
        <span style={{ fontWeight: 600, color, marginRight: 4 }}>{label}</span>
        {text}
      </div>
    </div>
  );
}
