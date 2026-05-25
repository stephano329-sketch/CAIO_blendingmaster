# Blending Master — Technology Stack

## Primary Language

**Python 3.11** (backend, ML, RAG) + **TypeScript** (frontend)

Chosen for AI/data ecosystem compatibility (Python) and rapid web UI development (TypeScript/Next.js).

## Technology Stack

| Layer | Technology | Version | Rationale |
|---|---|---|---|
| Frontend framework | Next.js | 14 (App Router) | Fast UI scaffolding, SSR, Vercel-native deployment |
| Frontend styling | Tailwind CSS | 3.x | Utility-first, consistent rapid design |
| Frontend components | shadcn/ui | Latest | Accessible, composable component primitives |
| Backend framework | FastAPI | 0.110+ | Async LLM calls, automatic OpenAPI docs, Python ecosystem |
| ML model | XGBoost | 2.x | Strong tabular data performance, Feature Importance, interpretability |
| LLM | Claude Sonnet (Anthropic API) | To be confirmed | Reasoning quality, RAG integration, safe output |
| Primary DB | SQLite | 3.x | Zero-config for MVP demo; migrate to PostgreSQL at commercialization |
| Vector DB | ChromaDB | 0.5+ | Local/embedded operation, suitable for MVP scale |
| Deployment (frontend) | Vercel | — | Fast demo URL, Next.js native |
| Deployment (backend) | Railway | — | Simple Python service hosting for demo |

## Framework Architecture

### FastAPI Backend

```python
# Async endpoint pattern
@router.post("/judge", response_model=JudgeResponse)
async def judge(request: JudgeRequest):
    result = await hybrid_engine.run(request)
    return result
```

Key design decisions:
- All LLM and RAG calls are async to support p95 ≤ 30s response targets
- OpenAPI spec auto-generated for frontend type safety
- Pydantic v2 for request/response validation

### Hybrid Engine (3-Layer Processing)

```
User Input
  │
  ▼
Layer 1: XGBoost ML Model
  → CFPP / CP / PP prediction
  → WAFI candidate range estimation
  │
  ▼
Layer 2: RAG Retrieval (ChromaDB)
  → Similar case search (Primary RAG, A-D)
  → Heuristic matching (Secondary RAG, E)
  │
  ▼
Layer 3: LLM Response Generation (Claude API)
  → Synthesize ML prediction + RAG evidence
  → Generate 3 WAFI scenarios (min-cost / balanced / safe)
  → Cite case IDs + heuristic IDs + document sources
  │
  ▼
Output: Judgment + Scenarios + Evidence
```

### Next.js Frontend

- **App Router** with server and client components
- **API client**: Typed fetch wrapper in `lib/api.ts` — no third-party HTTP library for MVP simplicity
- **State management**: React `useState`/`useReducer` for local state; no global state manager needed at MVP scale
- **Component library**: shadcn/ui (Radix UI primitives + Tailwind)

## Data Storage

### SQLite (Structured Data)

Used for case records, heuristics, interview sessions, veterans, and decision logs.

