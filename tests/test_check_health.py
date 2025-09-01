import json
import pathlib
import sqlite3
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import check_health


def _init_db(db_path: pathlib.Path) -> None:
    con = sqlite3.connect(db_path)
    con.execute(
        """
        CREATE VIRTUAL TABLE fts_issues USING fts5(
            title, summary, fix_steps, signals_concat, language,
            content='', tokenize='porter', prefix='2 3 4'
        )
        """
    )
    con.commit()
    con.close()


def test_main_ok(tmp_path, monkeypatch):
    db = tmp_path / 'db.sqlite'
    _init_db(db)
    monkeypatch.chdir(tmp_path)

    events = []

    def fake_record(self, event_type, status, **kw):
        events.append((event_type, status, kw))

    critical = []

    def fake_critical(self, message):
        critical.append(message)

    monkeypatch.setattr(check_health.MetricsCollector, 'record', fake_record)
    monkeypatch.setattr(check_health.AlertManager, 'critical', fake_critical)

    check_health.main(['--check-health', '--db-path', str(db)])

    status = json.loads((tmp_path / 'metrics/health_status.json').read_text())
    assert status['status'] == 'ok'
    assert events == [('check_health', 'success', {})]
    assert critical == []


def test_main_corrupted(tmp_path, monkeypatch):
    db = tmp_path / 'db.sqlite'
    _init_db(db)
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO fts_issues(rowid,title,summary,fix_steps,signals_concat,language)"
        " VALUES(1,'t','','','','')"
    )
    cur.execute('DROP TABLE fts_issues_data')
    con.commit()
    con.close()

    monkeypatch.chdir(tmp_path)

    events = []

    def fake_record(self, event_type, status, **kw):
        events.append((event_type, status, kw))

    critical = []

    def fake_critical(self, message):
        critical.append(message)

    monkeypatch.setattr(check_health.MetricsCollector, 'record', fake_record)
    monkeypatch.setattr(check_health.AlertManager, 'critical', fake_critical)

    with pytest.raises(SystemExit):
        check_health.main(['--check-health', '--db-path', str(db)])

    status = json.loads((tmp_path / 'metrics/health_status.json').read_text())
    assert status['status'] == 'error'
    assert events and events[0][1] == 'failure'
    assert critical
