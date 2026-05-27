import type {
  CaseRow,
  ConsultResponse,
  JudgeRequest,
  JudgeResponse,
} from "./types";

const BASE = "/api/backend";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText} :: ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => call<{ status: string }>("/health"),
  judge: (body: JudgeRequest) =>
    call<JudgeResponse>("/judge", { method: "POST", body: JSON.stringify(body) }),
  consult: (body: {
    query: string;
    top_k?: number;
    doc_type?: string;
    season?: string;
    case_id?: string;
  }) =>
    call<ConsultResponse>("/consult", { method: "POST", body: JSON.stringify(body) }),
  listCases: (params: { season?: string; decision?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.season) q.set("season", params.season);
    if (params.decision) q.set("decision", params.decision);
    if (params.limit) q.set("limit", String(params.limit));
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return call<CaseRow[]>(`/cases${suffix}`);
  },
  getCase: (caseId: string) =>
    call<{
      case_id: string;
      season: string;
      tank_history_flag: string;
      target_cfpp: number;
      decision: string;
      rule_summary: string | null;
      blend_components: Record<string, number>;
      key_metrics: Record<string, number | string>;
    }>(`/cases/${encodeURIComponent(caseId)}`),
  nextInterviewCase: () =>
    call<{
      case_id: string;
      season: string;
      blend_components: Record<string, string>;
      cfpp: number; cp: number; pp: number;
      ai_draft_decision: string;
    }>("/interview/next-case"),
  listKnowledge: (params: { decision?: string; season?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.decision) q.set("decision", params.decision);
    if (params.season) q.set("season", params.season);
    if (params.limit != null) q.set("limit", String(params.limit));
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return call<Array<{
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
    }>>(`/knowledge${suffix}`);
  },
  createKnowledge: (payload: {
    case_id: string;
    season: string;
    blend_components: Record<string, string>;
    cfpp: number; cp: number; pp: number;
    ai_draft_decision?: string | null;
    q1_decision: string;
    q2_reasons: string[]; q3_priorities: string[]; q4_risks: string[];
    q5_memo: string;
    author: string;
  }) => call("/knowledge", { method: "POST", body: JSON.stringify(payload) }),
  dashboardStats: () =>
    call<{ today_batch_count: number; month_judge_count: number; month_saving_man_won: number }>(
      "/dashboard/stats",
    ),
  listBatches: (params: { limit?: number; offset?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.limit != null) q.set("limit", String(params.limit));
    if (params.offset != null) q.set("offset", String(params.offset));
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return call<Array<{
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
    }>>(`/journal/batches${suffix}`);
  },
  createDecisionLog: (payload: { input: unknown; ai_recommendation: unknown; selected_scenario: string }) =>
    call<{ log_id: string; selected_scenario: string }>(
      "/decision-logs",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  patchSelectedScenario: (logId: string, label: string) =>
    call<{ log_id: string; selected_scenario: string }>(
      `/decision-logs/${encodeURIComponent(logId)}/select-scenario`,
      { method: "PATCH", body: JSON.stringify({ label }) },
    ),
  patchOutcome: (logId: string, body: { actual_cfpp?: number; actual_wafi?: number }) =>
    call<{ log_id: string; actual_outcome: { cfpp?: number; wafi_ppm?: number } }>(
      `/decision-logs/${encodeURIComponent(logId)}/outcome`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),
  dashboardRecentLogs: (limit = 10) =>
    call<Array<{
      date: string;
      log_id: string;
      pred_cfpp: number;
      wafi_suggested: number;
      actual_cfpp: number | null;
      actual_wafi: number | null;
      decision: string;
      selected_scenario: string | null;
    }>>(`/dashboard/recent-logs?limit=${limit}`),
  ragTypes: () => call<Record<string, number>>("/rag/types"),
  ragList: (params: { doc_type?: string; limit?: number; offset?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.doc_type) q.set("doc_type", params.doc_type);
    if (params.limit != null) q.set("limit", String(params.limit));
    if (params.offset != null) q.set("offset", String(params.offset));
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return call<{ total: number; items: Array<{ doc_id: string; doc_type: string; text: string; metadata: Record<string, unknown> }> }>(`/rag/docs${suffix}`);
  },
  ragSearch: (q: string, top_k = 5, doc_type?: string) => {
    const params = new URLSearchParams({ q, top_k: String(top_k) });
    if (doc_type) params.set("doc_type", doc_type);
    return call<{
      query: string;
      hits: Array<{ doc_id: string; doc_type: string; text: string; metadata: Record<string, unknown>; similarity_score: number; distance: number }>;
    }>(`/rag/search?${params.toString()}`);
  },
};
