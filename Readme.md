> **Part of the [Redwood AI Insurance Platform](https://github.com/anil-avvaru-cool/redwood-ai-insurance)**
> — an end-to-end intelligent insurance operations platform spanning underwriting through claims settlement.

# Insurance Data Platform

Entity resolution, feature store, and synthetic data generation — the foundation
that both the underwriting and claims platforms are built on.

## Overview

Both the risk scoring and fraud detection platforms depend on the same underlying
entities: vehicles (VINs), people (policyholders, drivers, claimants), addresses,
phone numbers, and policies. If those entities are not resolved consistently, every
downstream system degrades silently.

This repo owns:
- **Entity resolution** — VIN decode, person dedup, address normalization, policy
  lapse calculation. Runs once offline before any feature computation.
- **Feature store** — versioned, immutable feature snapshots for both underwriting
  and claims. State regulatory mask applied here, not at model level.
- **Synthetic data generator** — 20K quotes + 20K claims across 10 archetypes per
  platform, with correlated feature patterns designed for ensemble model training.

## Architecture

```
Layer 0 — config.py + feature_definitions.py       (no dependencies)
    ↓
Layer 1 — archetypes_underwriting.py + archetypes_claims.py
    ↓
Layer 2 — generator.py                             (raw parquet output)
    ↓
Layer 3 — entity_vehicle.py + entity_person.py +
          entity_address.py + entity_phone.py +
          entity_policy.py                         (data/entities/)
    ↓
Layer 4 — validator.py
    ↓
Layer 5 — graph_builder.py                         (loads entities → Neo4j)
    ↓
Layer 6 — graph_features.py + offline_pipeline.py  (data/processed/)
    ↓
Layer 7 — model training
```

**Why `feature_definitions.py` is Layer 0:** Archetypes import feature names from
it — never the reverse. This prevents training-serving skew from the first line of
code. See [DEC-004](https://github.com/anil-avvaru-cool/redwood-ai-insurance/blob/main/docs/DECISION_LOG.md#dec-004).

**Why entity resolution is Layer 3, not Layer 5:** Address and phone normalization
must happen before graph edges are created. A `shares_address` edge between two
unnormalized strings degrades Louvain community detection silently — fraud rings
appear disconnected. See [DEC-011](https://github.com/anil-avvaru-cool/redwood-ai-insurance/blob/main/docs/DECISION_LOG.md#dec-011).

## Status

Completed — 2026 Q2.

| Component | Status |
|---|---|
| `feature_definitions.py` | ✅ Complete |
| `config.py` | ✅ Complete |
| `archetypes_underwriting.py` | ✅ Complete |
| `archetypes_claims.py` | ✅ Complete |
| `generator.py` | ✅ Complete |
| `entity_*.py` (5 modules) | ✅ Complete |
| `validator.py` | ✅ Complete |
| `graph_builder.py` | ✅ Complete |
| `offline_pipeline.py` | ✅ Complete |

## Roadmap

- **Week 1, Day 1–2:** `config.py`, `feature_definitions.py`, archetypes
- **Week 1, Day 3:** `generator.py` — raw parquet with source datetime columns
- **Week 1, Day 4:** Entity resolution modules (5 modules → `data/entities/`)
- **Week 1, Day 5:** `validator.py`, `graph_builder.py`, `offline_pipeline.py`
- **Week 2:** Model training on `data/processed/` output

## Design Decisions

Key decisions documented in the
[platform Decision Log](https://github.com/anil-avvaru-cool/redwood-ai-insurance/blob/main/docs/DECISION_LOG.md):

| Decision | Summary |
|---|---|
| DEC-001 | Telematics nulls: null, never imputed — XGBoost learns from the signal |
| DEC-002 | Credit score null in CA/MA/MI/HI — regulatory compliance, non-negotiable |
| DEC-003 | Telematics trio convention — availability flag + enrolled-but-missing fraud signal |
| DEC-004 | `feature_definitions.py` as Layer 0 — prevents training-serving skew |
| DEC-005 | Graph features as second-pass enrichment — preserves online/offline parity |
| DEC-010 | `risk_score_at_issuance` as fraud feature — the shared data spine |
| DEC-011 | Entity resolution before graph build — normalized edges, reliable rings |
| DEC-013 | Source datetimes in raw parquet; derived ints in feature vector — non-breaking |

## Git Repository Structure

```text
insurance-data-platform/
├── README.md
├── docs/
│   └── (symlinks or copies of relevant platform docs)
│       ├── DECISION_LOG.md          ← DEC-001 through DEC-013
│       ├── FEATURE_STORE_GUIDE.md
│       └── DATA_GEN_GUIDE.md
│
├── config.py                        ← Layer 0: CREDIT_RESTRICTED_STATES,
│                                      PSI_CURRENT_WINDOW_DAYS, PSI_MIN_RECORDS,
│                                      QUOTE_DATE_RANGE_DAYS, OPEN_CLAIM_RATE,
│                                      UNCONFIRMED_FRAUD_RATE
│
├── features/
│   └── feature_definitions.py       ← Layer 0: feature names, null policy,
│                                      telematics trio, state regulatory mask,
│                                      derivation docs for policy_inception_days
│                                      and reporting_delay_days
│
├── data/
│   ├── synthetic/
│   │   ├── archetypes_underwriting.py  ← Layer 1: 10 driver/vehicle profiles
│   │   ├── archetypes_claims.py        ← Layer 1: 10 claim archetypes
│   │   ├── generator.py                ← Layer 2: outputs raw parquet
│   │   └── validator.py                ← Layer 4: temporal + null + fraud checks
│   │
│   ├── raw/                            ← gitignored
│   │   ├── quotes.parquet              ← generator.py output
│   │   └── claims.parquet              ← generator.py output
│   │
│   ├── entities/                       ← gitignored
│   │   ├── vehicles.parquet            ← entity_vehicle.py output
│   │   ├── persons.parquet             ← entity_person.py output
│   │   ├── addresses.parquet           ← entity_address.py output
│   │   ├── phones.parquet              ← entity_phone.py output
│   │   └── policies.parquet            ← entity_policy.py output
│   │
│   └── processed/                      ← gitignored
│       ├── quotes_features.parquet     ← offline_pipeline.py output
│       └── claims_features.parquet     ← offline_pipeline.py + graph_features.py output
│
├── entities/
│   ├── entity_vehicle.py            ← Layer 3: VIN decode, MSRP, ADAS efficacy
│   ├── entity_person.py             ← Layer 3: dedup, role assignment
│   ├── entity_address.py            ← Layer 3: normalize + hash
│   ├── entity_phone.py              ← Layer 3: normalize + hash
│   └── entity_policy.py             ← Layer 3: inception date, lapse calc,
│                                      writes policy_inception_date
│
├── graph/
│   ├── graph_builder.py             ← Layer 5: loads resolved entities
│   │                                  as nodes/edges into Neo4j only —
│   │                                  no feature computation here
│   └── graph_features.py            ← Layer 6: queries Neo4j → enriches
│                                      feature store
│
├── pipeline/
│   └── offline_pipeline.py          ← Layer 6: feature_definitions +
│                                      resolved entities → data/processed/
│
└── monitoring/
    └── psi_drift.py                 ← PSI current-period window keyed on
                                       quote_requested_at / fnol_submitted_at
                                       reads directly from data/raw/ parquet
```
## Local setup
docs/LOCAL_SETUP.md — dependency order, Docker setup, how to run the pipeline end-to-end

## Troubleshooting
docs/TROUBLESHOOTING.md