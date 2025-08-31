import argparse, requests, time, re, html
from urllib.parse import urljoin
from emit_issue import write_issue, sha1

def clean_html(s):
    if not s: return ''
    s = re.sub(r'<(script|style).*?</\\1>', '', s, flags=re.S|re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return html.unescape(re.sub(r'\s+', ' ', s)).strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='https://sonarcloud.io')
    ap.add_argument('--langs', default='java,js,ts,py')
    ap.add_argument('--page-size', type=int, default=500)
    ap.add_argument('--limit', type=int, default=1000)
    args = ap.parse_args()

    total = 0
    for lang in [x.strip() for x in args.langs.split(',') if x.strip()]:
        p = 1; seen = 0
        while True:
            r = requests.get(urljoin(args.base, '/api/rules/search'), params={'languages': lang, 'ps': args.page_size, 'p': p})
            r.raise_for_status()
            data = r.json(); rules = data.get('rules', [])
            for rule in rules:
                key   = rule.get('key') or ''
                title = rule.get('name') or key
                desc  = clean_html(rule.get('htmlDesc'))
                cwe   = rule.get('cwe') or []
                owasp = rule.get('owaspTop10') or []
                issue_id = sha1(f'sonar|{key}')
                doc = {
                    'issue_id': issue_id,
                    'source': 'sonar',
                    'source_rule_id': key,
                    'language': rule.get('lang'),
                    'title': title[:240],
                    'summary': (desc[:1000] if desc else None),
                    'root_cause': None,
                    'fix_steps': None,
                    'autofix_snippet': None,
                    'severity': rule.get('severity'),
                    'confidence': None,
                    'taxonomy': {'cwe': cwe, 'owasp': owasp},
                    'frequency': None,
                    'signals': [{'kind':'rule_id','value':key}],
                    'references': [{ 'label':'Sonar API (rule show)', 'url': urljoin(args.base, f'/api/rules/show?key={key}'), 'license': None }],
                    'metadata': { 'type': rule.get('type'), 'tags': rule.get('sysTags'), 'remediation': rule.get('remediation') }
                }
                write_issue(doc)
                seen += 1; total += 1
                if args.limit and seen >= args.limit:
                    break
            if args.limit and seen >= args.limit: break
            if p * args.page_size >= data.get('total', 0): break
            p += 1; time.sleep(0.15)
    print(f'Collected {total} issues into issuesdb/issues')

if __name__ == '__main__':
    main()