```sql
-- Core tables
CREATE TABLE cases (
  case_id TEXT PRIMARY KEY,
  context JSON NOT NULL,
  decision TEXT CHECK(decision IN ('normal', 'caution', 'risk')),
  reason_codes JSON,
  check_priority JSON,
  risk_codes JSON,
  rule_summary TEXT,
  actual_outcome JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE heuristics (
  id TEXT PRIMARY KEY,
  condition TEXT NOT NULL,
  action TEXT NOT NULL,
  confidence REAL DEFAULT 0.0,
  source_case_ids JSON,
  status TEXT CHECK(status IN ('draft', 'approved', 'archived'))
);

CREATE TABLE decision_logs (
  log_id TEXT PRIMARY KEY,
  input JSON NOT NULL,
  ai_recommendation JSON,
  selected_scenario TEXT,
  actual_outcome JSON,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

> **Upgrade path**: Replace SQLite with PostgreSQL + connection pooling at commercialization. ORM layer (SQLAlchemy) abstracts the switch.

### ChromaDB (Vector Storage)

Two isolated collections for two-tier RAG architecture:

| Collection | Content | Metadata Filters |
|---|---|---|
| `primary_rag` | A-D documents + synthetic cases | doc_type, season, product_type |
| `secondary_rag` | Veteran tacit knowledge (E) | decision, reason_codes, season |

Embedding model: Anthropic Embeddings or `text-embedding-3-small` (to be confirmed based on API access).

## ML Model

### XGBoost CFPP Prediction

```python
# Training configuration (MVP)
model = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
```

**Features (18 total)**:
- Blend ratios: `lgo_ratio`, `hgo_ratio`, `lco_ratio`, `kero_ratio`, `biodiesel_ratio`
- Properties: `density_15c`, `n_paraffin_c10_c15`, `n_paraffin_c16_c20`, `n_paraffin_c21_plus`
- Properties: `aromatic_content`, `sulfur_ppm`, `cetane_index`
- WAFI: `wafi_type` (encoded), `wafi_ppm`
- Environment: `season` (encoded), `tank_history_flag`

**Target metrics**:
- CFPP prediction: MAE ≤ 2°C, R² ≥ 0.85
- WAFI reverse recommendation: ≥ 90% within target CFPP ±1°C

**Synthetic data generation**: Latin Hypercube Sampling (200–500 records) + Gaussian noise for measurement variability + domain expert constraint validation.

## LLM Integration

### Claude API (Anthropic)

```python
# Async LLM call pattern
async def generate_recommendation(context: dict, rag_results: list) -> str:
    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-5",  # or equivalent available model
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_prompt(context, rag_results)}
        ]
    )
    return response.content[0].text
```

**Hallucination mitigation**:
- All responses must cite `case_id`, `heuristic_id`, or `doc_source`
- Safety disclaimer appended: "AI recommendation — final judgment by researcher required"
- RAG evidence passed in context window before generation

## Development Environment

### Requirements

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Backend, ML, RAG |
| Node.js | 20 LTS | Frontend development |
| npm / pnpm | Latest | Frontend package management |
| Git | 2.40+ | Version control |

### Python Dependencies (backend/requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
chromadb>=0.5.0
xgboost>=2.0.0
anthropic>=0.25.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
scikit-learn>=1.4.0
pandas>=2.0.0
numpy>=1.26.0
```

### Node Dependencies (frontend/package.json)

```json
{
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x",
    "tailwindcss": "3.x",
    "@radix-ui/react-*": "latest",
    "class-variance-authority": "latest",
    "clsx": "latest",
    "lucide-react": "latest"
  },
  "devDependencies": {
    "typescript": "5.x",
    "@types/node": "20.x",
    "@types/react": "18.x",
    "eslint": "8.x"
  }
}
```

## Build and Deployment

### Local Development

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev  # http://localhost:3000

# ML — generate synthetic data
cd ml
python data_generation/synthetic_generator.py
python training/train_cfpp.py
```

### Environment Variables

```bash
# .env (never commit — in .gitignore)
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=sqlite:///./blending_master.db
CHROMA_DB_PATH=./chroma_db
ALLOWED_ORIGINS=http://localhost:3000

# Production (set in Railway / Vercel dashboard)
ANTHROPIC_API_KEY=...
DATABASE_URL=...
```

### Demo Deployment

| Service | URL Pattern | Usage |
|---|---|---|
| Vercel (frontend) | `https://blending-master.vercel.app` | Demo URL for presentation |
| Railway (backend) | `https://blending-master-api.railway.app` | Backend API for demo |

## Non-Functional Requirements

| Category | Requirement |
|---|---|
| Response time | p95 ≤ 30s (recommendation); dashboard load ≤ 2s |
| Concurrency | MVP: 2 simultaneous demo users |
| Test coverage | Backend core logic ≥ 70% (pytest) |
| Security | No real internal data; API keys in `.env` + `.gitignore`; pre-commit secret scan |
| Authentication | MVP: Demo user selection (dropdown); SSO deferred to commercialization |

## Upgrade Roadmap (Post-MVP)

| Item | Technology | When |
|---|---|---|
| Production DB | PostgreSQL + Alembic migrations | Commercialization |
| Auth / SSO | Company SSO integration + RBAC | Commercialization |
| ML improvement | Bayesian optimization, confidence intervals, physical mixing rule layer | Phase after MVP |
| Embedding | Domain-tuned embeddings | After real data acquisition |
| Real-time data | LIMS/SAP/DCS API integration | Post-commercialization |
| Scaling | PostgreSQL + Redis caching + production WSGI | Production scale |
