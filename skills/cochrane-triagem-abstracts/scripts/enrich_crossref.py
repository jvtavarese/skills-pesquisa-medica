#!/usr/bin/env python3
"""Confere os metadados de cada pacote no Crossref (api.crossref.org) e registra divergências.

Para cada artigo de artigos/manifesto_pacotes.json, lê artigos/ART-NNNN/metadados.json (que NUNCA é
alterado) e grava um arquivo NOVO artigos/ART-NNNN/metadados_crossref.json com o que o Crossref
informa e a lista de divergências em relação à Cochrane.

Como o artigo é localizado (nunca por palpite):
  1. Com DOI na Cochrane: consulta direta https://api.crossref.org/works/<doi>  -> matched_by "doi".
  2. Sem DOI (ou DOI inexistente no Crossref): busca bibliográfica (título + 1º autor + ano, 3 resultados)
     e só aceita se o título normalizado for quase idêntico (similaridade >= 0.93) E o ano bater (±1)
     -> matched_by "titulo". Caso contrário, matched_by null (sem correspondência).

Campos comparados: título (normalizado), ano, volume, número (issue), páginas e DOI. A Cochrane continua
sendo a fonte principal: build_report.py só usa o Crossref para preencher campos vazios e lista as
divergências em resultados/triagem_abstracts.md.

As respostas brutas ficam em artigos/_crossref_cache/, então reexecuções funcionam sem internet
(--offline usa só o cache). Só usa a biblioteca padrão do Python.

Uso:
  enrich_crossref.py --dir levantamento-x
  enrich_crossref.py --dir levantamento-x --only ART-0003,ART-0016 --mailto voce@exemplo.com
  enrich_crossref.py --dir levantamento-x --offline

O e-mail (opcional, recomendado pelo Crossref para o "polite pool") vem de --mailto ou da variável de
ambiente CROSSREF_MAILTO.
"""
import argparse, difflib, hashlib, html, json, os, re, ssl, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request

API = 'https://api.crossref.org/works'
TITLE_MIN = 0.93      # aceitar busca por título
RELIABLE_MIN = 0.80   # registro achado por DOI é o mesmo artigo?
SLEEP = 0.2
TIMEOUT = 20
MAX_RETRIES = 3


# ------------------------------------------------------------------ utilidades
def now():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def dump_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


def norm_text(t):
    """Título comparável: sem HTML, sem acentos, minúsculo, só letras/dígitos separados por espaço."""
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t or ''))
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', t.lower()).split())


ABSTRACT_NO = re.compile(r'^[a-z]{0,3}\d{1,5}\s*')  # "SP634", "400", "P1549" antes do título de resumos


def title_ratio(a, b, strip_prefix=False):
    a, b = norm_text(a), norm_text(b)
    if not a or not b:
        return 0.0
    r = difflib.SequenceMatcher(None, a, b).ratio()
    if strip_prefix:  # usado só para conferir, nunca para aceitar uma busca por título
        r = max(r, difflib.SequenceMatcher(None, a, ABSTRACT_NO.sub('', b)).ratio())
    return r


def titles_equal(cochrane, crossref):
    a, b = norm_text(cochrane), norm_text(crossref)
    return a.replace(' ', '') == b.replace(' ', '') or a.replace(' ', '') == ABSTRACT_NO.sub('', b).replace(' ', '')


def norm_simple(v):
    v = str(v or '').lower()
    v = re.sub(r'^(volume|vol\.?|issue|no\.?)\s*', '', v.strip())
    v = re.sub(r'suppl(ement)?\.?|supl\.?', 's', v)
    return re.sub(r'[^a-z0-9]', '', v)


def norm_pages(p):
    """'585‐592', '585-92', 'i560-i560' -> forma canônica comparável."""
    p = re.sub(r'[‐-―−]', '-', str(p or '')).lower().replace(' ', '')
    if not p:
        return ''
    if '-' in p:
        a, _, b = p.partition('-')
        if a == b or not b:
            return a
        if a.isdigit() and b.isdigit() and len(b) < len(a):  # 1503-11 -> 1503-1511
            b = a[:len(a) - len(b)] + b
        return f'{a}-{b}'
    return p


def norm_doi(d):
    d = (d or '').strip().lower()
    return re.sub(r'^(https?://(dx\.)?doi\.org/|doi:)', '', d)


def safe_name(s):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', s)[:150]


