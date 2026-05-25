# RAG Data & Indexing Plan — Blending Master MVP

## Context

Synthetic data generation(`prd-snug-orbit.md`)이 완료되어 다음 자산이 준비됨:
- **Dataset F** (`ml_training.csv`, 500건) — XGBoost용
- **Dataset D** (`cases.json`, 35건) — RAG 사례 검색용
- **Dataset E-seed** (`interview_seeds.json`, 35건) — 인터뷰 Agent 시연용
- **A·B·C 문서** (`data/documents/`, 21 파일) — RAG 문서 지식

본 계획은 위 자산을 **voyage-4 + ChromaDB** 기반 RAG 시스템으로 적재하는 절차를 정의한다.

## Source Documents

- PRD: `Blending_Master_PRD_v2_3.md` §05 (RAG 기능), §08 (기술 스택)
- BRD: `BRD_Diesel_RAG_Detailed_Final.md` §11 (RAG 동작 방식)
- 선행 plan: `.moai/plans/prd-snug-orbit.md` (synthetic data)
- 문서: `data/documents/README.md`

## Architecture

```
1차 RAG (collection: primary_rag)
├── A 공정 (7 chunks)
├── B 경유 생산 (7 chunks)
├── C 반제품 (7 chunks)
└── D 사례 (35 chunks, narrative 임베딩)
                                                ┐
2차 RAG (collection: secondary_rag)             │ voyage-4
└── E 암묵지 (35 chunks, rule_summary 중심)      │ embedding
                                                ┘
            ↓
    ChromaDB (local, persistent)
            ↓
    Retriever → LLM (Claude API)
```

## Decision Log

| # | 항목 | 상태 | 확정 값 |
| --- | --- | --- | --- |
| **R1** | 임베딩 모델 + Vector DB | ✅ 확정 | **voyage-4 + ChromaDB** (Anthropic 친화, 다국어 지원) |
| R2 | A·B·C 작성 방식 | ✅ 완료 | 옵션 ②+③ 하이브리드 (LLM 보조 + 공개자료 + 도메인 검토 예정) |
| R3 | A·B·C 분량 | ✅ 완료 | PRD 명시 분량 충실 (총 21 섹션, ~19,500 토큰) |
| R4 | Chunking 단위 | ⏸ | 섹션 단위 / 단락 단위 / 고정 토큰 |
| R5 | 평가셋 규모 | ⏸ | 30 / 50 / 100 쿼리 |

## R1 상세 — voyage-4 + ChromaDB

### Voyage AI voyage-4 선택 근거

1. **Anthropic 공식 추천 임베딩 파트너** — Claude API와의 친화성
2. **다국어 지원** — 한국어 임베딩 품질 우수 (ko-sbert 수준)
3. **Asymmetric retrieval** — `input_type="document"` vs `"query"` 구분으로 검색 정확도 ↑
4. **PRD 원칙 부합** — 외부 LLM 의존 없이 (OpenAI 키 불필요)
5. **구현 단순** — `voyageai` Python SDK + ChromaDB 통합 간단

### 비용 추정 (MVP 규모)

| 항목 | 토큰 수 | 단가 (가정) | 비용 |
| --- | --- | --- | --- |
| 1차 적재 (A+B+C+D+E) | ~50,000 토큰 | $0.18/1M | $0.009 |
| 평가셋 쿼리 100회 | ~10,000 토큰 | $0.18/1M | $0.002 |
| 시연 인터랙티브 | ~50,000 토큰 | $0.18/1M | $0.009 |
| **합계 (MVP)** | | | **< $0.05** |

> 단가는 voyage-3-large 기준 추정. voyage-4 정식 가격은 출시 시점에 재산정.

### ChromaDB 통합 패턴

```python
# rag/embeddings/voyage_embedder.py
import os
from typing import Iterable, List

import voyageai


class VoyageEmbedder:
    """
    Voyage AI voyage-4 wrapper for ChromaDB.

    Supports asymmetric embedding (document vs query input types) for
    better retrieval accuracy. ChromaDB default treats embeddings as
    symmetric, so we expose two methods and call the appropriate one
    at indexing vs search time.
    """

    MODEL = "voyage-4"

    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        if not api_key:
            raise RuntimeError("VOYAGE_API_KEY env var required")
        self.client = voyageai.Client(api_key=api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        result = self.client.embed(
            texts=texts, model=self.MODEL, input_type="document"
        )
        return result.embeddings

    def embed_queries(self, texts: List[str]) -> List[List[float]]:
        result = self.client.embed(
            texts=texts, model=self.MODEL, input_type="query"
        )
        return result.embeddings

    # ChromaDB EmbeddingFunction protocol (called at indexing)
    def __call__(self, input: Iterable[str]) -> List[List[float]]:
        return self.embed_documents(list(input))
```

