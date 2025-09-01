from __future__ import annotations

"""Track process RSS memory usage."""

import os
from typing import Optional

import psutil


class MemoryMonitor:
    """Monitor resident set size (RSS) memory usage.

    Parameters are specified in megabytes. If ``limit_mb`` is not provided,
    ``ISSUES_KB_MEMORY_LIMIT_MB`` environment variable is used when set.
    """

    def __init__(self, warn_mb: Optional[int] = None, limit_mb: Optional[int] = None) -> None:
        if limit_mb is None:
            env_limit = os.getenv('ISSUES_KB_MEMORY_LIMIT_MB')
            limit_mb = int(env_limit) if env_limit else None
        self.warn_mb = warn_mb
        self.limit_mb = limit_mb
        self.process = psutil.Process(os.getpid())

    def rss_mb(self) -> float:
        """Return current RSS memory usage in megabytes."""

        return self.process.memory_info().rss / (1024 ** 2)
