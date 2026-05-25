# Blending Master — Backend (Phase 1 + 2)

Phase 1: FastAPI scaffold + SQLite models + `cases.json` loader + XGBoost CFPP predictor + `POST /judge`.
Phase 2: ChromaDB RAG over 21 markdown docs (A·B·C) + 35 cases + `POST /consult` + RAG-based `similar_cases` in `/judge`.

Interview (`/interview/*`) endpoints arrive in Phase 3.

## Quick start (Windows / Git Bash)

```bash
# From project root: C:\Claude_home\BlendingMaster

# 1. Create venv (Python 3.11 recommended; 3.14 may have wheel gaps)
/c/Python314/python.exe -m venv .venv
source .venv/Scripts/activate

# 2. Install deps
pip install -r backend/requirements.txt

# 3. Initialize DB + load 30+ synthetic cases
python -m backend.db.init_db

# 4. Train the XGBoost CFPP model (~30s on 500 records)
python -m ml.training.train_cfpp

# 5. Build the RAG index (21 docs + 35 cases; first run downloads ~80MB embedding model)
python -m rag.indexing.index_documents --reset

# 6. Run the API
uvicorn backend.main:app --reload --port 8000
```

Optional: set `ANTHROPIC_API_KEY` in `.env` to enable real Claude answers on `/consult`.
Without the key, `/consult` returns a deterministic citation-only summary.

Visit:
- http://localhost:8000/         — service metadata
- http://localhost:8000/docs     — Swagger UI
- http://localhost:8000/health   — liveness

## Tests

```bash
pytest backend/tests -v
```

The test suite uses a separate `test_blending_master.db` and seeds one fixture case.
ML model file is optional — the predictor falls back to a heuristic estimator if
`ml/models/cfpp_xgb_v1.pkl` is missing, so tests run without training.

## API

### `POST /judge`

Quality assessment + 3 WAFI scenarios (min_cost / balanced / safe).

**Request example:**

```json
{
  "blend_components": {"lgo": 0.6, "hgo": 0.15, "lco": 0.1, "kero": 0.12, "biodiesel": 0.03},
  "key_metrics": {
    "density_15c": 840.0,
    "n_paraffin_c10_c15": 10.0,
    "n_paraffin_c16_c20": 9.0,
    "n_paraffin_c21_plus": 2.0,
    "aromatic_content": 24.0,
    "sulfur_ppm": 8.0,
    "cetane_index": 49.0,
    "wafi_type": "A",
    "wafi_ppm": 0.0
  },
  "target_cfpp": -8.0,
  "season": "winter",
  "tank_history_flag": "clean",
  "priority": "balance"
}
```

**Response:**

```json
{
  "decision": "caution",
  "predicted_cfpp_baseline": -3.4,
  "confidence": 0.62,
  "scenarios": [
    {"label": "min_cost",  "wafi_type": "A", "wafi_ppm": 200, "predicted_cfpp": -7.2, "margin_to_target": -0.8, "confidence": 0.55, "rationale": "..."},
    {"label": "balanced",  "wafi_type": "A", "wafi_ppm": 275, "predicted_cfpp": -11.3, "margin_to_target": 3.3, "confidence": 0.73, "rationale": "..."},
    {"label": "safe",      "wafi_type": "A", "wafi_ppm": 350, "predicted_cfpp": -13.8, "margin_to_target": 5.8, "confidence": 0.85, "rationale": "..."}
  ],
  "check_priority": ["retest", "blend_ratio", "additive_dose"],
  "similar_cases": [
    {"case_id": "DIESEL-D-001", "decision": "normal", "similarity_score": 0.78, "rule_summary": "..."}
  ],
  "applied_heuristics": []
}
```

### `GET /cases`, `GET /cases/{case_id}`

Browse the loaded case library. Supports `?season=winter&decision=caution&limit=20`.

### `POST /consult`  (Phase 2)

