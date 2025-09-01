"""Build the SQLite FTS5 index from JSON issue files.

This script maintains a contentless FTS5 index for fast search over issue metadata. It
tracks file modification times to update only changed records, drastically reducing
rebuild time for large datasets. The index is optimized using FTS5 merge operations and
an `automerge` configuration. After updates, an integrity check validates index health.

Usage:
    python scripts/build_index.py [--batch-size N]
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from pathlib import Path
import argparse
from typing import Dict, Iterable, List, Optional

from json_utils import load_json


ROOT = Path('issuesdb')
DB = ROOT / 'issues.sqlite'
SQL = Path('issues_index.sql')
STATE = ROOT / 'index_state.json'


def get_logger(correlation_id: str) -> logging.LoggerAdapter:
    """Return a structured logger with correlation ID."""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [cid=%(cid)s] %(message)s',
    )
    base_logger = logging.getLogger(__name__)
    return logging.LoggerAdapter(base_logger, {'cid': correlation_id})


def iter_issue_files() -> Iterable[Path]:
    """Yield all JSON issue files lazily."""

    return (ROOT / 'issues').glob('*/*/*.json')


def load_state() -> Dict[str, int]:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding='utf-8'))
    return {}


def save_state(state: Dict[str, int]) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def upsert_issue(cur: sqlite3.Cursor, doc: Dict[str, object]) -> None:
    cur.execute(
        """
        INSERT INTO issues(
            issue_id,source,source_rule_id,language,title,summary,fix_steps,
            severity,confidence,taxonomy_json,frequency,metadata_json,updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(issue_id) DO UPDATE SET
            title=excluded.title,
            summary=excluded.summary,
            fix_steps=excluded.fix_steps,
            severity=excluded.severity,
            confidence=excluded.confidence,
            frequency=excluded.frequency,
            taxonomy_json=excluded.taxonomy_json,
            metadata_json=excluded.metadata_json,
            updated_at=excluded.updated_at
        """,
        (
            doc['issue_id'],
            doc['source'],
            doc.get('source_rule_id'),
            doc.get('language'),
            doc['title'],
            doc.get('summary'),
            doc.get('fix_steps'),
            doc.get('severity'),
            doc.get('confidence'),
            json.dumps(doc.get('taxonomy', {}), ensure_ascii=False),
            doc.get('frequency'),
            json.dumps(doc.get('metadata', {}), ensure_ascii=False),
            doc.get('updated_at'),
        ),
    )
    cur.execute('DELETE FROM signals WHERE issue_id=?', (doc['issue_id'],))
    for s in doc.get('signals', []):
        cur.execute(
            'INSERT INTO signals(issue_id,kind,value) VALUES(?,?,?)',
            (doc['issue_id'], s['kind'], s['value']),
        )
    cur.execute('DELETE FROM references_web WHERE issue_id=?', (doc['issue_id'],))
    for r in doc.get('references', []):
        cur.execute(
            'INSERT INTO references_web(issue_id,label,url,license) VALUES(?,?,?,?)',
            (doc['issue_id'], r['label'], r['url'], r.get('license')),
        )


def update_fts(cur: sqlite3.Cursor, issue_id: str) -> None:
    row = cur.execute('SELECT rowid FROM issues WHERE issue_id=?', (issue_id,)).fetchone()
    if not row:
        return
    cur.execute(
        """
        INSERT INTO fts_issues(rowid,title,summary,fix_steps,signals_concat,language)
        SELECT rowid,
               title,
               COALESCE(summary,''),
               COALESCE(fix_steps,''),
               COALESCE((SELECT TRIM(GROUP_CONCAT(value,' '))
                         FROM signals s WHERE s.issue_id=i.issue_id),'') AS signals_concat,
               COALESCE(language,'')
        FROM issues i
        WHERE issue_id=?
        """,
        (issue_id,),
    )


def delete_issue(cur: sqlite3.Cursor, issue_id: str) -> None:
    row = cur.execute('SELECT rowid FROM issues WHERE issue_id=?', (issue_id,)).fetchone()
    if not row:
        return
    cur.execute(
        "INSERT INTO fts_issues(fts_issues, rowid) VALUES('delete', ?)",
        (row[0],),
    )
    cur.execute('DELETE FROM signals WHERE issue_id=?', (issue_id,))
    cur.execute('DELETE FROM references_web WHERE issue_id=?', (issue_id,))
    cur.execute('DELETE FROM issues WHERE issue_id=?', (issue_id,))


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch-size', type=int, default=1000)
    args = ap.parse_args(argv)
    if not 1 <= args.batch_size <= 10000:
        raise ValueError('--batch-size must be between 1 and 10000')
    return args


def check_integrity(cur: sqlite3.Cursor) -> None:
    """Validate FTS index and main database integrity."""

    cur.execute("INSERT INTO fts_issues(fts_issues) VALUES('integrity-check')")
    if cur.fetchall():
        raise RuntimeError('fts_issues integrity check failed')
    if cur.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise RuntimeError('database integrity check failed')


def process_batch(con: sqlite3.Connection, cur: sqlite3.Cursor, batch: List[Dict[str, object]]) -> None:
    con.execute('BEGIN')
    for doc in batch:
        upsert_issue(cur, doc)
        update_fts(cur, doc['issue_id'])
    con.commit()


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv or [])

    cid = uuid.uuid4().hex[:8]
    logger = get_logger(cid)
    start = time.time()
    state = load_state()
    removed_keys = set(state.keys())
    new_state: Dict[str, int] = {}
    total = 0
    changed = 0

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript(SQL.read_text(encoding='utf-8'))
    cur.execute('PRAGMA journal_mode=WAL;')
    cur.execute("INSERT INTO fts_issues(fts_issues, rank) VALUES('automerge', 4)")
    con.commit()

    batch: List[Dict[str, object]] = []
    for path in iter_issue_files():
        total += 1
        mtime = int(path.stat().st_mtime_ns)
        key = str(path.relative_to(ROOT))
        new_state[key] = mtime
        removed_keys.discard(key)
        if state.get(key) != mtime:
            doc = load_json(path)
            batch.append(doc)
            changed += 1
            if len(batch) >= args.batch_size:
                process_batch(con, cur, batch)
                batch.clear()

    if batch:
        process_batch(con, cur, batch)
        batch.clear()

    removed = list(removed_keys)
    logger.info('scan complete total=%s changed=%s removed=%s', total, changed, len(removed))
    if not changed and not removed and DB.exists():
        con.close()
        logger.info('index up-to-date seconds=%s', round(time.time() - start, 2))
        return

    if removed:
        con.execute('BEGIN')
        for key in removed:
            delete_issue(cur, Path(key).stem)
        con.commit()

    con.execute('BEGIN')
    cur.execute("INSERT INTO fts_issues(fts_issues, rank) VALUES('merge', 16)")
    cur.execute("INSERT INTO fts_issues(fts_issues) VALUES('optimize')")
    check_integrity(cur)
    con.commit()
    con.close()

    save_state(new_state)
    logger.info(
        'index build complete updated=%s removed=%s seconds=%s',
        changed,
        len(removed),
        round(time.time() - start, 2),
    )


if __name__ == '__main__':
    main()

