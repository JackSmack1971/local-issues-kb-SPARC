from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def check_fts5_integrity(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f'{db_path} does not exist')
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        try:
            cur.execute("INSERT INTO fts_issues(fts_issues) VALUES('integrity-check')")
            if cur.fetchall():
                raise RuntimeError('fts_issues integrity check failed')
            if cur.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('database integrity check failed')
        except sqlite3.DatabaseError as exc:
            raise RuntimeError(str(exc)) from exc
    finally:
        con.close()


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db-path', type=Path, default=Path('issuesdb/issues.sqlite'))
    ap.add_argument('--check-health', action='store_true')
    return ap.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if not args.check_health:
        return
    try:
        check_fts5_integrity(args.db_path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error('health check failed: %s', exc)
        raise SystemExit(1)
    logger.info('database health OK')


if __name__ == '__main__':
    main()
