import json
import sys
from importlib import util
from pathlib import Path

import pytest

scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
sys.path.append(str(scripts_dir))

from json_utils import MAX_JSON_BYTES, load_json  # noqa: E402
import collect_sonar  # noqa: E402

spec = util.spec_from_file_location("security_scan", scripts_dir / "security_scan.py")
security_scan = util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = security_scan
spec.loader.exec_module(security_scan)


def run_scan(tmp_path: Path) -> list[security_scan.Finding]:
    return security_scan.scan_paths([tmp_path], correlation_id="test")


def test_security_scan_flags_fake_api_key(tmp_path: Path) -> None:
    file = tmp_path / "secrets.py"
    file.write_text("api_key='abcd'")
    findings = run_scan(tmp_path)
    assert any("secret" in f.message for f in findings)


def test_load_json_oversized_file(tmp_path: Path) -> None:
    big_value = "x" * MAX_JSON_BYTES
    path = tmp_path / "big.json"
    path.write_text(json.dumps({"data": big_value}), encoding="utf-8")
    assert path.stat().st_size > MAX_JSON_BYTES
    with pytest.raises(ValueError):
        load_json(path)


def test_collect_sonar_invalid_base_url() -> None:
    with pytest.raises(ValueError):
        collect_sonar.parse_args(["--base", "http://example.com"])


def test_security_scan_reports_raw_sql(tmp_path: Path) -> None:
    file = tmp_path / "db.py"
    file.write_text("def query(db):\n    db.execute('SELECT * FROM users')\n")
    findings = run_scan(tmp_path)
    assert any(
        "SQL statement without parameter placeholders" in f.message for f in findings
    )
