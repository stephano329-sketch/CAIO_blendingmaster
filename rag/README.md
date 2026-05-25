# RAG System — Blending Master MVP

베테랑 경유 품질 전문가의 암묵지 + 공정/생산/반제품 문서를 검색 가능한
지식 자산으로 변환하는 **RAG (Retrieval-Augmented Generation)** 시스템.

PRD §05 기능 1·2·3 (WAFI 시나리오 추천, 상담 Agent, 베테랑 지식 추출)의
근거 검색 레이어를 담당한다.

---

## Overview

### Two-tier RAG Architecture

```
1차 RAG (collection: primary_rag, 56 chunks)
├── A 공정 지식        (7 chunks)   — CDU, HDS, HCC, FCC, Reformer, Blending, Inspection
├── B 경유 생산 흐름   (7 chunks)   — Flow, KS spec, 계절 전략, WAFI ops, BD, 검사, 재블렌딩
├── C 반제품 특성      (7 chunks)   — LGO, HGO, LCO, Kero, Bio, 호환성, 계절 권장 비율
└── D 사례 지식        (35 chunks) — 합성 historical cases (cases.json)

2차 RAG (collection: secondary_rag, 35 chunks)
└── E 베테랑 암묵지    (35 chunks) — 인터뷰 시드 (interview_seeds.json)
```

### Decision (Plan §R1)
- **Embedding**: Voyage AI `voyage-4` (Anthropic 친화 + 다국어 + asymmetric retrieval)
- **Vector DB**: ChromaDB persistent local store
- **Fallback**: ChromaDB 기본 `all-MiniLM-L6-v2` (개발 검증용, 한국어 품질 약함)

자세한 계획: `.moai/plans/rag-data.md`

---

## Directory Structure

```
rag/
├── README.md                       # 이 파일
├── __init__.py
├── embeddings/
│   ├── __init__.py
│   └── voyage_embedder.py          # voyage-4 + fallback embedder
├── indexing/
│   ├── __init__.py
│   ├── code_decoder.py             # PRD 부록 A 25개 코드 영↔한 매핑
│   ├── build_documents.py          # A·B·C md 파일 → chunks
│   ├── build_cases.py              # cases.json → chunks (한국어 narrative)
│   ├── build_heuristics.py         # interview_seeds.json → chunks
│   └── index_all.py                # ChromaDB 적재 메인 (멱등)
├── retrieval/                      # ⏳ 미구현 (Phase 4)
│   └── __init__.py
├── eval/                           # ⏳ 미구현 (Phase 5)
│   └── __init__.py
└── chroma_db/                      # 영속 ChromaDB (gitignored)
    ├── primary/
    └── secondary/
```

---

## Setup

### Dependencies

```bash
pip install chromadb PyYAML voyageai
```

requirements.txt 추가 권장 항목:
```text
chromadb>=1.5.0
PyYAML>=6.0
voyageai>=0.2.0   # voyage-4 출시 시 >=0.3.0 필요할 수 있음
```

### Environment Variables

`.env` (프로젝트 루트, gitignored):
```bash
VOYAGE_API_KEY=pa-...        # https://voyageai.com 에서 발급
ANTHROPIC_API_KEY=sk-ant-... # Claude API용
```

API 키 미설정 시 자동으로 fallback embedder 사용 (검증 가능, 품질 낮음).

---

## Pipeline Architecture

```
[입력 데이터]
data/documents/*/*.md       data/synthetic/cases.json     data/synthetic/interview_seeds.json
        │                            │                              │
        ▼                            ▼                              ▼
build_documents.py          build_cases.py                build_heuristics.py
   21 chunks                   35 chunks                     35 chunks
        │                            │                              │
        └────────────┬───────────────┘                              │
                     ▼                                              ▼
                primary_rag                                  secondary_rag
                (56 chunks)                                   (35 chunks)
                     │                                              │
                     └──────────────────┬───────────────────────────┘
                                        ▼
                              voyage-4 embedding
                                 (or fallback)
                                        ▼
                                   ChromaDB
                              rag/chroma_db/
```

---

## Usage

### 1. Build & Index (Phase 1~3)

```bash
# 한 번에 전체 적재 (멱등 — 재실행 안전)
python -m rag.indexing.index_all

# 강제 재구축 (chroma_db 디렉터리 삭제 후 재인덱싱)
python -m rag.indexing.index_all --reset
```

