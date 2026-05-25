# Blending Master — Architecture Overview

> **Status**: Planning stage — no source code implemented yet. This overview reflects the planned architecture from the PRD and BRD documents.

## System Goals

Build an AI Agent system that:
1. Preserves veteran diesel product specialists' tacit knowledge as structured, searchable data
2. Supports junior researchers in WAFI injection-amount and quality-risk decision making
3. Provides evidence-cited AI recommendations to minimize hallucination and maintain trust

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  USER LAYER                                                  │
│  Browser → Next.js (Vercel) → 4 Screens                     │
│  S-001 Dashboard | S-002 Judge | S-003 Interview | S-004 Chat│
└──────────────────────────────┬───────────────────────────────┘
                               │ REST / HTTPS
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  APPLICATION LAYER                                           │
│  FastAPI (Railway) — Async Python 3.11                      │
│  ├─ Recommend Service (/judge)                               │
│  ├─ Interview Service (/interview/*)                         │
│  └─ Consult Service (/consult)                               │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  INTELLIGENCE LAYER — Hybrid Engine                          │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────────┐ │
│  │ XGBoost ML     │ │ RAG Retriever  │ │ LLM Generator    │ │
│  │ CFPP/CP/PP     │ │ ChromaDB       │ │ Claude API       │ │
│  │ prediction     │ │ Primary (A-D)  │ │ scenario synth   │ │
│  │                │ │ Secondary (E)  │ │ + citation       │ │
│  └────────────────┘ └────────────────┘ └──────────────────┘ │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  STORAGE LAYER                                               │
│  SQLite (structured)          ChromaDB (vector)              │
│  ├─ Case                      ├─ primary_rag (A-D docs)      │
│  ├─ Heuristic                 └─ secondary_rag (tacit E)     │
│  ├─ InterviewSession                                         │
│  ├─ Veteran                                                  │
│  └─ DecisionLog                                              │
└──────────────────────────────────────────────────────────────┘
```

## Design Patterns

| Pattern | Where Applied | Rationale |
|---|---|---|
| Layered Architecture | Backend service → engine → storage | Clear separation of concerns |
| RAG (Retrieval-Augmented Generation) | Consult + Recommend services | Grounds LLM output in actual case evidence |
| Two-tier RAG | Primary (A-D) + Secondary (E) | Separates document knowledge from veteran tacit knowledge |
| Multiple-choice interview coding | Knowledge Extraction Agent | Reduces veteran interview fatigue; enables structured filtering |
| Hybrid Engine | ML + RAG + LLM | Each layer compensates for the other's weaknesses |

## Module Boundaries

| Module | Owns | Does NOT touch |
|---|---|---|
| `frontend/` | UI, user interaction, API client | Business logic, ML inference |
| `backend/services/` | Request orchestration, response shaping | ML training, ChromaDB internals |
| `engine/` | ML inference, RAG query, LLM call | HTTP routing, DB ORM |
| `ml/` | Model training, synthetic data generation | API routing, vector DB |
| `rag/` | Embedding, indexing, retrieval | ML model, SQL storage |

## Knowledge Flow

```
Expert Knowledge Interview (Feature 3)
  ↓ Q1–Q5 multiple-choice responses
  ↓ Code conversion (Korean label → English code)
  ↓ JSON + vector text + metadata
Secondary RAG (E)
  ↓ Retrieved as heuristics in Hybrid Engine
Feature 1 (Recommend) + Feature 2 (Consult)
  ↓ Evidence-cited AI output
Researcher Decision
  ↓ DecisionLog + actual outcome feedback
Case DB enrichment (P1 scope)
```

## Planned Module Count

| Category | Count |
|---|---|
| Frontend screens | 4 |
| Backend services | 3 |
| RAG collections | 2 |
| Data model classes | 5 |
| ML models | 1 (XGBoost CFPP) |
| API endpoints | ~8 |
