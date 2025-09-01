# Local Issues→Fixes KB (File-First, Agent-Ready)

This repository is a local-only, file-first knowledge base for programming issues → fixes, optimized for LLM agent ingestion and fast local search.

## Key Design
- Files are truth: one JSON file per issue under `issuesdb/issues/<source>/<language>/<issue_id>.json`.
- Search index: a single SQLite database with FTS5 (`issuesdb/issues.sqlite`) built from files.
- Agent-ready chunks: export to `exports/chunks.jsonl` (one record per chunk with metadata).

## Setup
Install the Python dependencies, including `psutil>=5.9.0` for cross-platform memory stats:

```bash
pip install -r requirements.txt
```

## Quick Start
```bash
python scripts/collect_sonar.py --base https://sonarcloud.io --langs py --limit 200
python scripts/build_index.py
python scripts/chunk_export.py
python scripts/render_memory_bank.py
```

### Health Check

Verify the SQLite database and FTS5 index integrity:

```bash
python scripts/check_health.py --check-health
```

### Memory Controls

`scripts/build_index.py` estimates memory usage before indexing. It warns when
`issues * batch_size` exceeds `--memory-warn-mb` and aborts when above
`--memory-limit-mb`:

```bash
python scripts/build_index.py --batch-size 500 --memory-warn-mb 2000 --memory-limit-mb 4000
```

## Security Scan

Scan the repository for potential secrets, missing input validation, and unsafe SQL usage:

```bash
python scripts/security_scan.py scripts
```

The command exits with a non-zero status when issues are found so it can be used in CI workflows.

## Metrics Collector

Record operational events in daily JSONL files:

```python
from monitoring.metrics_collector import MetricsCollector
mc = MetricsCollector()
mc.record("collect", "ok", duration_ms=120)
```

Disable with `METRICS_ENABLED=false`.

## Layout
```
.
├─ issuesdb/
│  ├─ issues/
│  │  └─ <source>/<language>/<issue_id>.json
│  └─ issues.sqlite
├─ memory_bank/
│  ├─ productContext.md
│  ├─ systemPatterns.md
│  ├─ decisionLog.md
│  └─ progress.md
├─ schemas/
│  ├─ issue.schema.json
│  └─ chunk.schema.json
└─ scripts/
   ├─ collect_sonar.py
   ├─ emit_issue.py
   ├─ build_index.py
   ├─ chunk_export.py
   ├─ render_memory_bank.py
   ├─ search.py
   └─ security_scan.py
```

## Search

Run `scripts/search.py` for FTS lookups with caching and basic metrics:

```bash
python - <<'PY'
from scripts.search import search, get_metrics
print(search('demo', 5))
print(get_metrics())
PY
```

- **Caching:** `search()` uses an in-memory LRU cache so repeated queries return instantly.
- **Metrics:** `get_metrics()` reports the number of queries and total seconds spent.
- **Prefix queries:** each term is suffixed with `*` enabling prefix matches like `dem` → `demo`.
