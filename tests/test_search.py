import sqlite3
from pathlib import Path
import sys
import pathlib
import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / 'scripts'))
import search as search_module


def create_db(tmp_path: Path) -> Path:
    db_path = tmp_path / 'issues.sqlite'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(
        '''
        CREATE TABLE issues (
            issue_id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            fix_steps TEXT,
            language TEXT
        );
        CREATE VIRTUAL TABLE fts_issues USING fts5(
            title, summary, fix_steps, signals_concat, language,
            content=''
        );
        '''
    )
    cur.execute(
        'INSERT INTO issues(issue_id,title,summary,fix_steps,language) VALUES (?,?,?,?,?)',
        ('id1', 'Example rule', 'Demo summary', 'Do something', 'py'),
    )
    rowid = cur.execute('SELECT rowid FROM issues WHERE issue_id=?', ('id1',)).fetchone()[0]
    cur.execute(
        'INSERT INTO fts_issues(rowid,title,summary,fix_steps,signals_concat,language) '
        'VALUES (?,?,?,?,?,?)',
        (rowid, 'Example rule', 'Demo summary', 'Do something', '', 'py'),
    )
    con.commit()
    con.close()
    return db_path


def test_query_fts_prefix_and_metrics(tmp_path: Path) -> None:
    db = create_db(tmp_path)
    before = search_module.get_metrics()
    rows = search_module.query_fts(db, 'Exam', 5)
    assert rows and rows[0]['issue_id'] == 'id1'
    after = search_module.get_metrics()
    assert after['queries'] == before.get('queries', 0) + 1


def test_search_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {'n': 0}

    def fake_query_fts(db_path: Path, query: str, limit: int):
        calls['n'] += 1
        return []

    monkeypatch.setattr(search_module, 'query_fts', fake_query_fts)
    search_module.search.cache_clear()
    search_module.search('demo', 1)
    search_module.search('demo', 1)
    assert calls['n'] == 1