예상 출력:
```
=== RAG Indexing Pipeline ===
Embedder: voyage-voyage-4   (또는 chromadb-default-MiniLM-L6)
Building chunks...
  documents: 21
  cases:     35
  heuristics: 35
=> Indexing primary_rag (56 chunks)
=> Indexing secondary_rag (35 chunks)
=== Verification ===
  primary_rag.count() = 56
  secondary_rag.count() = 35
OK — counts match
```

### 2. Standalone Module Tests

각 build 스크립트는 독립 실행 가능 (chunk 생성만 검증):

```bash
python -m rag.indexing.build_documents     # 21 chunks
python -m rag.indexing.build_cases         # 35 chunks
python -m rag.indexing.build_heuristics    # 35 chunks
python -m rag.indexing.code_decoder        # 25 codes 출력
python -m rag.embeddings.voyage_embedder   # embedding smoke test
```

### 3. Verification Queries

```python
import chromadb
client = chromadb.PersistentClient(path="rag/chroma_db")

primary = client.get_collection("primary_rag")
secondary = client.get_collection("secondary_rag")

# Count check
assert primary.count() == 56
assert secondary.count() == 35

# Metadata filter
result = primary.get(where={
    "$and": [{"season": "deep_winter"}, {"decision": "risk"}]
})
# → 5 cases (D matrix 정합)

# Semantic search
result = primary.query(query_texts=["혹한기 LCO 효과"], n_results=5)
```

---

## Module Reference

### `embeddings/voyage_embedder.py`

| Class / Function | 용도 |
| --- | --- |
| `VoyageEmbedder` | voyage-4 production embedder, asymmetric retrieval (`embed_documents` / `embed_queries`) |
| `FallbackEmbedder` | ChromaDB 기본 (`all-MiniLM-L6-v2`), 개발 검증용 |
| `get_embedder()` | `VOYAGE_API_KEY` 환경변수 자동 감지하여 적절한 embedder 반환 |

### `indexing/code_decoder.py`

PRD 부록 A의 25개 코드 영↔한 매핑.

| 카테고리 | 코드 수 | 예시 |
| --- | --- | --- |
| `decision` | 3 | `caution` ↔ "주의" |
| `reason` | 9 | `tank_history` ↔ "저장탱크 이력" |
| `check` | 7 | `retest` ↔ "검사 재확인" |
| `risk` | 6 | `within_spec_but_risky` ↔ "기준 내지만 위험 가능성 있음" |

### `indexing/build_documents.py`

A·B·C 마크다운 파일 → `Chunk` 리스트.
- YAML frontmatter 파싱 (`section_id`, `title`, `doc_type`, `lang`, `version`, `source`)
- 토큰 수 ≤ 1000이면 단일 청크, 초과하면 H2 단위 분할
- 출력 메타데이터: `doc_type`, `section_id`, `section_title`, `lang`, `version`, `source` (+ `subsection`)

### `indexing/build_cases.py`

`cases.json` 35건 → 사례 청크.
- 한국어 narrative 자동 생성 (반제품, 검사값, 판단 근거, 사후 결과 포함)
- 영문 코드 + 한글 라벨 모두 포함 → 양방향 검색 가능
- 메타데이터: `case_id`, `season`, `decision`, `reason_codes`, `off_spec`, ...

### `indexing/build_heuristics.py`

`interview_seeds.json` 35건 → 암묵지 청크.
- `rule_summary` 중심으로 RAG 텍스트 구성
- AI 초안 vs 베테랑 정답 패턴 (`match`/`under`/`over`) 명시
- 메타데이터: `case_id`, `season`, `decision`, `ai_draft_decision`, `draft_pattern`, ...

### `indexing/index_all.py`

End-to-end 적재 메인. 멱등성(upsert) 보장.

옵션:
- `--reset`: `rag/chroma_db/` 디렉터리 삭제 후 재인덱싱
- 종료 코드 0: 카운트 정합, 1: 미달

---

## Metadata Schema

ChromaDB는 메타데이터 값에 primitive 타입(str, int, float, bool)만 허용하므로,
배열은 comma-joined 문자열로 저장한다.

### 공통 필드

| 필드 | 타입 | 값 |
| --- | --- | --- |
| `doc_type` | str | `process` / `production` / `feedstock` / `case` / `heuristic` |
| `lang` | str | `ko` |
| `version` | str | `1.0` |
| `source` | str | `synthetic` / `public_doc` 등 |

### A·B·C 문서 전용

