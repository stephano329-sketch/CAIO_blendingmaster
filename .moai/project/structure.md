# Blending Master — Project Structure

## Architecture Pattern

**Fullstack Monorepo** with a clear frontend / backend / ML / RAG separation.  
Architecture style: **Layered Hybrid** (REST API gateway → service layer → Hybrid Engine → storage).

```
BlendingMaster/
├── frontend/          # Next.js 14 App Router, Tailwind CSS, shadcn/ui
├── backend/           # FastAPI, Python 3.11, async LLM integration
├── ml/                # XGBoost training, evaluation, synthetic data generation
├── rag/               # ChromaDB indexing, embedding pipelines, RAG utilities
├── data/              # Raw documents (A-D), synthetic cases (F), code system (G)
├── docs/              # Domain documentation, PRD, BRD, requirements
├── demo/              # Demo scenarios, presentation assets
├── planning/          # Requirements, roadmap, sprint planning
├── infra/             # Deployment configuration (Vercel, Railway)
└── .moai/             # MoAI project metadata and configuration
```

## Directory Purposes

### `frontend/`

Next.js 14 App Router application. Contains all 4 MVP screens:

```
frontend/
├── app/
│   ├── page.tsx               # S-001: Main Dashboard
│   ├── judge/
│   │   └── page.tsx           # S-002: New Judgment Input & Result
│   ├── interview/
│   │   └── page.tsx           # S-003: Veteran Knowledge Extraction Agent
│   └── consult/
│       └── page.tsx           # S-004: Blending Master AI Consultation
├── components/
│   ├── ui/                    # shadcn/ui base components
│   ├── dashboard/             # Dashboard widgets, batch list, log cards
│   ├── judge/                 # Input form, result cards, scenario comparison
│   ├── interview/             # Q1–Q5 multiple-choice interview UI
│   └── consult/               # Chat interface, citation display
├── lib/
│   ├── api.ts                 # API client (typed fetch wrapper)
│   └── types.ts               # Shared TypeScript types
├── public/                    # Static assets
└── design/                    # UI wireframes, design assets
```

**Key UI Screens**:

| Screen | Purpose |
|---|---|
| S-001 Main Dashboard | Current batch overview, recent decision log, navigation hub |
| S-002 New Judgment | Multi-step input → AI request → result card with 3 WAFI scenarios |
| S-003 Veteran Interview | Q1–Q5 structured multiple-choice knowledge extraction session |
| S-004 Consultation | RAG-backed conversational assistant with citation display |

### `backend/`

FastAPI application exposing REST API endpoints.

```
backend/
├── main.py                    # FastAPI application entry point
├── routers/
│   ├── judge.py               # POST /judge — quality assessment + recommendation
│   ├── interview.py           # POST /interview/start, /interview/respond
│   └── consult.py             # POST /consult — RAG-based conversation
├── services/
│   ├── recommend_service.py   # WAFI scenario generation orchestration
│   ├── interview_service.py   # Multiple-choice coding + storage
│   └── consult_service.py     # RAG query + LLM response generation
├── engine/
│   ├── hybrid_engine.py       # Orchestrates ML + RAG + LLM layers
│   ├── ml_predictor.py        # XGBoost inference wrapper
│   └── rag_retriever.py       # ChromaDB query + metadata filter
├── models/
│   ├── case.py                # Case data model (SQLite ORM)
│   ├── heuristic.py           # Heuristic data model
│   ├── interview_session.py   # InterviewSession data model
│   ├── veteran.py             # Veteran profile data model
│   └── decision_log.py        # DecisionLog data model
├── db/
│   ├── database.py            # SQLite connection and session management
│   └── init_db.py             # Schema initialization script
├── schemas/                   # Pydantic request/response schemas
└── tests/                     # pytest test suite (target ≥ 70% coverage)
```

**Core API Endpoints**:

| Endpoint | Method | Purpose |
|---|---|---|
| `/judge` | POST | Submit blend input → receive quality judgment + 3 WAFI scenarios |
| `/interview/start` | POST | Start veteran knowledge extraction session |
| `/interview/respond` | POST | Submit Q1–Q5 responses for a case |
| `/consult` | POST | Submit natural-language question → RAG + LLM answer |
| `/cases` | GET | List cases (with filter) |
| `/heuristics` | GET | List heuristics |
| `/decision-logs` | GET | List decision logs |

### `ml/`

XGBoost model training and synthetic data generation.

```
ml/
├── data_generation/
│   ├── synthetic_generator.py     # Latin Hypercube Sampling + noise injection
│   └── validation.py              # Domain expert constraint checking
├── training/
│   ├── train_cfpp.py              # XGBoost CFPP prediction model training
│   └── evaluate.py                # MAE, R², confusion matrix evaluation
├── models/
│   └── cfpp_xgb_v1.pkl            # Serialized trained model artifact
└── notebooks/                     # EDA and feature importance analysis
```

**ML Feature Set**:

| Category | Features |
|---|---|
| Blend ratios | lgo_ratio, hgo_ratio, lco_ratio, kero_ratio, biodiesel_ratio |
| Properties | density_15c, n_paraffin_c10_c15, n_paraffin_c16_c20, n_paraffin_c21_plus |
| Properties | aromatic_content, sulfur_ppm, cetane_index |
| WAFI | wafi_type, wafi_ppm |
| Environment | season, tank_history_flag |

