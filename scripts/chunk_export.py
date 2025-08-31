import json, pathlib
from json_utils import load_json

ROOT = pathlib.Path('issuesdb/issues')
OUTD = pathlib.Path('exports'); OUTD.mkdir(parents=True, exist_ok=True)
OUTF = OUTD / 'chunks.jsonl'
MAX_CHARS = 1400

def chunks(text: str, max_chars=MAX_CHARS):
    if not text: return []
    text = text.strip()
    if len(text) <= max_chars: return [text]
    parts, buf, total = [], [], 0
    for para in text.split('\n\n'):
        if total + len(para) + 2 > max_chars and buf:
            parts.append('\n\n'.join(buf).strip()); buf = []; total = 0
        buf.append(para); total += len(para) + 2
    if buf: parts.append('\n\n'.join(buf).strip())
    fixed = []
    for p in parts:
        if len(p) <= max_chars: fixed.append(p)
        else:
            for i in range(0, len(p), max_chars):
                fixed.append(p[i:i+max_chars])
    return fixed

def iter_issues():
    for p in ROOT.glob('*/*/*.json'):
        yield load_json(p)

with OUTF.open('w', encoding='utf-8') as out:
    for doc in iter_issues():
        base_text = []
        base_text.append(f"# {doc['title']}")
        if doc.get('summary'): base_text.append(doc['summary'])
        if doc.get('root_cause'): base_text.append('Root cause: ' + (doc.get('root_cause') or ''))
        if doc.get('fix_steps'): base_text.append('Fix: ' + (doc.get('fix_steps') or ''))
        body = '\n\n'.join([t for t in base_text if t])
        sigs = [s['value'] for s in doc.get('signals', [])]
        refs = [r['url'] for r in doc.get('references', [])]
        for ix, ch in enumerate(chunks(body)):
            rec = {
                'id': f"{doc['issue_id']}:{ix}",
                'doc_id': doc['issue_id'],
                'chunk_ix': ix,
                'text': ch,
                'metadata': {
                    'source': doc['source'],
                    'language': doc.get('language'),
                    'severity': doc.get('severity'),
                    'signals': sigs,
                    'references': refs,
                    'updated_at': doc.get('updated_at')
                }
            }
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
print(f'Wrote {OUTF}')
