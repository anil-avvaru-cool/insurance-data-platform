## Setup

**Local dev** (for tests and linting):
```bash
uv venv && source .venv/bin/activate
uv sync
cp example.env .env        # then edit .env
uv export --format requirements-txt --no-hashes --no-emit-workspace > requirements.txt
```

**Docker** (required for the full pipeline — Neo4j + Redis):
```bash
docker compose build --no-cache
docker compose up -d neo4j redis   # wait ~30 s for Neo4j to become healthy
```

## Data pipeline

```bash
# Wipe previous outputs (optional)
sudo rm -rf ./data/raw/* ./data/processed/*

**1. Start infrastructure**
```bash
docker compose up -d
```

**2. Configure environment** — create `.env` (gitignored):
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
REDIS_URL=redis://localhost:6379
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the full pipeline** (in order):
```bash

# Run in a single command
docker compose run --rm app python main.py --generate-data --resolve-entities \
  --build-graph --compute-graph-features --run-offline-pipeline --validate-data
```

**Drift check** (after pipeline):
```bash
python main.py --drift-check
python main.py --drift-check --as-of 2025-06-01   # back-test as of date
```

**Infrastructure**
```bash
docker compose stop       # stop containers, keep volumes
docker compose down -v    # stop + delete volumes (full reset)
```

Neo4j browser: http://localhost:7474

---