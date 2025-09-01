import json
import os
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class MetricsCollector:
    """Collects simple metrics by writing JSONL files per day."""

    def __init__(self, base_dir: Optional[Path] = None, *, enabled: Optional[bool] = None) -> None:
        self.base_dir = Path(base_dir or Path('metrics') / 'daily')
        env_enabled = os.getenv('METRICS_ENABLED', 'true').lower() != 'false'
        self.enabled = env_enabled if enabled is None else enabled

    def _get_today(self) -> date:
        return datetime.now(timezone.utc).date()

    @staticmethod
    def _validate(event_type: str, status: str) -> None:
        if not isinstance(event_type, str) or not event_type:
            raise ValueError('event_type must be a non-empty string')
        if not isinstance(status, str) or not status:
            raise ValueError('status must be a non-empty string')

    def record(
        self,
        event_type: str,
        status: str,
        *,
        duration_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cid: Optional[str] = None,
    ) -> None:
        """Record a metric event.

        Parameters mirror monitoring requirements. When disabled, this is a no-op.
        """
        if not self.enabled:
            return

        self._validate(event_type, status)

        record = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'event_type': event_type,
            'status': status,
        }
        if duration_ms is not None:
            record['duration_ms'] = duration_ms
        if details is not None:
            record['details'] = details
        if cid is not None:
            record['cid'] = cid

        today = self._get_today().isoformat()
        path = self.base_dir / f'{today}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as fh:
            json.dump(record, fh, ensure_ascii=False)
            fh.write('\n')
