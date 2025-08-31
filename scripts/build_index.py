import sqlite3, json, pathlib
from json_utils import load_json

ROOT = pathlib.Path('issuesdb')
DB   = ROOT / 'issues.sqlite'
SQL  = pathlib.Path('issues_index.sql')

def iter_docs():
    for p in (ROOT / 'issues').glob('*/*/*.json'):
        yield load_json(p)

con = sqlite3.connect(DB)
cur = con.cursor()
cur.executescript(SQL.read_text(encoding='utf-8'))
cur.execute('PRAGMA journal_mode=WAL;')

def upsert_issue(doc):
    cur.execute(
    """INSERT INTO issues(issue_id,source,source_rule_id,language,title,summary,fix_steps,
                          severity,confidence,taxonomy_json,frequency,metadata_json,updated_at)
       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
       ON CONFLICT(issue_id) DO UPDATE SET
         title=excluded.title, summary=excluded.summary, fix_steps=excluded.fix_steps,
         severity=excluded.severity, confidence=excluded.confidence, frequency=excluded.frequency,
         taxonomy_json=excluded.taxonomy_json, metadata_json=excluded.metadata_json, updated_at=excluded.updated_at
    """,
    (doc['issue_id'], doc['source'], doc.get('source_rule_id'), doc.get('language'),
     doc['title'], doc.get('summary'), doc.get('fix_steps'),
     doc.get('severity'), doc.get('confidence'),
     json.dumps(doc.get('taxonomy', {}), ensure_ascii=False),
     doc.get('frequency'),
     json.dumps(doc.get('metadata', {}), ensure_ascii=False),
     doc.get('updated_at'))
    )
    cur.execute('DELETE FROM signals WHERE issue_id=?', (doc['issue_id'],))
    for s in doc.get('signals', []):
        cur.execute('INSERT INTO signals(issue_id,kind,value) VALUES(?,?,?)', (doc['issue_id'], s['kind'], s['value']))
    cur.execute('DELETE FROM references_web WHERE issue_id=?', (doc['issue_id'],))
    for r in doc.get('references', []):
        cur.execute('INSERT INTO references_web(issue_id,label,url,license) VALUES(?,?,?,?)', (doc['issue_id'], r['label'], r['url'], r.get('license')))

for doc in iter_docs():
    upsert_issue(doc)

# rebuild FTS content
cur.execute('DELETE FROM fts_issues')
cur.execute(
    """
    INSERT INTO fts_issues(rowid,title,summary,fix_steps,signals_concat,language)
    SELECT rowid, title, COALESCE(summary,''), COALESCE(fix_steps,''),
           COALESCE((SELECT TRIM(GROUP_CONCAT(value,' ')) FROM signals s WHERE s.issue_id=i.issue_id),'') AS signals_concat,
           COALESCE(language,'')
    FROM issues i
    """
)
con.commit(); con.close()
print(f'Built {DB}')