```python
# rag/indexing/index_all.py
import chromadb
from chromadb.config import Settings

from rag.embeddings.voyage_embedder import VoyageEmbedder

embedder = VoyageEmbedder()

client = chromadb.PersistentClient(
    path="rag/chroma_db",
    settings=Settings(anonymized_telemetry=False),
)

primary = client.get_or_create_collection(
    name="primary_rag",
    embedding_function=embedder,
    metadata={"hnsw:space": "cosine"},
)

secondary = client.get_or_create_collection(
    name="secondary_rag",
    embedding_function=embedder,
    metadata={"hnsw:space": "cosine"},
)
```

```python
# rag/retrieval/retriever.py — search-time query embedding
def retrieve(query: str, collection, n_results: int = 5, where: dict = None):
    query_embedding = embedder.embed_queries([query])[0]
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,  # metadata filter
    )
```

### 환경 변수

```bash
# .env (gitignored)
VOYAGE_API_KEY=pa-...
ANTHROPIC_API_KEY=sk-ant-...
CHROMA_DB_PATH=./rag/chroma_db
```

### Python 의존성 (추가)

```text
voyageai>=0.3.0     # voyage-4 지원 버전
chromadb>=0.5.0
```

## Plan — Implementation Steps

### Phase 1: Embedding 모듈 + 환경 설정

| 단계 | 산출물 | 비고 |
| --- | --- | --- |
| 1.1 `rag/` 디렉터리 스캐폴딩 | `embeddings/`, `indexing/`, `retrieval/`, `eval/` | |
| 1.2 `voyage_embedder.py` | VoyageEmbedder 클래스 | document/query 분리 |
| 1.3 `.env.example` 추가 | VOYAGE_API_KEY 템플릿 | `.env`는 gitignore |
| 1.4 의존성 추가 | `requirements.txt`에 voyageai | |
| 1.5 smoke test | 임베딩 1건 호출 → 차원 확인 | voyage-4 차원 ~1024 예상 |

### Phase 2: 코드 디코더 + 빌드 스크립트

| 단계 | 산출물 | 비고 |
| --- | --- | --- |
| 2.1 `code_decoder.py` | 영문↔한글 25개 코드 매핑 | PRD 부록 A 기반 |
| 2.2 `build_documents.py` | A·B·C md → chunks + metadata | YAML frontmatter 파싱 |
| 2.3 `build_cases.py` | cases.json → narrative + 코드 디코딩 | D 35건 |
| 2.4 `build_heuristics.py` | interview_seeds.json → rule_summary 중심 | E 35건 |

### Phase 3: 적재

| 단계 | 산출물 | 비고 |
| --- | --- | --- |
| 3.1 `index_all.py` | ChromaDB primary + secondary 적재 | 멱등 (재실행 안전) |
| 3.2 적재 검증 | count, sample query | primary 56건 / secondary 35건 |

### Phase 4: 검색 인터페이스

| 단계 | 산출물 | 비고 |
| --- | --- | --- |
| 4.1 `retriever.py` | 쿼리 → Top-K 결과 + metadata filter | asymmetric embedding 적용 |
| 4.2 CLI 도구 | `python -m rag.retrieval.search "혹한기 LCO 高 케이스"` | 시연용 |

### Phase 5: 평가

| 단계 | 산출물 | 비고 |
| --- | --- | --- |
| 5.1 `eval/queries.json` | 30~100 라벨링된 쿼리 (R5) | 케이스 ID + 섹션 ID 정답 |
| 5.2 `eval/run_eval.py` | Top-5 Recall, NDCG@5 측정 | KPI: Recall ≥ 80% |
| 5.3 결과 리포트 | `eval/results.json` | 통과/미달 보고 |

## Chunking Strategy

R4 미정이지만 본 계획에서는 다음 기본값으로 진행:

| 데이터 | 청크 단위 | 토큰 수 | 예상 청크 수 |
| --- | --- | --- | --- |
| A·B·C 문서 | **섹션 1개 = 1 청크** | 400~800 | 21 |
| D 사례 | **케이스 1건 = 1 청크** | ~400 | 35 |
| E 암묵지 | **시드 1건 = 1 청크** | ~350 | 35 |

