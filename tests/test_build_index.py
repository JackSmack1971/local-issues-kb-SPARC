import hashlib
import json
import pathlib
import sqlite3
import sys
import time

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import build_index


def _write_issue(dir_path: pathlib.Path, idx: int) -> str:
    issue_id = hashlib.sha1(str(idx).encode()).hexdigest()
    doc = {
        'issue_id': issue_id,
        'source': 'src',
        'language': 'py',
        'title': f'Issue {idx}',
        'signals': [{'kind': 'rule', 'value': 'S1'}],
    }
    (dir_path / f'{issue_id}.json').write_text(json.dumps(doc), 'utf-8')
    return issue_id


def test_incremental_build(monkeypatch, tmp_path):
    root = tmp_path / 'issuesdb'
    issues_dir = root / 'issues' / 'src' / 'py'
    issues_dir.mkdir(parents=True)

    sql_path = pathlib.Path(__file__).resolve().parents[1] / 'issues_index.sql'
    monkeypatch.setattr(build_index, 'ROOT', root)
    monkeypatch.setattr(build_index, 'DB', root / 'issues.sqlite')
    monkeypatch.setattr(build_index, 'SQL', sql_path)
    monkeypatch.setattr(build_index, 'STATE', root / 'index_state.json')

    for i in range(1001):
        _write_issue(issues_dir, i)

    start = time.time()
    build_index.main()
    full_time = time.time() - start

    doc_path = next(issues_dir.iterdir())
    doc = json.loads(doc_path.read_text('utf-8'))
    doc['title'] = 'updated'
    doc_path.write_text(json.dumps(doc), 'utf-8')

    start = time.time()
    build_index.main()
    incr_time = time.time() - start

    assert incr_time < full_time

    con = sqlite3.connect(root / 'issues.sqlite')
    cur = con.cursor()
    assert cur.execute('SELECT COUNT(*) FROM issues').fetchone()[0] == 1001
    assert cur.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    con.close()


def test_batch_transactions(monkeypatch, tmp_path):
    root = tmp_path / 'issuesdb'
    issues_dir = root / 'issues' / 'src' / 'py'
    issues_dir.mkdir(parents=True)

    sql_path = pathlib.Path(__file__).resolve().parents[1] / 'issues_index.sql'
    monkeypatch.setattr(build_index, 'ROOT', root)
    monkeypatch.setattr(build_index, 'DB', root / 'issues.sqlite')
    monkeypatch.setattr(build_index, 'SQL', sql_path)
    monkeypatch.setattr(build_index, 'STATE', root / 'index_state.json')

    for i in range(10):
        _write_issue(issues_dir, i)

    commit_calls = 0

    class CountingConnection(sqlite3.Connection):
        def commit(self):
            nonlocal commit_calls
            commit_calls += 1
            return super().commit()

    orig_connect = sqlite3.connect

    def counting_connect(*args, **kwargs):
        kwargs['factory'] = CountingConnection
        return orig_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, 'connect', counting_connect)
    build_index.main(['--batch-size', '3'])
    expected_commits = (10 + 3 - 1) // 3 + 2  # batches + setup + final
    assert commit_calls == expected_commits


def test_parse_args_env(monkeypatch):
    monkeypatch.setenv('ISSUES_KB_MEMORY_LIMIT_MB', '321')
    ns = build_index.parse_args([])
    assert ns.memory_limit_mb == 321
    monkeypatch.delenv('ISSUES_KB_MEMORY_LIMIT_MB', raising=False)


def test_memory_limit_reduces_batch_size(monkeypatch, tmp_path, caplog):
    root = tmp_path / 'issuesdb'
    issues_dir = root / 'issues' / 'src' / 'py'
    issues_dir.mkdir(parents=True)

    sql_path = pathlib.Path(__file__).resolve().parents[1] / 'issues_index.sql'
    monkeypatch.setattr(build_index, 'ROOT', root)
    monkeypatch.setattr(build_index, 'DB', root / 'issues.sqlite')
    monkeypatch.setattr(build_index, 'SQL', sql_path)
    monkeypatch.setattr(build_index, 'STATE', root / 'index_state.json')
    monkeypatch.setattr(build_index, 'LOG_INTERVAL', 1)

    for i in range(5):
        _write_issue(issues_dir, i)

    class FakeMonitor:
        warn_mb = None
        limit_mb = 50

        def __init__(self, *_a, **_k):
            pass

        def rss_mb(self):
            return 100

    monkeypatch.setattr(build_index, 'MemoryMonitor', lambda warn_mb, limit_mb: FakeMonitor())
    caplog.set_level('WARNING')
    build_index.main(['--batch-size', '4', '--memory-limit-mb', '50'])
    assert any('memory limit exceeded' in r.message for r in caplog.records)


def test_projected_memory_warning(monkeypatch, tmp_path, caplog):
    root = tmp_path / 'issuesdb'
    issues_dir = root / 'issues' / 'src' / 'py'
    issues_dir.mkdir(parents=True)

    sql_path = pathlib.Path(__file__).resolve().parents[1] / 'issues_index.sql'
    monkeypatch.setattr(build_index, 'ROOT', root)
    monkeypatch.setattr(build_index, 'DB', root / 'issues.sqlite')
    monkeypatch.setattr(build_index, 'SQL', sql_path)
    monkeypatch.setattr(build_index, 'STATE', root / 'index_state.json')

    for i in range(3):
        _write_issue(issues_dir, i)

    caplog.set_level('WARNING')
    build_index.main(['--batch-size', '5', '--memory-warn-mb', '10', '--memory-limit-mb', '100'])
    assert any('projected memory usage' in r.message for r in caplog.records)


def test_projected_memory_limit_exits(monkeypatch, tmp_path):
    root = tmp_path / 'issuesdb'
    issues_dir = root / 'issues' / 'src' / 'py'
    issues_dir.mkdir(parents=True)

    sql_path = pathlib.Path(__file__).resolve().parents[1] / 'issues_index.sql'
    monkeypatch.setattr(build_index, 'ROOT', root)
    monkeypatch.setattr(build_index, 'DB', root / 'issues.sqlite')
    monkeypatch.setattr(build_index, 'SQL', sql_path)
    monkeypatch.setattr(build_index, 'STATE', root / 'index_state.json')

    for i in range(5):
        _write_issue(issues_dir, i)

    with pytest.raises(SystemExit) as excinfo:
        build_index.main(['--batch-size', '5', '--memory-limit-mb', '20'])
    assert 'projected memory' in str(excinfo.value)