### `rag/`

ChromaDB vector database management and retrieval utilities.

```
rag/
├── indexing/
│   ├── index_documents.py         # A-D document ingestion and embedding
│   └── index_interviews.py        # E (tacit knowledge) RAG update pipeline
├── retrieval/
│   ├── retriever.py               # Vector similarity search + metadata filter
│   └── reranker.py                # Optional: rerank by relevance score
├── embeddings/
│   └── embed_utils.py             # Embedding model wrapper
└── chroma_db/                     # ChromaDB local storage (gitignored)
    ├── primary/                   # Collections: A-D documents + cases
    └── secondary/                 # Collection: E tacit knowledge
```

**RAG Collections**:

| Collection | Content | Purpose |
|---|---|---|
| `process_docs` (A) | CDU/HDS/Hydrocracker process descriptions | Base context for LLM |
| `production_docs` (B) | Diesel production and blending flow | Production structure understanding |
| `feedstock_docs` (C) | LGO/HGO/LCO properties | Blend composition context |
| `case_docs` (D) | Synthetic quality issue cases | Similar case search |
| `tacit_knowledge` (E) | Veteran interview results | Real judgment layer |

### `data/`

Raw data assets — all MVP data is public or synthetic.

```
data/
├── documents/                     # A-D source documents (markdown/PDF)
│   ├── process/                   # A: Process knowledge docs
│   ├── production/                # B: Diesel production knowledge
│   ├── feedstock/                 # C: Feedstock characteristics
│   └── cases/                     # D: Quality issue case docs
├── synthetic/
│   ├── cases.json                 # 30–50 synthetic quality cases
│   ├── ml_training.csv            # 200–500 ML training records
│   └── interview_seeds.json       # 35 diversity-matrix interview seed cases
└── codes/
    └── code_system.json           # decision/reason/check/risk code definitions
```

### `docs/` and `planning/`

Project and requirements documentation.

```
docs/
├── Blending_Master_PRD_v2_3.md    # Product Requirements Document
├── BRD_Diesel_RAG_Detailed_Final.md # Business Requirements Document
└── requirements/                  # Detailed requirements breakdown

planning/
├── roadmap.md                     # Phase 0–4 implementation schedule
└── sprint_planning/               # Weekly sprint task lists
```

### `infra/`

Deployment configuration for demo environment.

```
infra/
├── vercel.json                    # Frontend deployment (Vercel)
├── railway.toml                   # Backend deployment (Railway)
└── .env.example                   # Environment variable template
```

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  Next.js (Vercel)                                       │
│  S-001 Dashboard | S-002 Judge | S-003 Interview | S-004 │
└──────────────────────────┬──────────────────────────────┘
                           │ REST API (HTTPS)
                           ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (Railway)                              │
│  ├─ /judge          → Recommend Service                 │
│  ├─ /interview/*    → Interview Service                 │
│  └─ /consult        → Consult Service                   │
│                          │                              │
│              ┌───────────▼───────────┐                  │
│              │   Hybrid Engine       │                  │
│              │ ┌─────────────────┐   │                  │
│              │ │ XGBoost ML      │   │                  │
│              │ │ (CFPP predict)  │   │                  │
│              │ ├─────────────────┤   │                  │
│              │ │ RAG Retriever   │   │                  │
│              │ │ (ChromaDB)      │   │                  │
│              │ ├─────────────────┤   │                  │
│              │ │ LLM Response    │   │                  │
│              │ │ (Claude API)    │   │                  │
│              │ └─────────────────┘   │                  │
│              └───────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌────────────────┐                  ┌──────────────────────┐
│ SQLite         │                  │ ChromaDB             │
│ ├─ Case        │                  │ ├─ Primary RAG (A-D) │
│ ├─ Heuristic   │                  │ └─ Secondary RAG (E) │
│ ├─ Interview   │                  └──────────────────────┘
│ ├─ Veteran     │
│ └─ DecisionLog │
└────────────────┘
```

## Data Models

| Model | Key Fields | Purpose |
|---|---|---|
| `Case` | case_id, context, decision, reason_codes, check_priority, risk_codes, rule_summary, actual_outcome | Historical/synthetic case storage and similar-case search |
| `Heuristic` | id, condition, action, confidence, source_case_ids, status | Veteran heuristic storage and recommendation adjustment |
| `InterviewSession` | session_id, veteran_id, case_responses, extracted_heuristic_ids, status | Interview progress and response storage |
| `Veteran` | id, name, career_years, domain_focus, decision_priorities | Veteran profile and metadata |
| `DecisionLog` | log_id, input, ai_recommendation, selected_scenario, actual_outcome | User final selection and post-hoc result tracking |

## Team Git Responsibilities

| Member | Scope | Git Directories |
|---|---|---|
| 오상훈 (Domain Owner) | Domain data, case validation, demo | `docs/`, `data/`, `demo/` |
| 윤창열 (PM) | Requirements, planning, document integration | `docs/requirements/`, `planning/` |
| 이동욱 (Backend/AI) | System design, backend, RAG, ML | `backend/`, `ml/`, `rag/`, `infra/` |
| 최윤정 (Frontend) | UI/UX design, Next.js implementation | `frontend/`, `design/`, `assets/` |
