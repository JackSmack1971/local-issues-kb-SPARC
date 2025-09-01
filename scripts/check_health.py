from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from monitoring.alert_manager import AlertManager
from monitoring.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

HEALTH_STATUS_PATH = Path('metrics/health_status.json')


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


def _write_status(data: dict) -> None:
    HEALTH_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = HEALTH_STATUS_PATH.with_suffix(HEALTH_STATUS_PATH.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False)
    tmp.replace(HEALTH_STATUS_PATH)


def _should_skip(path: Path, interval_min: int) -> bool:
    if not path.exists():
        return False
    try:
        existing = json.loads(path.read_text())
        last = datetime.fromisoformat(existing['ts'])
    except Exception:
        return False
    return datetime.now(timezone.utc) - last < timedelta(minutes=interval_min)


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

    metrics = MetricsCollector()
    alerts = AlertManager()
    interval_min = int(os.getenv('HEALTH_CHECK_INTERVAL_MIN', '0'))
    if interval_min > 0 and _should_skip(HEALTH_STATUS_PATH, interval_min):
        data = {'ts': datetime.now(timezone.utc).isoformat(), 'status': 'skipped'}
        _write_status(data)
        metrics.record('check_health', 'skipped')
        logger.info('health check skipped')
        return

    try:
        check_fts5_integrity(args.db_path)
    except Exception as exc:  # pragma: no cover - defensive
        metrics.record('check_health', 'failure', details={'error': str(exc)})
        alerts.critical(f'health check failed: {exc}')
        data = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'status': 'error',
            'message': str(exc),
        }
        _write_status(data)
        logger.error('health check failed: %s', exc)
        raise SystemExit(1)

    metrics.record('check_health', 'success')
    data = {'ts': datetime.now(timezone.utc).isoformat(), 'status': 'ok'}
    _write_status(data)
    logger.info('database health OK')


if __name__ == '__main__':
    main()