# ------------------------------------------------------------------ HTTP + cache
def ssl_context():
    """Contexto TLS com verificação sempre ligada. O Python do python.org no macOS às vezes vem sem
    certificados raiz; nesse caso usa certifi (se instalado) ou o pacote de certificados do sistema."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats().get('x509_ca'):
        for f in ('/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt'):
            if os.path.exists(f):
                ctx.load_verify_locations(cafile=f)
                break
    return ctx


class Client:
    def __init__(self, cache_dir, mailto, offline):
        self.cache_dir, self.offline = cache_dir, offline
        ua = 'cochrane-triagem-abstracts (https://github.com/jvtavarese/skills-pesquisa-medica'
        ua += f'; mailto:{mailto})' if mailto else ')'
        self.headers = {'User-Agent': ua, 'Accept': 'application/json'}
        self.mailto = mailto
        self.last = 0.0
        self.calls = 0
        self.ctx = ssl_context()
        self.dead = None  # depois de falhas seguidas de rede, para de tentar e usa só o cache
        self.fails = 0
        os.makedirs(cache_dir, exist_ok=True)

    def get(self, key, url):
        """Retorna (status, json|None). Status: 200, 404, 'sem_cache' ou 'erro:<msg>'."""
        path = os.path.join(self.cache_dir, safe_name(key) + '.json')
        cached = load_json(path)
        if cached is not None:
            return cached.get('_status', 200), cached.get('body')
        if self.offline:
            return 'sem_cache', None
        if self.dead:
            return f'erro:{self.dead}', None
        if self.mailto:
            url += ('&' if '?' in url else '?') + 'mailto=' + urllib.parse.quote(self.mailto)
        err = None
        for attempt in range(MAX_RETRIES + 1):
            wait = SLEEP - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time(); self.calls += 1
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=TIMEOUT, context=self.ctx) as r:
                    body = json.loads(r.read().decode('utf-8'))
                self.fails = 0
                dump_json({'_status': 200, '_url': url, '_retrieved_at': now(), 'body': body}, path)
                return 200, body
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    dump_json({'_status': 404, '_url': url, '_retrieved_at': now(), 'body': None}, path)
                    return 404, None
                err = f'HTTP {e.code}'
                if e.code != 429 and e.code < 500:
                    break
                ra = e.headers.get('Retry-After') if e.headers else None
                backoff = float(ra) if ra and ra.isdigit() else 2 ** attempt
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                reason = getattr(e, 'reason', e)
                err = f'{type(reason).__name__}: {reason}'
                if isinstance(reason, ssl.SSLCertVerificationError):
                    self.dead = ('certificado TLS não verificado — no macOS rode "Install Certificates.command" '
                                 'da pasta do Python ou "pip install certifi"')
                    return f'erro:{self.dead}', None
                backoff = 2 ** attempt
            if attempt < MAX_RETRIES:
                time.sleep(min(backoff, 30))
        self.fails += 1
        if self.fails >= 3:
            self.dead = f'{err} (3 artigos seguidos sem resposta; rede indisponível?)'
        return f'erro:{err}', None


# ------------------------------------------------------------------ Crossref -> campos
def years_of(w):
    ys = []
    for k in ('issued', 'published-print', 'published-online', 'published'):
        try:
            y = w[k]['date-parts'][0][0]
            if y:
                ys.append(int(y))
        except (KeyError, IndexError, TypeError, ValueError):
            pass
    return ys


def initials(given):
    parts = re.split(r'[\s\-.]+', given or '')
    return ''.join(p[0].upper() for p in parts if p and p[0].isalpha())


def authors_of(w):
    out = []
    for a in w.get('author') or []:
        if a.get('family'):
            ini = initials(a.get('given'))
            out.append(f"{a['family']} {ini}".strip())
        elif a.get('name'):
            out.append(a['name'])
    return out


def first(lst):
    return (lst or [None])[0] if isinstance(lst, list) else lst


def full_title(w):
    t = html.unescape(re.sub(r'<[^>]+>', '', first(w.get('title')) or '')).strip()
    sub = html.unescape(re.sub(r'<[^>]+>', '', first(w.get('subtitle')) or '')).strip()
    if sub and norm_text(sub) not in norm_text(t):
        t = f'{t}: {sub}' if t else sub
    return t or None


def fields_of(w):
    ys = years_of(w)
    return dict(crossref_doi=w.get('DOI'), title=full_title(w),
                authors=authors_of(w), journal=first(w.get('container-title')), year=ys[0] if ys else None,
                volume=w.get('volume'), issue=w.get('issue'), pages=w.get('page') or w.get('article-number'),
                type=w.get('type'), url=w.get('URL') or (f"https://doi.org/{w['DOI']}" if w.get('DOI') else None))


def discrepancies(m, cr, w):
    out = []
    if m.get('title') and cr.get('title') and not titles_equal(m['title'], cr['title']):
        out.append(dict(field='title', cochrane=m['title'], crossref=cr['title'],
                        similarity=round(title_ratio(m['title'], cr['title'], True), 3)))
    if m.get('year') and cr.get('year'):
        try:
            if int(m['year']) not in years_of(w):
                out.append(dict(field='year', cochrane=m['year'], crossref=cr['year']))
        except (TypeError, ValueError):
            out.append(dict(field='year', cochrane=m['year'], crossref=cr['year']))
    for f in ('volume', 'issue'):
        if m.get(f) and cr.get(f) and norm_simple(m[f]) != norm_simple(cr[f]):
            out.append(dict(field=f, cochrane=m[f], crossref=cr[f]))
    if m.get('pages') and cr.get('pages') and norm_pages(m['pages']) != norm_pages(cr['pages']):
        out.append(dict(field='pages', cochrane=m['pages'], crossref=cr['pages']))
    if m.get('doi') and cr.get('crossref_doi') and norm_doi(m['doi']) != norm_doi(cr['crossref_doi']):
        out.append(dict(field='doi', cochrane=m['doi'], crossref=cr['crossref_doi']))
    return out


def search_by_title(cl, m):
    """Busca bibliográfica estrita. Retorna (work|None, status, melhor_similaridade)."""
    title = m.get('title') or ''
    if not title or not m.get('year'):
        return None, 'sem_titulo_ou_ano', None
    try:
        year = int(m['year'])
    except (TypeError, ValueError):
        return None, 'ano_invalido', None
    au = (m.get('authors') or [''])[0] or ''
    family = au.rsplit(' ', 1)[0] if ' ' in au else au
    q = ' '.join(x for x in (title, family, str(year)) if x)
    url = f"{API}?query.bibliographic={urllib.parse.quote(q)}&rows=3"
    key = 'q_' + hashlib.sha1(q.encode()).hexdigest()[:20]
    status, body = cl.get(key, url)
    if status != 200 or not body:
        return None, str(status), None
    best, best_r = None, 0.0
    for w in (body.get('message') or {}).get('items') or []:
        r = title_ratio(title, full_title(w) or '')
        if r > best_r:
            best, best_r = w, r
        if r >= TITLE_MIN and any(abs(y - year) <= 1 for y in years_of(w)):
            return w, 'ok', round(r, 3)
    return None, 'sem_correspondencia', round(best_r, 3) if best else None


def process(cl, A, aid):
    m = load_json(os.path.join(A, aid, 'metadados.json'))
    if m is None:
        return None
    out = dict(article_id=aid, matched_by=None, crossref_doi=None, title=None, authors=[], journal=None, year=None,
               volume=None, issue=None, pages=None, type=None, url=None, retrieved_at=now(), discrepancies=[])
    work, notes = None, []
    doi = norm_doi(m.get('doi'))
    if doi:
        status, body = cl.get('doi_' + doi, f"{API}/{urllib.parse.quote(doi, safe='/')}")
        if status == 200 and body and body.get('message'):
            work, out['matched_by'] = body['message'], 'doi'
        else:
            notes.append(f'DOI da Cochrane não encontrado no Crossref ({status})')
            if str(status).startswith('erro') or status == 'sem_cache':
                out['status'] = str(status)
    if work is None and out.get('status') is None:
        w, st, sim = search_by_title(cl, m)
        if w is not None:
            work, out['matched_by'] = w, 'titulo'
            out['title_similarity'] = sim
        else:
            notes.append(f'busca por título: {st}' + (f' (melhor similaridade {sim})' if sim is not None else ''))
            if st.startswith('erro') or st == 'sem_cache':
                out['status'] = st
    if work is not None:
        cr = fields_of(work)
        out.update(cr)
        out.setdefault('title_similarity', round(title_ratio(m.get('title'), cr.get('title'), True), 3))
        out['discrepancies'] = discrepancies(m, cr, work)
        out['status'] = 'ok'
        # Confiável = o registro do Crossref é claramente o mesmo artigo. Um DOI da Cochrane que aponta para
        # outra coisa (ex.: o caderno inteiro de pôsteres do congresso) fica registrado, mas não é usado.
        out['confiavel'] = (out['title_similarity'] or 0) >= RELIABLE_MIN
        if out['confiavel'] and out['matched_by'] == 'titulo':
            # Casamento só por título exige também a mesma revista e o mesmo primeiro autor; senão pode ser
            # outra publicação com o mesmo título (ex.: resumo de congresso × artigo completo).
            nj = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
            fam = lambda a: nj((a or '').split(' ')[0])
            j_ok = bool(nj(m.get('journal'))) and (nj(m.get('journal')) in nj(cr.get('journal')) or
                                                   nj(cr.get('journal')) in nj(m.get('journal')) or
                                                   difflib.SequenceMatcher(None, nj(m.get('journal')), nj(cr.get('journal'))).ratio() >= 0.85)
            a_ok = bool((m.get('authors') or [None])[0]) and bool(cr.get('authors')) and \
                fam(m['authors'][0]) == fam(cr['authors'][0])
            if not (j_ok and a_ok):
                out['confiavel'] = False
                out.setdefault('notes', []).append('casou só pelo título, mas revista ou primeiro autor diferem; não usado')
        if not out['confiavel']:
            out.setdefault('notes', []).append(
                f"título do Crossref muito diferente (similaridade {out['title_similarity']}); não usado para completar")
    else:
        out['confiavel'] = False
        out.setdefault('status', 'sem_correspondencia')
    if notes:
        out['notes'] = notes + out.get('notes', [])
    dump_json(out, os.path.join(A, aid, 'metadados_crossref.json'))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dir', required=True, help='diretório de trabalho do levantamento')
    ap.add_argument('--only', help='lista de artigos separados por vírgula (ex.: ART-0001,ART-0002)')
    ap.add_argument('--mailto', default=os.environ.get('CROSSREF_MAILTO'),
                    help='e-mail para o User-Agent do Crossref (padrão: variável CROSSREF_MAILTO)')
    ap.add_argument('--offline', action='store_true', help='não acessa a internet; usa só artigos/_crossref_cache/')
    a = ap.parse_args()
    A = os.path.join(os.path.abspath(a.dir), 'artigos')
    man = load_json(os.path.join(A, 'manifesto_pacotes.json'))
    if not man:
        sys.exit(f'manifesto não encontrado: {os.path.join(A, "manifesto_pacotes.json")} (rode build_packets.py antes).')
    arts = [p['article_id'] for p in man['packets']]
    if a.only:
        want = {x.strip() for x in a.only.split(',') if x.strip()}
        unknown = want - set(arts)
        if unknown:
            print('Ignorados (não estão no manifesto):', ', '.join(sorted(unknown)))
        arts = [x for x in arts if x in want]
    cl = Client(os.path.join(A, '_crossref_cache'), a.mailto, a.offline)
    tally = {'doi': 0, 'titulo': 0, None: 0}
    unreliable = []
    with_disc, failed = [], []
    for aid in arts:
        r = process(cl, A, aid)
        if r is None:
            print(f'{aid}: metadados.json ausente — pulado'); continue
        tally[r['matched_by']] += 1
        if r['discrepancies']:
            with_disc.append(aid)
        if r['matched_by'] and not r['confiavel']:
            unreliable.append(aid)
        if r['status'] not in ('ok', 'sem_correspondencia'):
            failed.append(f"{aid} ({r['status']})")
        flds = ', '.join(d['field'] for d in r['discrepancies'])
        print(f"{aid}: {r['matched_by'] or 'sem correspondência'}" + (f' · divergências: {flds}' if flds else ''))
    print(f"\nResumo Crossref ({len(arts)} artigos): por DOI {tally['doi']} · por título {tally['titulo']} · "
          f"sem correspondência {tally[None]} · com divergências {len(with_disc)}"
          + (f' · requisições à API {cl.calls}' if cl.calls else ''))
    if with_disc:
        print('Com divergências:', ', '.join(with_disc))
    if unreliable:
        print('Registro do Crossref não parece o mesmo artigo (não usado para completar):', ', '.join(unreliable))
    if failed:
        print('Falha de rede ou sem cache (rode de novo depois):', ', '.join(failed))


if __name__ == '__main__':
    main()
