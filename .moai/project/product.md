# Blending Master — Product Documentation

## Project Overview

**Name**: Blending Master  
**Version**: MVP (v2.3)  
**Team**: CAIO 10기 12조  
**Domain**: Petroleum refinery — diesel cold flow property management

## One-Line Description

An expert knowledge-based AI Agent that converts veteran diesel product specialists' tacit judgment criteria into structured, searchable knowledge, supporting junior researchers in WAFI injection-amount and quality-risk decisions.

## Problem Statement

### Pain Points

1. **Judgment uncertainty** — Junior researchers lack confidence when deciding WAFI injection amounts as blend feedstock compositions change or new crude slates are introduced.
2. **Additive over-injection** — Conservative WAFI dosing practices to avoid off-spec risk generate unnecessary costs (estimated ≈ ₩20B/year).
3. **Re-blending losses** — Off-spec events in winter (Nov–Mar) cause time and material losses from re-analysis and re-blending (≈ 250 events/year × ₩40M per event).
4. **Knowledge attrition risk** — Key veteran researchers approaching retirement within 3 years; undocumented heuristics, exception handling, and priority logic risk being lost permanently.

### Estimated Business Impact

| Category | Estimated Annual Loss |
|---|---|
| Additive over-injection | ≈ ₩20B |
| Winter re-blending (250 events × ₩40M) | ≈ ₩100B |
| **Total** | **≈ ₩120B** |

> These are assumption-based estimates for project scoping; actual figures require internal cost/quality loss data at commercialization.

## Target Users

| Type | Persona | Role |
|---|---|---|
| Primary | Kim (Researcher, 32, 5-year tenure) | Daily blending decisions, WAFI injection, quality validation reports; wants AI-assisted independent judgment speed |
| Secondary | Lee (Senior Manager, 57, 30-year tenure) | Domain technical advisor, mentoring, knowledge transfer; wants tacit judgment criteria preserved for successors |

**Deployment Model**: B2B internal tool adopted by quality, production, and research organizations — not a consumer subscription product.

## Core Features

### P0 — MVP Required

#### Feature 1: Diesel Quality Assessment & WAFI Scenario Recommendation Engine

Accepts blend component composition, properties, target CFPP, season, and tank history as input; returns normal/caution/risk judgment plus 3 WAFI scenarios with rationale.

| Item | Detail |
|---|---|
| Input | Blend components (LGO/HGO/LCO/kerosene/biodiesel), properties (CFPP/CP/PP, density, n-paraffin, sulfur), target CFPP, season, tank history, priority (cost/balance/safety) |
| AI Processing | XGBoost prediction on synthetic data + similar-case RAG search + heuristic matching |
| Output | Normal/caution/risk judgment, 3 WAFI scenarios (min-cost / balanced / safe), predicted CFPP, confidence, Top-3 check priorities, Top-3 similar cases, applied heuristics |
| Success Criteria | CFPP MAE ≤ 2°C, R² ≥ 0.85, judgment agreement ≥ 70%, evidence citation rate ≥ 95%, response time ≤ 30s |

#### Feature 2: Blending Master AI Consultation Agent

Natural-language conversational RAG agent for follow-up questions after the recommendation engine output.

- Deep explanation of why a caution/risk verdict was issued
- Simulation of input-value changes (LCO ratio, target CFPP, WAFI ppm adjustments)
- Comparison to similar historical cases
- Domain knowledge Q&A (CFPP, WAFI, feedstock characteristics, seasonal strategies)
- All responses include case IDs, heuristic IDs, and document sources to minimize hallucination

#### Feature 3: Veteran Knowledge Extraction Agent

AI interviewer that extracts tacit knowledge from veteran researchers via structured multiple-choice coding — not free-form narration.

| Socratic Intent | Multiple-Choice Form | Storage |
|---|---|---|
| What is the judgment? | Q1: Normal / Caution / Risk | `decision` |
| Why that judgment? | Q2: Reason codes (max 2) | `reason_codes` |
| What to check first? | Q3: Check priority Top 3 | `check_priority` |
| What are the risks? | Q4: Risk codes (multiple) | `risk_codes` |
| One-line rule? | Q5: 1–2 sentence memo | `rule_summary` |

Approved tacit knowledge is reflected into the secondary RAG (E) and reused as evidence for Features 1 and 2.

### P1 — Should Have

