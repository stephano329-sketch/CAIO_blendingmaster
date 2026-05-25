# Synthetic Data — Blending Master MVP

Synthetic datasets for the Blending Master MVP demo. All data is generated from
physical models and Latin Hypercube Sampling — no internal company data is used.

## Plan & Decisions

The full generation plan with all 6 user-confirmed decisions is recorded at:
`.moai/plans/prd-snug-orbit.md`

## Files

| File | Dataset | Records | Purpose |
| --- | --- | --- | --- |
| `ml_training.csv` | F | 500 | XGBoost CFPP prediction model training |
| `ml_training_meta.json` | F | — | Generation metadata (seed, distributions, special-case indices) |
| `cases.json` | D | 35 | Historical case knowledge (1차 RAG search target) |
| `interview_seeds.json` | E-seed | 35 | Veteran Knowledge Extraction Agent UI demo seeds |

## Reproduction

```bash
# Install dependencies
pip install numpy scipy pandas

# Generate Dataset F (ML training)
python ml/data_generation/synthetic_generator.py

# Validate Dataset F
python ml/data_generation/validate.py

# Generate Dataset D (cases)
python ml/data_generation/case_renderer.py

# Generate Dataset E-seed (interview seeds)
python ml/data_generation/seed_renderer.py
```

Output paths are absolute relative to the project root. The seed used for
reproducibility is `20260510` (project SPEC date).

## Dataset F — ML Training (`ml_training.csv`)

500 records × 22 columns.

### Column Reference

| Column | Type | Range / Values | Description |
| --- | --- | --- | --- |
| `lgo_ratio` | float | [0.40, 0.85] | LGO blend ratio |
| `hgo_ratio` | float | [0.00, 0.30] | HGO blend ratio |
| `lco_ratio` | float | [0.00, 0.20] | LCO blend ratio |
| `kero_ratio` | float | [0.00, 0.10] | Kerosene blend ratio |
| `biodiesel_ratio` | float | 0.03 (fixed) | Korean spec — drop before ML training |
| `density_15c` | float | 800–920 kg/m³ | Density at 15°C |
| `n_paraffin_c10_c15` | float | wt% | n-paraffin C10–C15 distribution |
| `n_paraffin_c16_c20` | float | wt% | n-paraffin C16–C20 (main wax formers) |
| `n_paraffin_c21_plus` | float | wt% | n-paraffin C21+ (high-MW wax) |
| `aromatic_content` | float | vol% | Aromatic content |
| `sulfur_ppm` | float | 5–10 ppm | Sulfur (post-HDS) |
| `cetane_index` | float | — | Cetane index |
| `wafi_type` | str | {A, B, C, none} | WAFI additive type |
| `wafi_ppm` | float | 0–500 | WAFI dose in ppm |
| `season` | str | {winter, deep_winter} | Production season |
| `tank_history_flag` | str | {clean, recent_change, mixed} | Storage tank context |
| `cfpp` | float | °C | **Target #1**: predicted CFPP |
| `cp` | float | °C | Cloud Point (CFPP + 2~5°C) |
| `pp` | float | °C | Pour Point (CFPP + 5~9°C) |
| `target_cfpp` | float | °C | Per-row product target CFPP |
| `decision` | str | {normal, caution, risk} | **Target #2**: clean labeling rule output |
| `decision_noisy` | str | {normal, caution, risk} | **Target #3**: with 5% adjacent-class noise |

### Special-Case Structure

- **25 zero-WAFI baseline rows** (5%): `wafi_ppm = 0`, `wafi_type = none`
  - 13 winter + 12 deep_winter (stratified)
  - Used for ML to learn baseline CFPP behavior
- **30 monotonicity pairs** (60 rows, 12%): same blend/properties/season,
  different `wafi_ppm` (one low, one high ≥150ppm gap)
  - Pair indices recorded in `ml_training_meta.json` → `monotonicity_pairs`
  - Verified by `validate.py`: 97% of pairs preserve ppm↑ → CFPP↓

### Generated Distribution (with seed=20260510)

- **Season**: winter 251 / deep_winter 249
- **Decision (clean labels)**: normal 60 / caution 210 / risk 230
- **Decision (with 5% noise)**: normal 67 / caution 205 / risk 228
- **WAFI 0ppm baseline CFPP**: mean −3.6°C, p5 −7.4°C, p95 +0.1°C ✓ within [−10, +5]
- **CFPP overall**: mean −12.1°C, range [−21.7, +0.3]°C

