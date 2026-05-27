# Blending Master — PRD v4

## 경유 저온성상과 WAFI 주입량 의사결정을 지원하는 전문가 지식 기반 AI Agent

| 항목 | 내용 |
|---|---|
| 팀명 | CAIO 10기 12조 |
| 제품명 | Blending Master |
| 작성일 | 2026-05-28 |
| 문서 버전 | v4 (구현 반영본) |
| 주요 변경 | v3에서 기획 단계였던 항목 중 실제 구현된 기능을 정리하고, 구현 과정에서 결정된 사양·제약을 반영 |
| 관련 문서 | BRD, PRD v3, PROGRESS-2026-05-19/20/26/28 |
| 코드 저장소 | github.com/stephano329-sketch/CAIO_blendingmaster |

### 핵심 한 줄 설명

> 베테랑 경유 제품 전문가의 판단 기준을 구조화·검색 가능한 지식으로 전환하고, 저연차 연구원의 WAFI 주입량 및 품질 리스크 판단을 ML 예측·RAG 검색·경험치 DB로 지원하는 AI Agent.

---

## 01. 도입 분야 (v3 유지)

경유 저온성상(CFPP/CP/PP) 관리와 WAFI 첨가제 주입량 결정 업무. 본 PoC는 공개 자료 + 합성 데이터 기반 데모 시스템이며, 사업화 단계에서 사내 데이터 보안·권한·검증 정책 별도 적용 전제.

---

## 02. 문제 정의 (v3 유지)

판단 불확실성 / WAFI 과투입 / 재블렌딩 손실 / 베테랑 정년 임박에 따른 지식 휘발. 대안의 한계: 선형모델 비선형 미반영, 문서 저장은 판단 과정 미보존, 도제식 전수의 편차, 범용 LLM의 사내 컨텍스트 부재.

연간 손실 가능 규모(가정 기반): 최대 약 120억 원.

---

## 03. 시스템 구성 (구현 완료)

### 3-1. 아키텍처
- **Frontend**: Next.js 14 (App Router) + React 18 + TypeScript 5.6
- **Backend**: FastAPI + SQLAlchemy 2.0 (SQLite `blending_master.db`)
- **ML**: XGBoost CFPP 회귀 모델 (R² 0.944, MAE 1.16°C)
- **RAG**: ChromaDB persistent client (219건 인덱싱: case 35 / process 56 / production 59 / feedstock 69)
- **LLM**: Anthropic Claude Sonnet 4.6 (옵션, `ANTHROPIC_API_KEY` 미설정 시 RAG 인용 요약 폴백)

### 3-2. 데이터 계층
| 테이블 | 용도 | 행 수 |
|---|---|---|
| `cases` | 시드 케이스 (RAG + 유사 사례 검색 소스) | 35 |
| `decision_logs` | 사용자가 시나리오 채택한 batch 영속 | 동적 |
| `knowledge_entries` | 경험치 DB (지식 추출 결과) | 시드 3 + 사용자 추가 |
| `interview_sessions`, `heuristics`, `veterans` | 향후 확장용 (현재 미사용) | 0 |

ChromaDB는 `chroma_db/` 디렉터리에 영속.

---

## 04. 화면 구성 (구현된 8개 라우트)

```
대시보드          /
신규 판단         /judge
AI 상담           /consult
제품 배합 일지    /journal
─────
지식 추출         /interview
경험치 DB         /kb
RAG 문서 확인     /rag
```

각 화면별 기능:

### 4-1. 대시보드 (`/`)
- Stat 카드 3개: 오늘 처리한 Batch / 이번 달 판단 / 이번 달 절감액(추정 26만원/batch)
- 최근 의사결정 로그 테이블 (최근 10건):
  - 컬럼: 날짜, 로그 ID, 예측 CFPP (WAFI 후), WAFI 제안, 실측 CFPP, 실측 WAFI
  - 실측 컬럼 인라인 편집 (클릭 → 입력 → Enter 저장)
- 빈 상태: "아직 기록된 의사결정이 없습니다. 신규 판단을 실행하면 여기 표시됩니다."