- Decision log & feedback learning: Record final selections and actual batch results to enrich the Case DB
- Heuristic editor: Veteran review, edit, and approval of AI-extracted heuristics
- Coverage gap alert: Propose additional interview sessions when novel combinations not in the Case DB are detected

### P2 — Explicit Non-Goals

- Fully automated injection decisions (AI supports; humans decide)
- LIMS/SAP/DCS real-time integration (MVP: manual input or CSV upload)
- Domain LLM fine-tuning (MVP: LLM API + RAG)
- Real user authentication / authorization system (MVP: demo user selection; SSO deferred to commercialization)
- Multi-product expansion (MVP: diesel only)

## User Scenarios

### Scenario A: Researcher Daily Decision Flow

```
Select demo user → Main dashboard → New judgment input → Request AI assessment
→ Review normal/caution/risk + 3 WAFI scenarios → Consult or adopt
→ Save decision log → Input actual result → Feedback incorporated
```

### Scenario B: Veteran Knowledge Extraction Session

```
Start session → Agent presents case → AI draft judgment displayed
→ Q1 judgment → Q2 rationale → Q3 check priority → Q4 risk → Q5 memo
→ Code-form storage → Next case → End session
```

### Scenario C: Blending Master AI Consultation

```
Researcher has question about recommendation → Enter consultation mode
→ Current batch context auto-loaded → Natural-language question
→ Agent searches primary RAG (A-D) + secondary RAG (E) → Answer with citation IDs
```

## MVP KPIs

| KPI | Measurement | Target |
|---|---|---|
| ML CFPP MAE | Mean absolute error on synthetic test set | ≤ 2°C |
| ML R² | Coefficient of determination on synthetic test set | ≥ 0.85 |
| Reverse recommendation accuracy | ppm recommendations within target CFPP ±1°C | ≥ 90% |
| Similar-case search recall | Top-5 recall on pre-labeled answers | ≥ 80% |
| Judgment agreement rate | AI vs. labeled ground-truth (normal/caution/risk) | ≥ 70% |
| Response time (p95) | 100-call p95 latency | ≤ 30s |
| Scenario generation success | 3 scenarios all generated successfully | ≥ 95% |
| Evidence citation rate | Responses containing a case or heuristic | ≥ 95% |
| Interview efficiency | Interview time per case | 3–5 min |
| API success rate | HTTP 200 / total requests | ≥ 98% |
| Backend test coverage | pytest coverage on core logic | ≥ 70% |

## Implementation Timeline

| Phase | Period | Goal | Definition of Done |
|---|---|---|---|
| Phase 0 | Week 0 | Planning, data, skeleton | Code system finalized, 30 sample cases, 35 interview seeds, wireframes, Git repo, FastAPI/Next.js scaffold |
| Phase 1 | Week 1 | Backend core + primary RAG + synthetic ML data | Data models, A–D doc indexing, ≥200 synthetic ML records, XGBoost v1, /judge API draft |
| Phase 2 | Week 2 | Recommendation engine + interview storage + secondary RAG | 3-scenario generation, multiple-choice interview coding, interview results in secondary RAG, /interview/start + /consult APIs |
| Phase 3 | Week 3 | Frontend 4 screens | S-001–S-004 screens, API integration, result cards, consultation and interview UIs |
| Phase 4 | Week 4 | Integration, deployment, demo | Vercel/Railway deployed, demo dataset confirmed, presentation script, ≥1 team rehearsal |

## Data Strategy

| Type | Dataset | MVP Scale | Difficulty | Source |
|---|---|---|---|---|
| A. Process knowledge | CDU/HDS/Hydrocracker process descriptions | 10–15p | Low | Public technical references |
| B. Diesel production knowledge | Diesel fraction production and blending flow | 10–15p | Low | Public institution materials |
| C. Feedstock knowledge | LGO/HGO/LCO properties and characteristics | 15–20p | Medium | Public refs + domain review |
| D. Case knowledge | Synthetic quality issue cases | 30–50 cases | Medium | Synthetic data + domain review |
| E. Tacit knowledge | Veteran judgment criteria and exception conditions | 30–50 cases | Medium | AI multiple-choice interview |
| F. ML training data | Feedstock ratio + properties + WAFI ppm + CFPP result | 200–500 records | Medium | Synthetic data |
| G. Code system | decision/reason/check/risk codes | ~25 codes | Low | BRD-defined |

> **Security**: No actual internal company data used in MVP. Public data only, with attribution. LLM API calls use synthetic demo data only.