| 필드 | 예시 |
| --- | --- |
| `section_id` | `A-01` |
| `section_title` | `CDU (Crude Distillation Unit) 공정 설명` |
| `subsection` | (sub-chunk 시) `공정 목적` |

### D 사례 전용

| 필드 | 예시 |
| --- | --- |
| `case_id` | `DIESEL-D-001` |
| `season` | `winter` / `deep_winter` |
| `decision` | `normal` / `caution` / `risk` |
| `reason_codes` | `metric_variability,tank_history` |
| `check_priority` | `tank_history,blend_ratio,retest` |
| `risk_codes` | `within_spec_but_risky` (또는 빈 문자열) |
| `off_spec` | `False` / `True` |
| `rework_required` | `False` / `True` |
| `source_f_index` | `42` |
| `wafi_type` | `A` / `B` / `C` / `none` |

### E 암묵지 전용

| 필드 | 예시 |
| --- | --- |
| `case_id` | `DIESEL-E-001` |
| `ai_draft_decision` | `normal` / `caution` / `risk` |
| `draft_pattern` | `match` / `under` / `over` |
| (그 외 D와 동일 필드) | |

---

## Verification

### 카운트
- `primary_rag.count() == 56` (21 docs + 35 cases)
- `secondary_rag.count() == 35` (heuristics)

### 메타데이터 필터 정합 (수동 검증 완료)

| 필터 | 기대 결과 | 실측 |
| --- | --- | --- |
| `season=deep_winter AND decision=risk` | 5건 (D 매트릭스 정합) | ✅ 5건 |
| `draft_pattern=under` (secondary) | 10건 (Decision 5 ④ 정합) | ✅ 10건 |
| `decision=normal` (primary, cases) | 10건 | ✅ 10건 |

### Semantic Search Smoke Test

쿼리: `"혹한기 LCO 비율이 높은 케이스에서 WAFI 효과"`

Fallback embedder Top-5:
1. doc:B-07 — 재블렌딩 절차
2. doc:C-06 — 호환성 매트릭스
3. doc:A-06 — 블렌딩 공정
4. doc:B-04 — WAFI 첨가제 운영 ✓ (관련성 높음)
5. doc:C-03 — LCO 반제품 특성 ✓ (관련성 매우 높음)

voyage-4 적용 시 C-03/B-04가 더 상위로, LCO 관련 D 사례도 진입 예상.

---

## Future Work (미구현)

### Phase 4 — Retrieval Layer
- `rag/retrieval/retriever.py`: query embedding + 메타데이터 필터 통합
- `rag/retrieval/search.py`: CLI 검색 도구

### Phase 5 — Evaluation
- `rag/eval/queries.json`: 30~100 사전 라벨링 쿼리
- `rag/eval/run_eval.py`: Top-5 Recall, NDCG@5 측정
- KPI: PRD §11 "유사 사례 검색 정확도 ≥ 80%"

### Backend Integration
- FastAPI `/consult` 엔드포인트 → retriever 호출 → Claude API
- Asymmetric embedding 활용 (`embed_queries()` 직접 호출)

---

## Troubleshooting

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| `RuntimeError: VOYAGE_API_KEY env var is required` | API 키 미설정 | `.env`에 `VOYAGE_API_KEY` 추가 또는 fallback 자동 사용 허용 |
| `ModuleNotFoundError: voyageai` | 패키지 미설치 | `pip install voyageai` |
| `primary_rag.count() < 56` | 데이터 파일 누락 | `data/documents/*.md`, `data/synthetic/cases.json` 존재 확인 |
| 한국어 검색 결과가 영어 문서를 우선 반환 | fallback embedder 사용 중 | `VOYAGE_API_KEY` 설정 필요 |
| ChromaDB 손상 (`KeyError`, `corrupt collection`) | 강제 종료 등 | `python -m rag.indexing.index_all --reset` |
| 적재 시 `Metadata value of type list not supported` | comma-join 누락 | build 스크립트에서 list → "," 조합 확인 |

---

## Plan & Source References

- **Plan**: `.moai/plans/rag-data.md` (Decision R1 확정)
- **PRD**: `Blending_Master_PRD_v2_3.md` §05 (RAG 기능), §08 (기술), §11 (KPI)
- **BRD**: `BRD_Diesel_RAG_Detailed_Final.md` §11 (RAG 동작 방식), §8 (코드 체계)
- **선행 데이터**: `.moai/plans/prd-snug-orbit.md` (synthetic data, 6개 결정 확정)
- **문서 소스**: `data/documents/README.md`