### 4-2. 신규 판단 (`/judge`)
**입력 (2열 레이아웃)**:
- 왼쪽:
  - 블렌딩 구성 (LGO 50 / HGO 12 / LCO 15 / Kero 20 / Bio 3 기본값, 합계 100% 검증)
  - 판단 조건 (목표 CFPP / 계절 [혹한기·동절기] / 탱크 이력 [잔류물 없음·최근 전환·혼합물 잔류] / WAFI 첨가제 종류 [A/B/C/none])
- 오른쪽:
  - 주요 성상 9개 (CP·PP[참고용] / 밀도 / n-파라핀 C10–C15 · C16–C20 · C21+ / 방향족 / 황분 / 세탄)
- 세 섹션 헤더에 PoC placeholder 버튼: 제품 배합 계획 / 제품 운영 계획 / RTDB 분석값 불러오기 (모두 "PoC에서 구현하지 않음" 호버 표시)

**결과**:
- 예측 CFPP 베이스라인 (가로 전체 배너)
- WAFI 추천 시나리오 3장 (비용 최소 / 균형 / 안전 우선)
  - 각 카드: WAFI ppm + 예상 CFPP + 마진 + rationale + 목표 달성/미달성 인디케이터
  - 클릭으로 선택 → 초록 "✓ 선택됨" 배지
  - "균형 (권장)" = 백엔드 기본 priority
- 확인 우선순위 (한글 라벨 매핑)
- 유사 사례 Top 3 (case_id + 유사도% + rule_summary + 호버 시 표 툴팁)
- 액션 버튼: "시나리오 선택" / "AI 상담 요청" / "← 다시 입력"

### 4-3. AI 상담 (`/consult`)
- 상단 Batch 선택 드롭다운 (DB의 `decision_logs`에서 fetch, 기본 = 최근 batch)
- 컨텍스트 바: LGO/HGO/LCO/Kero/Bio % · 목표 CFPP · 계절 · 베이스라인
- 추천 질문 3개 (placeholder)
- 마크다운 렌더링 (`react-markdown` + `remark-gfm`)
- 인용 칩: CASE / PROC / PROD / FEED / RULE / DOC 타입별 색상
- CASE 타입 인용 호버 시 표 툴팁 (`/cases/{id}` fetch + 캐시)
- LLM 미설정 시 "RAG 인용 요약 (LLM 미사용)" 표시

### 4-4. 제품 배합 일지 (`/journal`)
- Stat 3개: 총 일지 / 실측 입력 완료 / 시나리오 채택 완료
- 검색 + 페이지네이션 (10건/페이지)
- 카드:
  - 헤더: log_id + 계절 + 시나리오 칩 (색상 차등: 비용=파랑/균형=주황/안전=초록)
  - 블렌딩 / CFPP·WAFI / 실측(예측차이) / 유사 사례 (호버 툴팁)

### 4-5. 지식 추출 (`/interview`)
- DB의 미인터뷰 케이스 자동 fetch
- 케이스 정보 + Q1~Q5 (판단 / 근거 / 우선순위 / 리스크 / 메모)
- 진행 상태 사이드 패널 (Q1~Q5 답변 완료도)
- 저장 시 `KnowledgeEntry` 생성 → 경험치 DB에 즉시 반영
- "다음 케이스 →" 클릭 시 다음 미인터뷰 케이스 자동 로드

### 4-6. 경험치 DB (`/kb`)
- 필터 칩 (판단별: 정상/주의/위험) + 검색
- 카드: 작성자 + 작성일 + 케이스 메트릭 + Q1~Q5 응답

### 4-7. RAG 문서 확인 (`/rag`)
- 타입 필터 (case/process/production/feedstock)
- 검색 (벡터 유사도)
- 카드 클릭으로 본문 + 메타데이터 펼침
- 페이지네이션 (20건/페이지)

---

## 05. 백엔드 API (구현 완료)

### Judge / 의사결정
- `POST /judge` — XGBoost 예측 + WAFI sweep + 3 시나리오 + 유사 사례. **DB 영속 없음** (선택만 반환).
- `POST /decision-logs` — 사용자 "시나리오 선택" 시점에 DecisionLog 생성. ID: `D-YYMMDD-NNN`
- `PATCH /decision-logs/{log_id}/select-scenario` — 시나리오 변경
- `PATCH /decision-logs/{log_id}/outcome` — 실측 CFPP/WAFI 입력
- `GET /journal/batches?limit=&offset=` — 일지 페이지용 전체 로그
- `GET /dashboard/stats`, `GET /dashboard/recent-logs?limit=`

