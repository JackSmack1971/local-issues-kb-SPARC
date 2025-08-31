import pathlib, json, datetime
from json_utils import load_json

ROOT = pathlib.Path('.')
MB   = ROOT / 'memory_bank'
ISS  = ROOT / 'issuesdb' / 'issues'

def count_docs():
    total = 0; by_source = {}; by_lang = {}
    for p in ISS.glob('*/*/*.json'):
        total += 1
        doc = load_json(p)
        src = doc['source']; by_source[src] = by_source.get(src,0)+1
        lang = (doc.get('language') or 'unknown').lower()
        by_lang[lang] = by_lang.get(lang,0)+1
    return total, by_source, by_lang

def frontmatter(title: str):
    now = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    return (
        '---\n'
        f'version: 1\n'
        f'updated: {now}\n'
        f'title: {title}\n'
        '---\n'
    )

def render_product_context():
    return frontmatter('Product Context') + (
        '# Product Context\n\n'
        '**Purpose:** Maintain a local, file-first “Issues→Fixes” knowledge base for AI agents.\n\n'
        '**Users:** SPARC/Roo orchestrator, specialist agents (architect, coder, tester).\n\n'
        '**Constraints:** Local-only, auditable, license-aware; files are the source of truth; SQLite FTS for fast search.\n'
    )

def render_system_patterns(total, by_source, by_lang):
    rows = '\n'.join([f'- {k}: {v}' for k,v in sorted(by_source.items())]) or '- (none)'
    langs = '\n'.join([f'- {k}: {v}' for k,v in sorted(by_lang.items())]) or '- (none)'
    return frontmatter('System Patterns') + (
        '# System Patterns\n\n'
        f'## Dataset Snapshot\n- Total issues: {total}\n- By source:\n{rows}\n- By language:\n{langs}\n\n'
        '## Access Patterns\n'
        '1. Search via `issuesdb/issues.sqlite` (FTS5) → `issue_id` → open JSON.\n'
        '2. File-first reads for deterministic traversal.\n'
        '3. RAG via `exports/chunks.jsonl`.\n\n'
        '## Quality Gates\n- Enforce JSON schema on write.\n- Ensure ≥1 signal.\n- Always attach license/attribution URLs.\n'
    )

def render_decision_log():
    return frontmatter('Decision Log') + (
        '# Architectural Decision Log\n\n'
        '## ADR-001: Files as Source of Truth\n- Status: Accepted\n- Decision: One JSON per issue.\n\n'
        '## ADR-002: SQLite FTS5 for Local Search\n- Status: Accepted\n- Decision: Contentless FTS with stemming/prefix.\n\n'
        '## ADR-003: Chunk Export for LLMs\n- Status: Accepted\n- Decision: Export `exports/chunks.jsonl`.\n'
    )

def render_progress():
    return frontmatter('Progress') + (
        '# Progress\n\n- [ ] Bootstrap Sonar rules\n- [ ] Validate JSON\n- [ ] Build index\n- [ ] Export chunks\n'
        '- [ ] Wire into SPARC ingest\n- [ ] Add SO/other sources with attribution\n- [ ] Set up refresh\n'
    )

def main():
    total, by_source, by_lang = count_docs()
    (MB / 'productContext.md').write_text(render_product_context(), encoding='utf-8')
    (MB / 'systemPatterns.md').write_text(render_system_patterns(total, by_source, by_lang), encoding='utf-8')
    (MB / 'decisionLog.md').write_text(render_decision_log(), encoding='utf-8')
    (MB / 'progress.md').write_text(render_progress(), encoding='utf-8')
    print('Rendered memory_bank/*.md')

if __name__ == '__main__':
    main()
