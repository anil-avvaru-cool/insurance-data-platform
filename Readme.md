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

In active development — 2026 Q2.

| Component | Status |
|---|---|
| `feature_definitions.py` | ✅ Complete |
| `config.py` | ✅ Complete |
| `archetypes_underwriting.py` | 🔨 In progress |
| `archetypes_claims.py` | 🔨 In progress |
| `generator.py` | 🔨 In progress |
| `entity_*.py` (5 modules) | 🔨 In progress |
| `validator.py` | 🔨 In progress |
| `graph_builder.py` | 📋 Planned |
| `offline_pipeline.py` | 📋 Planned |

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