### Knowledge / 경험치
- `GET /knowledge?decision=&season=&limit=` · `POST /knowledge`

### Interview
- `GET /interview/next-case?skip_done=true` — 미인터뷰 케이스 우선 반환

### Cases / RAG
- `GET /cases`, `GET /cases/{case_id}`
- `GET /rag/types`, `GET /rag/docs?doc_type=&limit=&offset=`, `GET /rag/search?q=&top_k=&doc_type=`

### Consult
- `POST /consult` body `{query, top_k, season?, doc_type?, case_id?}` — RAG 검색 + LLM 생성

---

## 06. ML 모델 (구현 완료)

### 6-1. 학습 파이프라인
- 합성 데이터 생성: `ml/data_generation/synthetic_generator.py` — 500 rows
- 물리 모델 파라미터 (`physical_model.py`):
  - Feedstock baseline CFPP (LGO -6 / HGO +4 / LCO -6 / Kero -40 / Bio +5)
  - WAFI 응답 곡선: Type A max=18 / B max=23 / C max=25 (LCO > 15% 시 30% 감쇠)
  - n-파라핀 분포 보정 (C16-C20 β1=0.7 / C21+ β2=1.4)
  - 탱크 이력 오프셋 (clean 0 / recent_change +1 / mixed +2)
  - 측정 노이즈 σ=0.8°C
- Season-fixed target_cfpp: 동절기 -18 / 혹한기 -23
- Decision 라벨: margin 기반 + 노이즈 5%

### 6-2. 모델
- XGBoost regressor (`cfpp_xgb_v1.pkl`)
- 피처 16개 (blend ratios 5 + 주요 성상 7 + WAFI 2 + season + tank_history)
- 메트릭: **MAE 1.16°C / RMSE 1.43°C / R² 0.944**
- 폴백 heuristic (모델 파일 부재 시): -3.6 + WAFI 효과 + season + paraffin

### 6-3. WAFI 시나리오 추천
- PPM grid: 0~1000 ppm, 25 ppm 간격
- 마진 기준: min_cost +1°C / balanced +3°C / safe +5°C
- 그리드 한계 도달 시 rationale에 "PPM 그리드 한계" 메시지 자동 노출

### 6-4. 신뢰도 산출
2-signal 가중 평균:
- 신호 1 (agreement): top-3 유사 사례 중 최종 decision과 일치 비율
- 신호 2 (margin_signal): decision별 마진 경계 거리
- `confidence = 0.5 × agreement + 0.5 × margin_signal` (clamp 0.30~0.95)
- **UI 미노출** (백엔드 응답에는 보존)

---

## 07. RAG 시스템 (구현 완료)

### 7-1. 인덱싱
- ChromaDB persistent (default embedding)
- 4개 doc_type, 219건
- 메타데이터 필터: `doc_type`, `season`

### 7-2. 검색 파이프라인 (Hybrid)
```
RAG 벡터 검색 (top-20 후보, 넓은 recall)
    ↓
구조적 거리 재정렬 (블렌딩 + 주요 성상 + target CFPP)
    ↓
최종 top-3 + 유사도 = 70% 구조적 + 30% RAG
```

### 7-3. 가중 스케일 (`_STRUCT_SCALES`)
스케일 작을수록 더 민감:
- 가장 민감: LCO 0.05 / Biodiesel 0.02 / C21+ 0.8
- 중간: LGO/HGO/Kero 0.08~0.10 / C16-C20 1.5
- 덜 민감: 방향족/세탄/CFPP 3.0 / 밀도 5.0

### 7-4. 검증
LCO 10% / 25% / 35% 입력에 대해 명확히 다른 케이스 셋 + 유사도 차등화 확인.

---

## 08. 의사결정 영속 규칙

`/judge` 호출은 **저장 안 함**. 사용자가 결과 화면에서 "시나리오 선택" 버튼을 누른 경우에만 `DecisionLog` 생성. 이후 대시보드에서 실측을 인라인 입력하면 같은 로그의 `actual_outcome`이 PATCH로 갱신됨.

