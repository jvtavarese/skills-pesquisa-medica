"""Utilitários compartilhados pelos scripts da skill cochrane-triagem-abstracts.

Formato de registro (artigos/_registros/<ID>.json):
  id, url, title, authors[list], citation, journal, year, volume, issue, pages, doi, accession,
  publication_type, language, sourced_from, abstract (str|None), section, captured_at, origin,
  pmid (str|None: PMID do MESMO registro, tirado do Accession Number "PUBMED n" da Cochrane),
  abstract_source ("cochrane" | "pubmed" | None)
Campos opcionais gravados por fetch_pubmed.py: abstract_pmid, abstract_fetched_at, abstract_pubmed,
  abstract_pubmed_match, abstract_pubmed_similarity, pubmed_check
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


_PMID_PATTERNS = (
    re.compile(r'pub\s?med(?:\s*(?:id|accession(?:\s*number)?))?\s*[:#]?\s*(\d{1,9})\b', re.I),
    re.compile(r'\bPMID\s*[:#]?\s*(\d{1,9})\b', re.I),
    re.compile(r'pubmed\.ncbi\.nlm\.nih\.gov/(\d{1,9})', re.I),
    re.compile(r'ncbi\.nlm\.nih\.gov/pubmed/(\d{1,9})', re.I),
)
# Campos em que um número puro já é o PMID (campo PM das exportações, campo pmid do registro).
_PMID_BARE_KEYS = ('pmid', 'PM', 'PMID')
_PMID_TEXT_KEYS = ('accession', 'AN', 'PM', 'PMID', 'url', 'href', 'US', 'UR', 'L2', 'links')


def extract_pmid(record_or_text):
    """Devolve o PMID (str) a partir de 'PUBMED 39402480', 'PubMed 39402480', 'PMID: 123', campo PM,
    ou URLs pubmed.ncbi.nlm.nih.gov/<n>; aceita texto, lista ou dicionário de registro. Senão, None.
    Não confunde com outros números (EMBASE, CINAHL, DOI): só aceita número puro em campos PM/pmid."""
    x = record_or_text
    if x is None:
        return None
    if isinstance(x, dict):
        for k in _PMID_BARE_KEYS:
            for v in (x.get(k) if isinstance(x.get(k), list) else [x.get(k)]):
                if v is not None and re.fullmatch(r'\s*\d{1,9}\s*', str(v)):
                    return str(v).strip()
        for k in _PMID_TEXT_KEYS:
            r = extract_pmid(x.get(k))
            if r:
                return r
        return None
    if isinstance(x, (list, tuple)):
        for v in x:
            r = extract_pmid(v)
            if r:
                return r
        return None
    for pat in _PMID_PATTERNS:
        m = pat.search(str(x))
        if m and m.group(1).lstrip('0'):
            return m.group(1).lstrip('0')
    return None


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


ID_RE = re.compile(r'(CN-\d+|CD\d+(?:\.PUB\d+)?)', re.I)


def valid_id(rid):
    """True só para IDs Cochrane (CN-NNNN ou CDNNNN[.PUBn]); evita usar texto arbitrário em nomes de arquivo."""
    return bool(rid) and bool(ID_RE.fullmatch(str(rid).strip()))
