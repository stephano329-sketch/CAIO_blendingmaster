# Synthetic Data Generation Plan — Blending Master MVP

## Context

Blending Master(CAIO 10기 12조)는 경유 저온성상(CFPP/CP/PP) 관리와 WAFI(Wax Anti-settling Flow Improver) 첨가제 주입량 의사결정을 지원하는 RAG + ML 기반 AI Agent다. PRD v2.3 §02·§09에 따라 MVP는 **사내 실데이터를 사용하지 않고 합성 데이터로 데모 시스템을 구축**한다.

본 계획은 PRD §09(데이터 확보)와 부록 B(ML Feature)를 기반으로 다음 3종 합성 데이터셋의 생성 방법을 정의한다:
- **F**: ML 학습 데이터 (XGBoost CFPP 예측용)
- **D**: 사례 지식 (1차 RAG 유사 사례 검색용)
- **E-seed**: 인터뷰 시드 케이스 (베테랑 지식 추출 Agent UI 시연용)

A·B·C(공정/생산/반제품 지식)는 공개자료 기반 저작이고, G(코드 체계 25종)는 PRD 부록 A에 정의되어 합성 대상이 아니다.

## Source Documents

- `Blending_Master_PRD_v2_3.md` — PRD v2.3
- `BRD_Diesel_RAG_Detailed_Final.md` — BRD v1.0
- `.moai/project/product.md`, `structure.md`, `tech.md` — 파생 문서

## User-Confirmed Constraints

다음 5개 조정 사항은 사용자 확정:
1. `biodiesel_ratio` = 0.03 고정 (국내 경유 생산 규격)
2. `season` = {winter, deep_winter} 만 사용 (여름은 WAFI 미투입)
3. ML 데이터 규모 = 500건
4. E-seed의 `decision`(정답) 사전 채움 (MVP 시연 우선)
5. WAFI 0ppm baseline CFPP 분포 = -10°C ~ +5°C

## Decision Log

| # | 항목 | 상태 | 확정 값 |
| --- | --- | --- | --- |
| 1 | WAFI 응답 곡선 파라미터 (A, k) | ✅ 확정 | 옵션 ① 표준: A타입 (A=12, k=0.008), B타입 (A=10, k=0.010), C타입 (A=15, k=0.005) |
| 1b | LCO 감쇠 룰 | ✅ 확정 | ⓐ 유지: LCO 비율 > 15% → WAFI 효과 30% 감쇠 |
| 2 | 라벨링 룰 임계값 | ✅ 확정 | 옵션 ② 엄격: normal margin >= 4°C, caution margin >= 2°C |
| 2b | 라벨 노이즈 주입 | ✅ 확정 | 5% 균등 (500건 중 25건을 인접 클래스로 무작위 뒤집음) |
| 3 | wafi_ppm 0ppm 비중 | ✅ 확정 | 5% 균등 (25건: winter 13건 + deep_winter 12건) |
| 4 | 계절별 WAFI 평균 ppm 차등 | ✅ 확정 | ① 차등 Uniform: winter ~ U(50, 350) 평균 200ppm, deep_winter ~ U(200, 500) 평균 350ppm |
| 5 | E-seed 초안 vs 정답 차이 비율 | ✅ 확정 | ④ 21/10/4 (60% 일치, 낙관 10건 ≫ 과민 4건) — 베테랑이 AI보다 더 보수적이라는 메시지 강조 |
| 6 | D의 `actual_outcome` off-spec 발생률 | ✅ 확정 | ① 일관성: normal 0%, caution 25%, risk 60% (총 ~10건/35) |

## Plan (Incremental — 의사결정 확정 시 갱신)

### Dataset F — ML Training Data (500 records)

**Features (16개, Bio 제외)**:
- 반제품 비율: lgo_ratio (0.40~0.85), hgo_ratio (0.00~0.30), lco_ratio (0.00~0.20), kero_ratio (0.00~0.10)
- 성상: density_15c, n_paraffin_c10_c15, n_paraffin_c16_c20, n_paraffin_c21_plus, aromatic_content, sulfur_ppm, cetane_index
- 첨가제: wafi_type {A,B,C,none}, wafi_ppm (0~500)
- 환경: season {winter, deep_winter}, tank_history_flag {clean, recent_change, mixed}

**Constraints**:
- LGO + HGO + LCO + Kero = 0.97 (Bio 0.03 고정)
- Bio 컬럼은 데이터에 포함되지만 ML 학습 시 drop

**Physical Model**:
- 반제품 baseline CFPP: LGO -6°C, HGO +14°C, LCO -6°C, Kero -40°C, Bio +5°C
- δ_nparaffin = 0.7 × (n_paraffin_c16_c20 - 9) + 1.4 × (n_paraffin_c21_plus - 2)
- WAFI 효과: ΔCFPP = -A × (1 - exp(-k × ppm)), Type별 (A,k) 확정 (Decision 1)
- LCO > 15% → WAFI 효과 0.7배 감쇠 (Decision 1b)
- 측정 노이즈: N(0, 0.8°C)