| 시점 | 행위 | DB 효과 |
|---|---|---|
| AI 판단 요청 | `/judge` 호출 | 변화 없음 (추천만 반환) |
| 시나리오 카드 클릭 | 프론트 state | 변화 없음 |
| "시나리오 선택" 클릭 | `POST /decision-logs` | **새 로그 생성 (`D-YYMMDD-NNN`)** |
| 대시보드 실측 입력 | `PATCH /outcome` | `actual_outcome` 갱신 |
| 지식 추출 저장 | `POST /knowledge` | `knowledge_entries` 새 행 |

---

## 09. 의도적으로 UI에서 제거된 항목

데이터는 백엔드에서 계속 생성·저장되지만 화면에는 노출하지 않음:
- decision 라벨 (정상/주의/위험) — 대시보드, 신규 판단, AI 상담, 제품 배합 일지에서 모두 제거
- confidence (%) 표시 — 시나리오 카드 conf-bar와 우상단 % 모두 제거
- 실측 CFPP delta (예측 차이) 색상 표시 — 대시보드 셀에서 제거 (제품 배합 일지에는 인라인 "(예측차이 +N°C)" 텍스트로 유지)
- 최적화 우선순위 select — 기본 `balanced` 고정 송신

---

## 10. PoC 비범위 / 다음 단계

### 10-1. PoC에서 구현하지 않음 (placeholder 노출)
- 외부 시스템 연동: RTDB 분석값 · 제품 배합 계획 · 제품 운영 계획 불러오기
- LLM 미설정 시 자연어 응답 (RAG 인용 요약 폴백 대체)

### 10-2. 향후 후보
- AI 상담 추천 질문 컨텍스트 기반 동적화
- 절감액 산출 정교화 (현재 상수 26만원/batch)
- 지식 추출 전체 진행률 (예: 3/35) 사이드 패널 표시
- decision 분류 모델 (현재는 규칙 기반)
- 24/7 호스팅 (Vercel + Railway 또는 Codespaces)
- 실측 outcome 입력 자동 알림 (batch 출하 후 N일 경과 시)

---

## 11. 실행 / 재기동

```powershell
# 백엔드 (스키마/모델 변경 후 한 번 재기동)
cd C:\Claude_home\BlendingMaster
.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000

# 프론트
cd C:\Claude_home\BlendingMaster\frontend
npm install   # 최초 1회 또는 의존성 변경 시
npm run dev

# 합성 데이터 재생성 + 모델 재학습 (파라미터 변경 시)
cd C:\Claude_home\BlendingMaster\ml\data_generation
..\..\.venv\Scripts\python.exe synthetic_generator.py
cd C:\Claude_home\BlendingMaster
.venv\Scripts\python.exe -m ml.training.train_cfpp
```

---

## 12. 변경 이력 (v3 → v4)

| 항목 | v3 (기획 단계) | v4 (구현 완료) |
|---|---|---|
| 화면 수 | 4개 계획 | 7개 구현 (대시보드/신규판단/AI상담/제품배합일지/지식추출/경험치DB/RAG문서확인) |
| ML 모델 | 기획만 | XGBoost R² 0.944 학습 완료 |
| RAG | 기획만 | ChromaDB 219건 + Hybrid 검색 구현 |
| LLM | 기획만 | Claude Sonnet 4.6 옵션 연동 |
| 의사결정 영속 | 미정 | 사용자 선택 시점 영속 + 실측 인라인 입력 |
| 유사 사례 검색 | 미정 | 입력 민감도 검증 완료 |
| WAFI 시나리오 | 3개 계획 | 3개 (비용/균형/안전) + 클릭 선택 |
| 경험치 DB | 미정 | DB 영속 + 지식 추출 자동 fetch 사이클 |
| 배포 | 미정 | GitHub push (호스팅 미진행) |

---

## 13. 코드 통계 (2026-05-28 기준)

- 백엔드: FastAPI 라우터 7개 (judge, cases, consult, rag, dashboard, knowledge, interview)
- 프론트 라우트: 7개 (`app/{,judge,consult,journal,interview,kb,rag}/page.tsx`)
- 모델 파일: `cfpp_xgb_v1.pkl` (1.2 MB)
- ChromaDB: 1.8 MB (219 vectors)
- SQLite: ~230 KB (시드 + 사용자 데이터)
- Git: main branch, 3 commits, 647+ tracked files
