import json
import pathlib
import sys
from pathlib import Path

sys.path.append(str(pathlib.Path(__file__).resolve().parents[2]))

from monitoring.alert_manager import AlertManager, load_thresholds, parse_args


def make_manager(tmp_path: Path) -> tuple[AlertManager, Path]:
    args = parse_args([])
    thresholds = load_thresholds(args)
    out = tmp_path / "alerts" / "active_alerts.json"
    manager = AlertManager(thresholds, output_path=out)
    return manager, out


def load_file(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_collection_success_rate_breach(tmp_path):
    manager, out = make_manager(tmp_path)
    alerts = manager.check({"collection_success_rate": 0.9})
    assert alerts[0].severity == "ERROR"
    data = load_file(out)
    assert data[0]["name"] == "collection_success_rate"


def test_index_build_time_breach(tmp_path):
    manager, out = make_manager(tmp_path)
    alerts = manager.check({"index_build_time_seconds": 120})
    assert alerts[0].severity == "WARN"
    data = load_file(out)
    assert data[0]["name"] == "index_build_time_seconds"


def test_disk_usage_warn(tmp_path):
    manager, out = make_manager(tmp_path)
    alerts = manager.check({"disk_usage": 0.85})
    assert alerts[0].severity == "WARN"
    data = load_file(out)
    assert data[0]["name"] == "disk_usage"


def test_disk_usage_critical(tmp_path):
    manager, out = make_manager(tmp_path)
    alerts = manager.check({"disk_usage": 0.97})
    assert alerts[0].severity == "CRITICAL"
    data = load_file(out)
    assert data[0]["severity"] == "CRITICAL"


def test_memory_usage_breach(tmp_path):
    manager, out = make_manager(tmp_path)
    alerts = manager.check({"memory_usage_mb": 500})
    assert alerts[0].severity == "WARN"
    data = load_file(out)
    assert data[0]["name"] == "memory_usage_mb"


def test_api_rate_limited_breach(tmp_path):
    manager, out = make_manager(tmp_path)
    alerts = manager.check({"api_rate_limited_ratio": 0.2})
    assert alerts[0].severity == "WARN"
    data = load_file(out)
    assert data[0]["name"] == "api_rate_limited_ratio"


def test_fts5_integrity_failure(tmp_path):
    manager, out = make_manager(tmp_path)
    alerts = manager.check({"fts5_integrity_ok": False})
    assert alerts[0].severity == "CRITICAL"
    data = load_file(out)
    assert data[0]["name"] == "fts5_integrity"