큰 섹션(>1,000 토큰)은 H2 단위로 sub-chunking. 본 시스템 평균 토큰 수 ~700이므로 단일 청크가 자연스러움.

## Metadata Schema

### Primary RAG 공통

```json
{
  "doc_type": "process | production | feedstock | case",
  "lang": "ko",
  "version": "1.0",
  "source": "synthetic | public_doc | internal_case"
}
```

### A·B·C 문서 전용

```json
{
  "section_id": "A-01",
  "section_title": "CDU 공정 설명",
  "subsection": null  // sub-chunking 시
}
```

### D 사례 전용

```json
{
  "case_id": "DIESEL-D-001",
  "season": "winter | deep_winter",
  "decision": "normal | caution | risk",
  "reason_codes": ["metric_variability", "tank_history"],
  "off_spec": false,
  "source_f_index": 42
}
```

### Secondary RAG (E)

```json
{
  "case_id": "DIESEL-E-001",
  "season": "winter | deep_winter",
  "decision": "normal | caution | risk",
  "reason_codes": ["metric_variability", "tank_history"],
  "draft_pattern": "match | under | over",
  "source_f_index": 67
}
```

## Critical Files to Create

```
rag/
├── embeddings/
│   ├── __init__.py
│   └── voyage_embedder.py        # voyage-4 wrapper + ChromaDB integration
├── indexing/
│   ├── __init__.py
│   ├── code_decoder.py           # PRD 부록 A 영문↔한글 매핑
│   ├── build_documents.py        # A·B·C md → chunks
│   ├── build_cases.py            # cases.json → RAG text
│   ├── build_heuristics.py       # interview_seeds.json → RAG text
│   └── index_all.py              # ChromaDB 적재 메인
├── retrieval/
│   ├── __init__.py
│   ├── retriever.py              # query embedding + 메타데이터 필터
│   └── search.py                 # CLI 검색 도구
├── eval/
│   ├── __init__.py
│   ├── queries.json              # 사전 라벨링 쿼리셋 (R5에 따라 30~100)
│   ├── run_eval.py               # Top-5 Recall, NDCG@5 측정
│   └── results.json              # 평가 결과
├── chroma_db/                    # gitignored
└── README.md                     # 사용법 + 재현 절차
```

## Verification

### Phase 3 적재 후
```bash
python -c "
import chromadb
client = chromadb.PersistentClient(path='rag/chroma_db')
print('primary_rag:', client.get_collection('primary_rag').count())
print('secondary_rag:', client.get_collection('secondary_rag').count())
"
# Expected: primary_rag: 56, secondary_rag: 35
```

### Phase 4 검색 smoke test
```bash
python -m rag.retrieval.search "혹한기 LCO 비율이 높은데 WAFI를 더 넣어야 할까?"
# Expected: Top-5에 LCO 관련 D 사례, B-04 WAFI Ops, C-03 LCO 섹션 포함
```

### Phase 5 KPI
- **Top-5 Recall ≥ 80%** (PRD §11)
- **메타데이터 필터 정확도 = 100%** (`season=winter` 검색이 deep_winter를 반환 안 함)
- **검색 응답 시간 < 1s** (100회 호출 평균)

## Open Decisions

| # | 항목 | 검토 시점 |
| --- | --- | --- |
| R4 | Chunking 단위 (섹션 / 단락 / 고정 토큰) | Phase 2 시작 전 |
| R5 | 평가셋 규모 (30 / 50 / 100) | Phase 5 시작 전 |

기본값(섹션 단위, 30 쿼리)으로 진행하다 평가 결과에 따라 조정.

## Risks & Mitigation

| 위험 | 영향 | 완화 |
| --- | --- | --- |
| Voyage API 키 발급 지연 | Phase 1 시작 불가 | Phase 1.1~1.4 코드 작성 선행, smoke test만 키 필요 |
| voyage-4 출시 지연 또는 가격 변경 | 모델 변경 필요 | `MODEL = "voyage-4"` 한 곳만 수정하면 다른 voyage 모델로 fallback (voyage-3-large 등) |
| 한국어 임베딩 품질 미흡 | Recall < 80% | 평가셋으로 사전 측정, 미달 시 ko-sbert로 fallback |
| ChromaDB persistent 손상 | 재적재 필요 | `index_all.py` 멱등 보장, 5분 내 재구축 |
| 코드 디코딩 누락 | 한글 쿼리 매칭 실패 | `code_decoder.py` 양방향 매핑 + 테스트 케이스 |
| Voyage rate limit | 적재 지연 | 배치 크기 32~64로 분할, exponential backoff |