**Sampling**:
- LHS 16차원
- 계절 stratified: winter 50%, deep_winter 50%
- WAFI 0ppm baseline 비중: 5% (25건, 계절별 균등)
  - 비고: ML baseline 학습 신호가 적으므로 WAFI 효과 학습 페어 30쌍을 의도적으로 보강하여 단조성 학습을 강화
- 극단 케이스: 5%
- WAFI 효과 학습 페어: 30쌍 의도 생성

**Split**: Train 350 / Val 75 / Test 75

### Dataset D — Case Knowledge (35 cases)

| 판단 \ 계절 | 동절기 | 혹한기 | 소계 |
| --- | --- | --- | --- |
| normal | 5 | 5 | 10 |
| caution | 8 | 7 | 15 |
| risk | 5 | 5 | 10 |
| **소계** | **18** | **17** | **35** |

- F에서 35건 샘플링 → 검사값 일관성 확보
- `actual_outcome.off_spec` 발생률 (Decision 6 확정):
  - normal 10건 → off_spec 0건
  - caution 15건 → off_spec 4건 (~25%)
  - risk 10건 → off_spec 6건 (~60%)
  - 35건 합계 ~10건 off_spec
- `actual_outcome.rework_required`: off_spec 케이스의 80% (~8건)에서 true
- `actual_outcome.wafi_adjusted_to`: 초기 WAFI 대비 ±50ppm 범위에서 결정 (off_spec 케이스는 +50~+150ppm 증액 보정)
- `narrative` 필드는 LLM 보조 또는 템플릿 + 슬롯 생성 (RAG 임베딩 대상)

### Dataset E-seed — Interview Seeds (35 cases)

D와 동일한 35건 매트릭스 분포 (다른 케이스 ID).
모든 응답 필드(`decision`, `reason_codes`, `check_priority`, `risk_codes`, `rule_summary`) 사전 채움.
추가 필드: `ai_draft_decision`, `ai_draft_reason_codes` (Agent 초안)

**초안 vs 정답 차이 비율 (Decision 5 확정 — ④ 21/10/4)**:

| 패턴 | 건수 | 의미 |
| --- | --- | --- |
| 일치 (`ai_draft_decision == decision`) | 21건 (60%) | Agent가 잘 맞히는 일반 케이스 |
| Agent 낙관 (초안 < 정답: normal→caution, caution→risk) | 10건 (29%) | 베테랑이 위험을 더 보수적으로 판단 |
| Agent 과민 (초안 > 정답: caution→normal, risk→caution) | 4건 (11%) | 베테랑이 안전 마진을 정확히 봐서 통과 |

배분 원칙:
- 낙관 10건은 caution/risk 정답 케이스에서 우선 배정 (베테랑 가치 부각)
- 과민 4건은 normal/caution 정답 케이스에서 배정
- 메시지: "Agent는 안전 장치, 베테랑은 더 보수적이고 정확한 판단자"

### Labeling Rule (확정)

```
margin = target_cfpp - predicted_cfpp
target_cfpp: winter -16°C, deep_winter -23°C

if margin >= 4°C and tank_history_flag == 'clean' and 변동성_낮음:
    decision = "normal"
elif margin >= 2°C or (margin >= 0 and tank_history_flag != 'clean'):
    decision = "caution"
elif margin < 0 or (n_paraffin_c21_plus > 3.5 and wafi_ppm < 150):
    decision = "risk"

# 라벨 노이즈: 전체 500건 중 무작위 25건(5%)의 라벨을 인접 클래스로 뒤집음
#   normal ↔ caution: 12건
#   caution ↔ risk:   13건
#   normal → risk 또는 risk → normal로의 점프는 금지 (인접 클래스만)
```

예상 분포: normal ~22%, caution ~46%, risk ~32% (라벨 노이즈 적용 전)

### Validation / Sanity Check

- 반제품 비율 합 = 1.00 ± 0.001 (Bio 항상 = 0.03)
- Season ⊂ {winter, deep_winter}
- WAFI 0ppm baseline 분포: 평균 -3°C ± 1°C, 5~95 percentile ⊂ [-10, +5]°C
- WAFI 단조성: Spearman > 0.85 (동일 조건 ppm 증가 시 CFPP 감소)
- 라벨 균형: normal:caution:risk ≈ 30:45:25
- 도메인 검토 (오상훈) 무작위 20건 합리성 검토 통과

### Output Files

