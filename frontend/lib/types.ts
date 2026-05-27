export type Decision = "normal" | "caution" | "risk";
export type Season = "winter" | "deep_winter" | "summer" | "spring" | "fall";
export type TankHistory = "clean" | "recent_change" | "mixed";
export type WafiType = "A" | "B" | "C" | "none";
export type Priority = "cost" | "balance" | "safety";

export interface BlendComponents {
  lgo: number;
  hgo: number;
  lco: number;
  kero: number;
  biodiesel: number;
}

export interface KeyMetrics {
  density_15c: number;
  n_paraffin_c10_c15: number;
  n_paraffin_c16_c20: number;
  n_paraffin_c21_plus: number;
  aromatic_content: number;
  sulfur_ppm: number;
  cetane_index: number;
  wafi_type: WafiType;
  wafi_ppm: number;
}

export interface JudgeRequest {
  blend_components: BlendComponents;
  key_metrics: KeyMetrics;
  target_cfpp: number;
  season: Season;
  tank_history_flag: TankHistory;
  priority: Priority;
}

export interface WafiScenario {
  label: "min_cost" | "balanced" | "safe";
  wafi_type: WafiType;
  wafi_ppm: number;
  predicted_cfpp: number;
  margin_to_target: number;
  confidence: number;
  rationale: string;
}

export interface SimilarCase {
  case_id: string;
  decision: Decision;
  similarity_score: number;
  rule_summary?: string | null;
  blend_components?: Record<string, number> | null;
  key_metrics?: Record<string, number | string> | null;
  target_cfpp?: number | null;
  season?: string | null;
  tank_history_flag?: string | null;
}

export interface JudgeResponse {
  decision: Decision;
  predicted_cfpp_baseline: number;
  confidence: number;
  scenarios: WafiScenario[];
  check_priority: string[];
  similar_cases: SimilarCase[];
  applied_heuristics: string[];
  log_id?: string | null;
}

export interface ConsultCitation {
  doc_id: string;
  doc_type: string;
  section_title?: string | null;
  similarity_score: number;
  preview: string;
}

export interface ConsultResponse {
  answer: string;
  used_llm: boolean;
  model?: string | null;
  retrieved_count: number;
  citations: ConsultCitation[];
}

export interface CaseRow {
  case_id: string;
  season: string;
  decision: Decision;
  target_cfpp: number;
  rule_summary?: string | null;
}
