# ADR 0001: Pre-scan Memory Projection
- Status: Accepted
- Context: Large datasets can exceed memory when indexing issues.
- Decision: Count issue files streamingly and compute projected memory as `issues * batch_size`.
- Consequences: Warn when projection exceeds `--memory-warn-mb` and exit when above `--memory-limit-mb`.
