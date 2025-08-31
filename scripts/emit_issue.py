import datetime
import hashlib
import json
import pathlib
import re
from typing import Any, Dict

ROOT = pathlib.Path('issuesdb/issues').resolve()
ISSUE_ID_PATTERN = re.compile(r'^[a-f0-9]{40}$')


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def write_issue(doc: Dict[str, Any]) -> pathlib.Path:
    """Write issue document to canonical JSON file."""
    assert 'issue_id' in doc and 'source' in doc and 'title' in doc, 'minimum fields missing'
    issue_id = doc['issue_id']
    if not ISSUE_ID_PATTERN.fullmatch(issue_id):
        raise ValueError('issue_id must be a 40-character hexadecimal string')
    src = doc['source']
    lang = (doc.get('language') or 'unknown').lower()
    out = (ROOT / src / lang).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if 'updated_at' not in doc:
        doc['updated_at'] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    path = (out / f'{issue_id}.json').resolve()
    try:
        path.relative_to(out)
    except ValueError as exc:
        raise ValueError('resolved path escapes target directory') from exc
    with path.open('w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=True)
    return path
