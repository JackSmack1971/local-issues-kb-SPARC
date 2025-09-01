import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import memory_monitor
from memory_monitor import MemoryMonitor


def test_rss_mb(monkeypatch):
    class FakeProcess:
        def __init__(self, *_args, **_kwargs):
            pass

        def memory_info(self):
            class Info:
                rss = 100 * 1024 * 1024

            return Info()

    monkeypatch.setattr(memory_monitor.psutil, 'Process', lambda *_a, **_k: FakeProcess())
    monitor = MemoryMonitor()
    assert monitor.rss_mb() == 100


def test_env_limit(monkeypatch):
    monkeypatch.setenv('ISSUES_KB_MEMORY_LIMIT_MB', '123')
    monitor = MemoryMonitor()
    assert monitor.limit_mb == 123
    monkeypatch.delenv('ISSUES_KB_MEMORY_LIMIT_MB', raising=False)
