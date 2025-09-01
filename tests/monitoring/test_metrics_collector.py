import json
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))
from datetime import date
from pathlib import Path

import pytest

from monitoring.metrics_collector import MetricsCollector


def test_record_creates_daily_file(tmp_path):
    base = tmp_path / 'metrics' / 'daily'
    collector = MetricsCollector(base)
    collector.record('test_event', 'ok', duration_ms=5)
    today = collector._get_today().isoformat()
    file_path = base / f'{today}.json'
    assert file_path.exists()
    content = file_path.read_text(encoding='utf-8').strip()
    record = json.loads(content)
    assert record['event_type'] == 'test_event'
    assert record['status'] == 'ok'
    assert record['duration_ms'] == 5


def test_rotation(tmp_path):
    base = tmp_path / 'metrics' / 'daily'
    collector = MetricsCollector(base)

    collector._get_today = lambda: date(2024, 1, 1)
    collector.record('e1', 'ok')
    collector._get_today = lambda: date(2024, 1, 2)
    collector.record('e2', 'ok')

    assert (base / '2024-01-01.json').exists()
    assert (base / '2024-01-02.json').exists()


def test_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv('METRICS_ENABLED', 'false')
    base = tmp_path / 'metrics' / 'daily'
    collector = MetricsCollector(base)
    collector.record('e', 'ok')
    assert not base.exists()
    monkeypatch.delenv('METRICS_ENABLED', raising=False)
