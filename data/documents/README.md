# RAG Document Repository — Blending Master MVP

이 디렉터리는 **1차 RAG (Primary RAG)** 의 문서 데이터(A·B·C)를 보관한다.
`cases.json`(D)과 `interview_seeds.json`(E)은 `../synthetic/`에 별도 저장되어 있으며,
RAG 인덱싱 시 함께 적재된다.

## 디렉터리 구조

```
data/documents/
├── A-process/          # 공정 지식 (CDU, HDS, HCC, FCC, Reformer, Blending, Inspection)
│   ├── A-01-cdu.md
│   ├── A-02-hds.md
│   ├── A-03-hydrocracker.md
│   ├── A-04-fcc.md
│   ├── A-05-reformer.md
│   ├── A-06-blending.md
│   └── A-07-inspection.md
├── B-production/       # 경유 생산 흐름·운영
│   ├── B-01-flow.md
│   ├── B-02-ks-spec.md
│   ├── B-03-seasonal-strategy.md
│   ├── B-04-wafi-ops.md
│   ├── B-05-biodiesel.md
│   ├── B-06-pre-shipment-inspection.md
│   └── B-07-rework.md
└── C-feedstock/        # 반제품 특성
    ├── C-01-lgo.md
    ├── C-02-hgo.md
    ├── C-03-lco.md
    ├── C-04-kerosene.md
    ├── C-05-biodiesel.md
    ├── C-06-compatibility.md
    └── C-07-seasonal-recommendations.md
```

## 파일 형식

각 마크다운 파일은 YAML frontmatter + 본문 + 출처 섹션으로 구성된다.

```markdown
---
section_id: A-01
title: CDU 공정 설명
doc_type: process
lang: ko
source: 합성 (공개 정유공정 자료 기반)
version: 1.0
---

# A-01. ...

본문...

## 출처
- ...
```

### Frontmatter 필드

| 필드 | 필수 | 설명 |
| --- | --- | --- |
| `section_id` | ✅ | 고유 식별자 (e.g., `A-01`) |
| `title` | ✅ | 한국어 제목 |
| `doc_type` | ✅ | `process` / `production` / `feedstock` |
| `lang` | ✅ | `ko` (한국어 본문) |
| `source` | ✅ | 출처 분류 (합성 / 공개자료 / 베테랑 인터뷰) |
| `version` | ✅ | 버전 (현재 1.0) |

## RAG Chunking 가이드

각 마크다운 파일은 **하나의 RAG chunk**로 처리하는 것을 권장한다. 토큰 수가 많은 파일(>1000 tokens)은 본문 내 H2 단위로 sub-chunking 가능.

### Chunking 메타데이터 (ChromaDB 적재 시 사용)

```json
{
  "doc_type": "process | production | feedstock",
  "section_id": "A-01",
  "section_title": "CDU 공정 설명",
  "lang": "ko",
  "version": "1.0",
  "subsection": "CDU 운전 조건"  // sub-chunk 시
}
```

## 컨텐츠 일관성 정책

본 문서들은 다음 원칙으로 작성되었다:

1. **`physical_model.py`의 상수와 정합**:
   - LGO baseline CFPP -6°C, HGO +14°C, LCO -6°C, Kero -40°C, Bio +5°C
   - WAFI Type A/B/C 응답 곡선
   - LCO > 15% → WAFI 효과 0.7배 감쇠

2. **PRD `target_cfpp` 변수와 정합**:
   - 시즌 고정이 아니라 사용자 입력 (제품 등급별 다양)

3. **한국 KS M 2610 규격 + RFS 의무 (BD 3%) 반영**

## 향후 작업

- [ ] **R1 임베딩 모델 결정** (Voyage / 로컬 ko-sbert / ChromaDB 기본)
- [ ] **`rag/indexing/build_documents.py`** 작성: 마크다운 → ChromaDB 적재
- [ ] **`rag/indexing/build_cases.py`** 작성: cases.json → ChromaDB 적재
- [ ] **`rag/indexing/build_heuristics.py`** 작성: interview_seeds.json → ChromaDB 적재
- [ ] **사전 라벨링 평가셋** 30~50 쿼리 작성
- [ ] **Top-5 Recall ≥ 80%** KPI 측정

## 통계

- **A 문서**: 7 파일, 약 5,500 토큰
- **B 문서**: 7 파일, 약 6,500 토큰
- **C 문서**: 7 파일, 약 7,500 토큰
- **합계**: 21 파일, **약 19,500 토큰**

PRD §09의 분량 가이드(A 10-15p, B 10-15p, C 15-20p, 도합 약 35-50p ≈ 18,000-25,000 토큰)와 부합.

## 출처 정책

본 데이터는 **합성·공개 자료 기반**이며 **사내 실데이터 미사용**.
- 인용된 표준(KS, ASTM, ISO)은 공개 표준 식별자만 표기
- 정유사 내부 절차서는 "공개된 일반 원칙"으로 추상화
- 첨가제사 기술 자료는 공개 제품 데이터시트 수준만 인용
