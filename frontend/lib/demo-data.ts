export type UserKey = "junior" | "veteran";
export type Decision = "normal" | "caution" | "risk";

export const USERS: { value: UserKey; label: string; initials: string }[] = [
  { value: "junior", label: "김 연구원", initials: "김" },
  { value: "veteran", label: "이 부장", initials: "이" },
];

export const NAV = [
  { id: "/introduction", label: "Introduction", icon: "ti-info-circle" },
  { id: "/", label: "대시보드", icon: "ti-layout-dashboard" },
  { id: "/judge", label: "신규 판단", icon: "ti-clipboard-check" },
  { id: "/consult", label: "AI 상담", icon: "ti-message-dots" },
  { id: "/journal", label: "제품 배합 일지", icon: "ti-book-2" },
  { id: "/interview", label: "지식 추출", icon: "ti-user-question" },
  { id: "/kb", label: "경험치 DB", icon: "ti-database" },
  { id: "/rag", label: "RAG 문서 확인", icon: "ti-file-search" },
];

export const Q2_LABELS: Record<string, string> = {
  metric_level: "검사값 절대 수준",
  blend_component: "블렌딩 구성",
  tank_history: "탱크 이력",
  seasonality: "계절 영향",
  additive: "첨가제 영향",
  other: "기타",
};
export const Q3_LABELS: Record<string, string> = {
  retest: "검사 재확인",
  tank_history: "탱크 이력",
  blend_ratio: "블렌딩 비율",
  additive_dose: "첨가제 투입량",
  process_condition: "공정 조건",
};
export const Q4_LABELS: Record<string, string> = {
  within_spec: "기준내 안착 가능",
  historical: "이력 영향",
  post_issue: "출하 후 문제",
  conditional: "조건부 품질 안착",
};

export const Q2_OPTS: [string, string][] = [
  ["metric_level", "검사값 절대 수준"],
  ["blend_component", "블렌딩 구성"],
  ["tank_history", "탱크 이력"],
  ["seasonality", "계절 영향"],
  ["additive", "첨가제 영향"],
  ["other", "기타"],
];
export const Q3_OPTS: [string, string][] = [
  ["retest", "검사 재확인"],
  ["tank_history", "탱크 이력"],
  ["blend_ratio", "블렌딩 비율"],
  ["additive_dose", "첨가제 투입량"],
  ["process_condition", "공정 조건"],
];
export const Q4_OPTS: [string, string][] = [
  ["within_spec", "기준내 안착 가능"],
  ["historical", "이력 영향"],
  ["post_issue", "출하 후 문제"],
  ["conditional", "조건부 품질 안착"],
];

export const LOGS = [
  { date: "2026-05-17", id: "D-2104", predCfpp: -14.2, wafiSug: 240, actualCfpp: -14.0, actualWafi: 240 },
  { date: "2026-05-16", id: "D-2103", predCfpp: -12.5, wafiSug: 150, actualCfpp: -12.8, actualWafi: 150 },
  { date: "2026-05-15", id: "D-2102", predCfpp: -17.8, wafiSug: 380, actualCfpp: -16.1, actualWafi: 400 },
  { date: "2026-05-14", id: "D-2101", predCfpp: -11.3, wafiSug: 120, actualCfpp: -11.5, actualWafi: 120 },
];

export type KBRecord = {
  id: string;
  caseId: string;
  season: string;
  comps: Record<string, string>;
  cfpp: number;
  cp: number;
  pp: number;
  aiDraft?: Decision;
  q1: Decision;
  q2: string[];
  q3: string[];
  q4: string[];
  q5: string;
  author: UserKey;
  savedAt: string;
};

export const INITIAL_KB: KBRecord[] = [
  {
    id: "KB-0003", caseId: "CASE-SYN-0023", season: "혹한기",
    comps: { LGO: "35%", HGO: "25%", LCO: "30%", Kero: "10%" }, cfpp: -16, cp: -8, pp: -10,
    aiDraft: "caution", q1: "caution",
    q2: ["blend_component", "tank_history"],
    q3: ["tank_history", "blend_ratio", "retest"],
    q4: ["within_spec", "conditional"],
    q5: "LCO 25% 초과 + 혹한기 조합에서는 탱크 잔류물 영향까지 함께 확인 필요. WAFI 단독으로 해결 어려움.",
    author: "veteran", savedAt: "2026-05-18 16:42",
  },
  {
    id: "KB-0002", caseId: "CASE-SYN-0019", season: "동절기",
    comps: { LGO: "25%", HGO: "30%", LCO: "35%", Kero: "10%" }, cfpp: -12, cp: -6, pp: -9,
    aiDraft: "risk", q1: "risk",
    q2: ["blend_component", "additive"],
    q3: ["blend_ratio", "additive_dose", "retest"],
    q4: ["post_issue", "within_spec"],
    q5: "LCO 30% 이상이면 WAFI 효과 둔화. CP-CFPP 갭이 좁으면 출하 후 동결 위험 큼.",
    author: "veteran", savedAt: "2026-05-17 11:20",
  },
  {
    id: "KB-0001", caseId: "CASE-SYN-0015", season: "동절기",
    comps: { LGO: "45%", HGO: "30%", LCO: "15%", Kero: "10%" }, cfpp: -14, cp: -10, pp: -12,
    aiDraft: "normal", q1: "normal",
    q2: ["metric_level"], q3: ["retest"], q4: [],
    q5: "파라핀 계열 위주 + LCO 15% 이하 조건. 표준 WAFI 투입 범위로 충분.",
    author: "junior", savedAt: "2026-05-16 09:08",
  },
];

export const JUDGE_LABELS: Record<Decision, string> = {
  normal: "정상",
  caution: "주의",
  risk: "위험",
};
