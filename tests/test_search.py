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
            content='', prefix='2 3 4'
        );
        '''
    )
    sample_rows = [
        ('id1', 'Network hiccup', 'Network glitch', 'Restart network', 'py'),
        (
            'id2',
            'Network network problem',
            'Network network network failure',
            'Network network reset',
            'py',
        ),
    ]
    for issue in sample_rows:
        cur.execute(
            'INSERT INTO issues(issue_id,title,summary,fix_steps,language) VALUES (?,?,?,?,?)',
            issue,
        )
        rowid = cur.execute('SELECT rowid FROM issues WHERE issue_id=?', (issue[0],)).fetchone()[0]
        cur.execute(
            'INSERT INTO fts_issues(rowid,title,summary,fix_steps,signals_concat,language) '
            'VALUES (?,?,?,?,?,?)',
            (rowid, issue[1], issue[2], issue[3], '', issue[4]),
        )
    con.commit()
    con.close()
    return db_path


def test_query_fts_orders_by_bm25_and_prefix(tmp_path: Path) -> None:
    db = create_db(tmp_path)
    before = search_module.get_metrics()
    rows = search_module.query_fts(db, 'netw', 5)
    assert [r['issue_id'] for r in rows] == ['id2', 'id1']
    after = search_module.get_metrics()
    assert after['queries'] == before.get('queries', 0) + 1
    assert after['seconds_total'] > before.get('seconds_total', 0)


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
