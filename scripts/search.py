from __future__ import annotations

import logging
import sqlite3
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

DB = Path('issuesdb/issues.sqlite')
logger = logging.getLogger(__name__)

_metrics = {'queries': 0, 'seconds_total': 0.0}


def _prepare_query(query: str) -> str:
    return ' '.join(f"{term}*" for term in query.split())


def query_fts(db_path: Path | str, query: str, limit: int) -> List[Dict[str, str]]:
    assert limit > 0
    if not query:
        return []
    fts_query = _prepare_query(query)
    start = time.time()
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            (
                'SELECT i.issue_id,'
                '       i.title,'
                '       i.summary,'
                '       i.fix_steps,'
                '       i.language'
                '  FROM fts_issues'
                '  JOIN issues AS i ON i.rowid = fts_issues.rowid'
                ' WHERE fts_issues MATCH ?'
                ' ORDER BY bm25(fts_issues)'
                ' LIMIT ?'
            ),
            (fts_query, limit),
        )
        rows = [
            {
                'issue_id': r[0],
                'title': r[1],
                'summary': r[2],
                'fix_steps': r[3],
                'language': r[4],
            }
            for r in cur.fetchall()
        ]
    finally:
        con.close()
    elapsed = time.time() - start
    _metrics['queries'] += 1
    _metrics['seconds_total'] += elapsed
    logger.info('search query=%s limit=%s seconds=%s', query, limit, round(elapsed, 4))
    return rows


@lru_cache(maxsize=128)
def search(query: str, limit: int) -> List[Dict[str, str]]:
    return query_fts(DB, query, limit)


def get_metrics() -> Dict[str, float]:
    return dict(_metrics)