RAG-based natural-language consultation. Pulls top-K relevant chunks from the
primary collection (process docs + production docs + feedstock docs + cases),
optionally filtered by `doc_type` (`process`/`production`/`feedstock`/`case`),
`season`, or a specific `case_id`. Generates an answer with Claude (if
`ANTHROPIC_API_KEY` is set) or a citation-only summary otherwise.

**Request:**

```json
{
  "query": "혹한기에 LCO 비율이 높을 때 WAFI 투입 전략은?",
  "top_k": 5,
  "doc_type": null,
  "season": null,
  "case_id": null
}
```

**Response (used_llm=false fallback):**

```json
{
  "answer": "질의: ... 관련 근거(요약): ...",
  "used_llm": false,
  "model": null,
  "retrieved_count": 5,
  "citations": [
    {"doc_id": "C-03-lco", "doc_type": "feedstock", "section_title": "2. WAFI 효과 감쇠", "similarity_score": 0.68, "preview": "LCO 비율 > 15% → WAFI 효과 30% 감쇠..."}
  ]
}
```

## Architecture (Phase 1 + 2)

```
backend/
├── main.py                  FastAPI app + CORS + routers
├── db/
│   ├── database.py          SQLAlchemy engine + session
│   └── init_db.py           Create schema + load cases.json
├── models/                  SQLAlchemy ORM models
│   ├── case.py              Case (from cases.json)
│   ├── heuristic.py         Heuristic (Phase 3)
│   ├── interview_session.py Interview state (Phase 3)
│   ├── veteran.py           Veteran profile (Phase 3)
│   └── decision_log.py      User selections
├── schemas/
│   ├── judge.py             /judge Pydantic v2 schemas
│   └── consult.py           /consult Pydantic v2 schemas
├── engine/
│   ├── ml_predictor.py      XGBoost wrapper + heuristic fallback
│   ├── similar_cases.py     Numeric-distance fallback (when RAG unavailable)
│   ├── rag_retriever.py     ChromaDB primary-collection retriever
│   └── llm_client.py        Anthropic Claude wrapper + offline fallback
├── services/
│   ├── recommend_service.py /judge orchestrator (ML + WAFI sweep + RAG)
│   └── consult_service.py   /consult orchestrator (RAG → LLM/fallback)
├── routers/
│   ├── judge.py             POST /judge
│   ├── consult.py           POST /consult
│   └── cases.py             GET /cases, GET /cases/{id}
└── tests/                   pytest with TestClient

rag/
├── config.py                ChromaDB paths + collection names
├── indexing/
│   ├── chunker.py           H2/H3 markdown chunker
│   └── index_documents.py   Build primary RAG from data/documents + cases.json
└── retrieval/               (reserved for reranker, Phase 3)

ml/training/train_cfpp.py    XGBoost training on data/synthetic/ml_training.csv
chroma_db/                   ChromaDB persistent storage (gitignored)
```

## Decision logic (current)

1. Predict baseline CFPP at `wafi_ppm=0`
2. Sweep WAFI ppm 0–600 (step 25) → list of (ppm, CFPP)
3. For each scenario margin (cost=1°C / balanced=3°C / safe=5°C),
   pick smallest ppm whose predicted CFPP ≤ target − margin
4. Combine margin-based judgment with similar-case majority vote
5. Generate check priority based on decision + tank history + season

## Known limitations (Phase 2)

- No heuristic rules engine yet — `applied_heuristics` always returns `[]` (Phase 3)
- No interview endpoints — `/interview/*` arrives in Phase 3 with secondary RAG population
- LLM fallback returns citation-only summary; set `ANTHROPIC_API_KEY` to enable real Claude answers
- No authentication — demo-user only (per PRD non-goals)
- WAFI sweep uses fixed grid 0–600 by 25; production would use binary search
- Embedding model is ChromaDB default (`all-MiniLM-L6-v2`); domain-tuned embeddings deferred

## Updating the RAG index

```bash
# Re-index after editing data/documents/*.md or cases.json
python -m rag.indexing.index_documents --reset
```

Add the `--reset` flag to drop and rebuild; omit it to upsert in place.