```
data/synthetic/
├── ml_training.csv          # F, 500행 × 17 컬럼
├── ml_training_meta.json    # 시드, 분포 통계, 검증 결과
├── cases.json               # D, 35건
├── interview_seeds.json     # E-seed, 35건 (decision 사전 채움)
└── README.md                # 생성 방법, 시드, 재현 절차

ml/data_generation/
├── synthetic_generator.py   # 메인 생성기 (LHS + 물리 모델)
├── physical_model.py        # CFPP/WAFI 응답 함수
├── case_renderer.py         # F → D 서사 변환
├── seed_renderer.py         # F → E-seed 변환
└── validate.py              # Sanity check
```

### Generation Pipeline

1. LHS 샘플링 (500행) — 16차원
2. 반제품 비율 정규화 (Bio 0.03 차감 후 4개 비율 합 = 0.97)
3. 종속 성상 계산 (가중평균 + 노이즈)
4. 물리 모델 → cfpp, cp, pp 계산
5. 라벨링 룰 → decision 부여
6. Sanity check 통과 확인 → 실패 시 1로
7. F → ml_training.csv 저장
8. F에서 35건 샘플 → D 생성 (서사 + 코드)
9. D 매트릭스 위에 다양성 축 보정 → E-seed 생성 (decision 포함 사전 채움)
10. 도메인 검토자(오상훈) 20건 검토
11. 보정 사항 반영 후 v1.0 락

## Critical Files to Modify (Implementation 시점)

- `ml/data_generation/synthetic_generator.py` (신규)
- `ml/data_generation/physical_model.py` (신규)
- `ml/data_generation/case_renderer.py` (신규)
- `ml/data_generation/seed_renderer.py` (신규)
- `ml/data_generation/validate.py` (신규)
- `data/synthetic/*.csv|json` (생성 결과물)
- `data/synthetic/README.md` (재현 절차 문서)

## Verification

- Phase 1 완료 시: `pytest ml/data_generation/tests/` 통과 (Sanity check 자동화)
- 도메인 검토자 20건 무작위 검토 합격
- ML 1차 학습 결과 R² ≥ 0.85, MAE ≤ 2°C (PRD KPI)
- D 데이터셋이 ChromaDB에 인덱싱되어 유사 사례 Top-5 Recall ≥ 80% 측정 가능
- E-seed가 인터뷰 UI에서 정상적으로 시연 가능 (초안 → 정답 비교 화면)

## Final Spec Summary (모든 의사결정 확정)

### Dataset F (500건)
- Features: 16개 (Bio 0.03 고정 → 학습 시 drop)
- Sampling: LHS 16차원, 계절 50:50, 0ppm 25건(5%), 극단 5%, WAFI 단조성 페어 30쌍
- 분할: Train 350 / Val 75 / Test 75
- **WAFI ppm 분포**: winter ~ Uniform(50, 350), deep_winter ~ Uniform(200, 500), 0ppm 케이스 25건 별도
- **WAFI 응답 곡선 (Type별 A, k)**:
  - Type A: A=12, k=0.008 (균형형)
  - Type B: A=10, k=0.010 (저ppm 효율형)
  - Type C: A=15, k=0.005 (고ppm 잠재력형)
  - none:   A=0
  - LCO > 15% → 효과 0.7배 감쇠
- **반제품 baseline CFPP**: LGO -6, HGO +14, LCO -6, Kero -40, Bio +5
- **라벨링 룰** (margin = target_cfpp - predicted_cfpp):
  - normal: margin >= 4°C + clean tank + 변동성 낮음
  - caution: margin >= 2°C 또는 (margin >= 0 + 비-clean tank)
  - risk: margin < 0 또는 (n_paraffin_c21+ > 3.5 + wafi_ppm < 150)
- **라벨 노이즈**: 5% 균등 (25건을 인접 클래스로 무작위 뒤집음)

### Dataset D (35건)
- 매트릭스: winter 18 (5/8/5) + deep_winter 17 (5/7/5)
- F에서 샘플링하여 검사값 일관성 보장
- **off_spec 비율**: normal 0%, caution 25%(4건), risk 60%(6건) → 총 10건/35
- rework_required: off_spec의 80%
- narrative: 템플릿 + 슬롯 또는 LLM 보조

### Dataset E-seed (35건)
- 매트릭스: D와 동일 분포, 다른 케이스 ID
- 모든 응답 필드 사전 채움 (MVP 시연 우선)
- **초안 vs 정답 비율**: 일치 21건(60%) / Agent 낙관 10건(29%) / Agent 과민 4건(11%)
- 메시지: 베테랑은 AI보다 더 보수적이고 정확

### Validation Targets
- 반제품 비율 합 = 1.00 ± 0.001
- Bio = 0.03 정확히
- Season ⊂ {winter, deep_winter}
- WAFI 0ppm baseline 분포: 평균 -3°C ± 1°C, [-10, +5]°C ⊂ p5-p95
- WAFI 단조성: Spearman > 0.85
- 라벨 균형: normal ~22%, caution ~46%, risk ~32% (노이즈 적용 전)
- 도메인 검토 (오상훈) 무작위 20건 합리성 통과
