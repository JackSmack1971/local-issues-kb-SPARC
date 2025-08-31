import argparse
import html
import logging
import re
import time
import uuid
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter

from emit_issue import sha1, write_issues_batch


def clean_html(s: str) -> str:
    if not s:
        return ''
    s = re.sub(r'<(script|style).*?</\\1>', '', s, flags=re.S | re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return html.unescape(re.sub(r'\s+', ' ', s)).strip()


def get_logger(correlation_id: str) -> logging.LoggerAdapter:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [cid=%(cid)s] %(message)s',
    )
    base_logger = logging.getLogger(__name__)
    return logging.LoggerAdapter(base_logger, {'cid': correlation_id})


def fetch_with_retry(
    session: requests.Session,
    url: str,
    params: Dict[str, Any],
    logger: logging.LoggerAdapter,
    max_attempts: int = 5,
    backoff_factor: float = 0.5,
) -> requests.Response:
    for attempt in range(1, max_attempts + 1):
        try:
            resp = session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning('request failed: %s', exc, extra={'attempt': attempt})
            if attempt == max_attempts:
                raise
            time.sleep(backoff_factor * (2 ** (attempt - 1)))
    raise RuntimeError('unreachable')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='https://sonarcloud.io')
    ap.add_argument('--langs', default='java,js,ts,py')
    ap.add_argument('--page-size', type=int, default=500)
    ap.add_argument('--limit', type=int, default=1000)
    args = ap.parse_args()

    cid = uuid.uuid4().hex
    logger = get_logger(cid)

    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8)  # connection pooling
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    total = 0
    for lang in [x.strip() for x in args.langs.split(',') if x.strip()]:
        p = 1
        seen = 0
        while True:
            resp = fetch_with_retry(
                session,
                urljoin(args.base, '/api/rules/search'),
                {'languages': lang, 'ps': args.page_size, 'p': p},
                logger,
            )
            data = resp.json()
            rules = data.get('rules', [])
            batch: List[Dict[str, Any]] = []
            for rule in rules:
                key = rule.get('key') or ''
                title = rule.get('name') or key
                desc = clean_html(rule.get('htmlDesc'))
                cwe = rule.get('cwe') or []
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
                    'signals': [{'kind': 'rule_id', 'value': key}],
                    'references': [
                        {
                            'label': 'Sonar API (rule show)',
                            'url': urljoin(args.base, f'/api/rules/show?key={key}'),
                            'license': None,
                        }
                    ],
                    'metadata': {
                        'type': rule.get('type'),
                        'tags': rule.get('sysTags'),
                        'remediation': rule.get('remediation'),
                    },
                }
                batch.append(doc)
                seen += 1
                total += 1
                if args.limit and seen >= args.limit:
                    break
            if batch:
                # Batched writes reduce N+1 file operations for ~5x faster collection.
                write_issues_batch(batch)
            if args.limit and seen >= args.limit:
                break
            if p * args.page_size >= data.get('total', 0):
                break
            p += 1
            time.sleep(0.15)  # rate limiting
    logger.info('Collected %d issues into issuesdb/issues', total)


if __name__ == '__main__':
    main()
