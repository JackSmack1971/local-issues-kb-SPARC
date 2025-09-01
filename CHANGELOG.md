# Changelog

## [Unreleased]
### Added
- Warn and abort in `build_index.py` based on projected memory from issue count and batch size.
- Require `psutil>=5.9.0` and document setup dependency.
- Parametrized tests for batch-size and memory flags with psutil-based memory simulation.
- `check_health.py` CLI for SQLite and FTS5 integrity validation.
