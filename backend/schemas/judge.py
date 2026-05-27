from typing import Literal
from pydantic import BaseModel, Field


Season = Literal["winter", "deep_winter", "summer", "spring", "fall"]
TankHistory = Literal["clean", "recent_change", "mixed"]
WafiType = Literal["A", "B", "C", "none"]
Decision = Literal["normal", "caution", "risk"]
Priority = Literal["cost", "balance", "safety"]


class BlendComponents(BaseModel):
    lgo: float = Field(..., ge=0.0, le=1.0)
    hgo: float = Field(..., ge=0.0, le=1.0)
    lco: float = Field(..., ge=0.0, le=1.0)
    kero: float = Field(..., ge=0.0, le=1.0)
    biodiesel: float = Field(..., ge=0.0, le=1.0)


class KeyMetrics(BaseModel):
    density_15c: float
    n_paraffin_c10_c15: float
    n_paraffin_c16_c20: float
    n_paraffin_c21_plus: float
    aromatic_content: float
    sulfur_ppm: float
    cetane_index: float
    wafi_type: WafiType = "A"
    wafi_ppm: float = 0.0


class JudgeRequest(BaseModel):
    blend_components: BlendComponents
    key_metrics: KeyMetrics
    target_cfpp: float
    season: Season
    tank_history_flag: TankHistory
    priority: Priority = "balance"


class WafiScenario(BaseModel):
    label: Literal["min_cost", "balanced", "safe"]
    wafi_type: WafiType
    wafi_ppm: float
    predicted_cfpp: float
    margin_to_target: float
    confidence: float
    rationale: str


class SimilarCase(BaseModel):
    case_id: str
    decision: Decision
    similarity_score: float
    rule_summary: str | None = None
    blend_components: dict | None = None
    key_metrics: dict | None = None
    target_cfpp: float | None = None
    season: str | None = None
    tank_history_flag: str | None = None


class JudgeResponse(BaseModel):
    decision: Decision
    predicted_cfpp_baseline: float
    confidence: float
    scenarios: list[WafiScenario]
    check_priority: list[str]
    similar_cases: list[SimilarCase]
    applied_heuristics: list[str] = Field(default_factory=list)
    log_id: str | None = None
