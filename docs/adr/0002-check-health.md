# ADR 0002: Database Health Check
- Status: Accepted
- Context: Need a standalone way to verify SQLite and FTS5 integrity.
- Decision: Add `scripts/check_health.py` with `--check-health` flag invoking FTS5 and `PRAGMA` checks.
- Consequences: Enables automated detection of index or database corruption.