> **Note on class balance**: The plan's estimate was `normal:caution:risk ≈ 22:46:32`,
> but the actual ratio is `12:42:46` (more risk-heavy). This is a physical
> consequence of the strict labeling rule (Decision 2: 4°C/2°C thresholds)
> applied to deep_winter products where target CFPP commonly exceeds achievable
> CFPP given the locked WAFI parameters and feedstock baselines. The data is
> realistic; ML training should account for this imbalance via class weights
> or sample weighting if classifier-style training is used.

### Suggested ML Train/Val/Test Split

Stratify by `season` × `decision`:
- Train: 350 rows (70%)
- Validation: 75 rows (15%)
- Test: 75 rows (15%)

For ML training, **drop `biodiesel_ratio`** (no information — constant 0.03).

## Dataset D — Case Knowledge (`cases.json`)

35 cases sampled from F with the matrix:

| | winter | deep_winter | total |
| --- | --- | --- | --- |
| normal | 5 | 5 | 10 |
| caution | 8 | 7 | 15 |
| risk | 5 | 5 | 10 |
| **total** | **18** | **17** | **35** |

### Case Schema

```json
{
  "case_id": "DIESEL-D-001",
  "source_f_index": 42,
  "context": {
    "season": "winter",
    "blend_components": { "lgo": 0.65, "hgo": 0.20, "lco": 0.07, "kero": 0.05, "biodiesel": 0.03 },
    "key_metrics": { /* CFPP, properties, WAFI */ },
    "target_cfpp": -12.5,
    "tank_history_flag": "clean"
  },
  "decision": "normal",
  "reason_codes": ["metric_level"],
  "check_priority": ["retest", "blend_ratio", "additive_dose"],
  "risk_codes": [],
  "rule_summary": "동절기 표준 조건 — 검사값 안정, WAFI 적정 → 출하 가능",
  "actual_outcome": {
    "final_cfpp": -12.3,
    "off_spec": false,
    "rework_required": false,
    "wafi_adjusted_to": 220
  },
  "narrative": "케이스 DIESEL-D-001 — 동절기 생산. 반제품 구성: LGO 0.65 / HGO 0.20 / ..."
}
```

### `actual_outcome.off_spec` Distribution (Decision 6)

| decision | off_spec count | rate |
| --- | --- | --- |
| normal | 0 / 10 | 0% |
| caution | 4 / 15 | ~25% |
| risk | 6 / 10 | 60% |
| **total** | **10 / 35** | **29%** |

### Use in RAG

The `narrative` field is the primary text for embedding into ChromaDB. Metadata
filters can be applied via `context.season`, `decision`, `reason_codes`, etc.

## Dataset E-seed — Interview Seeds (`interview_seeds.json`)

35 cases with the same matrix as D but **different rows** from F (no overlap
with D's `source_f_index`). For MVP, all veteran response fields are pre-filled.

### Additional Fields vs D

| Field | Purpose |
| --- | --- |
| `ai_draft_decision` | Agent's initial guess shown to veteran at interview start |
| `ai_draft_reason_codes` | Agent's reasoning chain matching the draft decision |
| `draft_pattern` | One of {match, under, over} — relationship between draft and decision |

### `draft_pattern` Distribution (Decision 5 — Option ④ 21/10/4)

| pattern | count | meaning |
| --- | --- | --- |
| match | 21 (60%) | Agent draft = veteran's final decision |
| under | 10 (29%) | Agent under-estimates risk (draft is "less severe") |
| over | 4 (11%) | Agent over-estimates risk (draft is "more severe") |

Distribution by veteran decision:
- normal (10): 7 match + 3 over
- caution (15): 9 match + 5 under (draft=normal) + 1 over (draft=risk)
- risk (10): 5 match + 5 under (draft=caution)

### Demo Message

The asymmetric distribution (under 10 ≫ over 4) intentionally conveys:
> "AI is a safety helper, but the veteran is more conservative and accurate
> in identifying risk."

## Code System (`reason_codes`, `check_priority`, `risk_codes`)

All structured codes follow PRD Appendix A and BRD §8 definitions. See those
documents for the canonical 25-code system. The renderers in this directory
generate the codes via rule-based mapping from row features.

## Validation

Run `python ml/data_generation/validate.py` after regeneration. The validator
runs 25 sanity checks. Last run: 25/25 passed.

## Source Documents

- `Blending_Master_PRD_v2_3.md` — Product Requirements Document
- `BRD_Diesel_RAG_Detailed_Final.md` — Business Requirements Document
- `.moai/plans/prd-snug-orbit.md` — Approved generation plan with 6 decision log
