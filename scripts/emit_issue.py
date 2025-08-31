import datetime
import hashlib
import json
import pathlib
import re
from typing import Any, Dict, Iterable, List

from json_utils import MAX_JSON_BYTES

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
    json_blob = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True)
    if len(json_blob) > MAX_JSON_BYTES:
        raise ValueError(
            f'document exceeds {MAX_JSON_BYTES} bytes (size={len(json_blob)})'
        )
    with path.open('w', encoding='utf-8') as f:
        f.write(json_blob)
    return path


def write_issues_batch(docs: Iterable[Dict[str, Any]]) -> List[pathlib.Path]:
    """Write multiple issue documents atomically.

    Files are first written to temporary paths and then moved into place to emulate
    transaction semantics. Batched writes reduce N+1 filesystem overhead, improving
    collection speed on large rule sets. F:scripts/collect_sonar.py†L61-L64
    """

    docs_list = list(docs)
    paths: List[pathlib.Path] = []
    temp_paths: List[pathlib.Path] = []
    try:
        for doc in docs_list:
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
            path.relative_to(out)
            tmp = path.with_suffix('.json.tmp')
            json_blob = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True)
            if len(json_blob) > MAX_JSON_BYTES:
                raise ValueError(
                    f'document exceeds {MAX_JSON_BYTES} bytes (size={len(json_blob)})'
                )
            with tmp.open('w', encoding='utf-8') as f:
                f.write(json_blob)
            paths.append(path)
            temp_paths.append(tmp)
        for tmp, final in zip(temp_paths, paths):
            tmp.replace(final)
    except Exception:
        for tmp in temp_paths:
            if tmp.exists():
                tmp.unlink()
        raise
    return paths
