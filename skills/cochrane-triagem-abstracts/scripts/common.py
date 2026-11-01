"""Utilitários compartilhados pelos scripts da skill cochrane-triagem-abstracts.

Formato de registro (artigos/_registros/<ID>.json):
  id, url, title, authors[list], citation, journal, year, volume, issue, pages, doi, accession,
  publication_type, language, sourced_from, abstract (str|None), section, captured_at, origin
"""
import hashlib, json, os, re, time

REGISTRY_HINTS = ('trialsearch.who.int', 'clinicaltrials.gov', 'ICTRP', 'CT.gov', 'isrctn', 'anzctr', 'chictr')
NO_ABSTRACT = 'does not have an abstract'


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def record_url(rid):
    if rid.upper().startswith('CD'):
        return f'https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.{rid.upper()}/full'
    return f'https://www.cochranelibrary.com/central/doi/10.1002/central/{rid}/full'


def norm_title(t):
    return re.sub(r'[^a-z0-9]', '', (t or '').lower())


def is_registry(item):
    blob = ' '.join(str(item.get(k) or '') for k in ('src', 'source', 'meta', 'citation', 'sourced_from', 'journal'))
    return any(h.lower() in blob.lower() for h in REGISTRY_HINTS)


def is_protocol(item):
    t = (item.get('title') or '').lower()
    ab = (item.get('abstract') or '')[:600].lower()
    return item.get('section') == 'cochrane_protocol' or 'protocol for' in t or ': protocol' in t or \
        'study protocol' in t or 'this protocol describes' in ab or 'design and rationale' in t


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def load_json(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default


def dump_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def split_citation(cit):
    """'BMC nephrology, 2024, 25(1), 350' -> journal, year, volume, issue, pages."""
    m = re.match(r'(.+?), (\d{4})(?:, ([^,(]+)(?:\(([^)]*)\))?)?(?:, (.+))?$', (cit or '').strip())
    if not m:
        return dict(journal=cit, year=None, volume=None, issue=None, pages=None)
    return dict(journal=m.group(1).strip(), year=int(m.group(2)), volume=(m.group(3) or '').strip() or None,
                issue=m.group(4), pages=(m.group(5) or '').strip() or None)
