import hashlib, json, pathlib, datetime

ROOT = pathlib.Path('issuesdb/issues')

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8')).hexdigest()

def write_issue(doc: dict):
    assert 'issue_id' in doc and 'source' in doc and 'title' in doc, 'minimum fields missing'
    src   = doc['source']
    lang  = (doc.get('language') or 'unknown').lower()
    out   = ROOT / src / lang
    out.mkdir(parents=True, exist_ok=True)
    if 'updated_at' not in doc:
        doc['updated_at'] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    path = out / f"{doc['issue_id']}.json"
    with path.open('w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2, sort_keys=True)
    return path
