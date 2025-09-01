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


def test_check_fts5_integrity_ok(tmp_path):
    db = tmp_path / 'db.sqlite'
    _init_db(db)
    check_health.check_fts5_integrity(db)


def test_check_fts5_integrity_corrupted(tmp_path):
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
    with pytest.raises(RuntimeError):
        check_health.check_fts5_integrity(db)
