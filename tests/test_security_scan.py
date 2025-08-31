import sys
from importlib import util
from pathlib import Path

spec = util.spec_from_file_location("security_scan", Path("scripts/security_scan.py"))
security_scan = util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = security_scan
spec.loader.exec_module(security_scan)


def run_scan(tmp_path: Path) -> list[security_scan.Finding]:
    return security_scan.scan_paths([tmp_path], correlation_id="test")


def test_detects_secret(tmp_path: Path) -> None:
    file = tmp_path / "secrets.py"
    file.write_text("api_key = 'abcd'")
    findings = run_scan(tmp_path)
    assert any("secret" in f.message for f in findings)


def test_flags_missing_input_validation(tmp_path: Path) -> None:
    file = tmp_path / "unsafe.py"
    file.write_text("def foo(path):\n    return open(path).read()\n")
    findings = run_scan(tmp_path)
    assert any("lacks input validation" in f.message for f in findings)


def test_flags_sql_without_placeholders(tmp_path: Path) -> None:
    file = tmp_path / "db.py"
    file.write_text("def query(db):\n    db.execute('SELECT * FROM users')\n")
    findings = run_scan(tmp_path)
    assert any("SQL statement without parameter placeholders" in f.message for f in findings)
