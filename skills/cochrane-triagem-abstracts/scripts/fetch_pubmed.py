#!/usr/bin/env python3
"""OPCIONAL: completa o abstract de registros CENTRAL pelo PubMed (NCBI E-utilities), sem navegador.

Descoberta e contagens continuam 100% Cochrane. Este script só busca o abstract do MESMO registro:
o PMID vem do próprio registro Cochrane (Accession Number "PUBMED <n>", campo PM da exportação).
Nada é inventado: o abstract do PubMed só é aceito se o título do PubMed bater com o título da
Cochrane (similaridade normalizada >= 0,90); senão é rejeitado como "titulo_divergente".

Trabalha em <dir>/artigos/_registros/*.json, ANTES de build_packets.py. Itens de busca
(buscas/S-*.json) sem registro viram um registro mínimo apenas se o item já trouxer o PMID
(ex.: veio de parse_export.py); os demais são listados no resumo e ficam como estão.

Modos:
  completar  (padrão) preenche só registros sem abstract. Grava: abstract (texto do PubMed),
             abstract_source="pubmed", abstract_pmid, abstract_fetched_at.
  substituir busca no PubMed todo registro com PMID, mas NUNCA sobrescreve o abstract da Cochrane:
             grava abstract_pubmed ao lado, com abstract_pubmed_match ("igual" | "quase_igual" |
             "diferente") e abstract_pubmed_similarity, para comparação. Registros sem abstract
             são completados como no modo completar.
Registros com abstract da Cochrane recebem abstract_source="cochrane" (se faltar). Todo registro
consultado recebe pubmed_check (status, PMID, similaridade do título, DOI/ano do PubMed).
O XML bruto fica em artigos/_pubmed_cache/<pmid>.xml; --offline usa só esse cache.
Um relatório por registro é salvo em artigos/_pubmed_relatorio.json.

Exemplos:
  fetch_pubmed.py --dir levantamento-x
  fetch_pubmed.py --dir levantamento-x --mode substituir --email voce@exemplo.com
  fetch_pubmed.py --dir levantamento-x --ids CN-02744917,CN-02746512 --buscar-pmid-por-doi
Chave da API (opcional, sobe o limite de 3 para 10 requisições/s): --api-key ou NCBI_API_KEY.
"""
import argparse, difflib, glob, json, os, re, ssl, sys, time
import urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump_json, extract_pmid, load_json, now, valid_id

EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
TOOL = 'cochrane-triagem-abstracts'
BATCH = 200
TITLE_MIN = 0.90
ABSTRACT_NEAR = 0.95


def norm_text(t):
    t = (t or '').lower().replace('‐', '-').replace('‑', '-')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9]+', ' ', t)).strip()


def similarity(a, b):
    a, b = norm_text(a), norm_text(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def ssl_context():
    """Contexto TLS com verificação; soma os certificados do sistema (o Python do python.org no macOS
    não traz CAs próprias) e do certifi, se instalado. Nunca desliga a verificação."""
    ctx = ssl.create_default_context()
    extra = ['/etc/ssl/cert.pem', '/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt']
    try:
        import certifi
        extra.append(certifi.where())
    except ImportError:
        pass
    for f in extra:
        if os.path.exists(f):
            try:
                ctx.load_verify_locations(cafile=f)
            except (ssl.SSLError, OSError):
                pass
    return ctx


class Client:
    def __init__(self, api_key=None, email=None):
        self.api_key, self.email = api_key, email
        self.interval = 0.11 if api_key else 0.34  # <=10 req/s com chave, <=3 sem chave
        self.last = 0.0
        self.ctx = ssl_context()

    def call(self, util, params, tries=5):
        p = dict(params, tool=TOOL)
        if self.email:
            p['email'] = self.email
        if self.api_key:
            p['api_key'] = self.api_key
        data = urllib.parse.urlencode(p).encode()
        err = None
        for k in range(tries):
            wait = self.interval - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                req = urllib.request.Request(EUTILS + util, data=data, headers={'User-Agent': TOOL})
                with urllib.request.urlopen(req, timeout=30, context=self.ctx) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                err = e
                if e.code not in (429, 500, 502, 503, 504):
                    raise
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                if isinstance(getattr(e, 'reason', None), ssl.SSLCertVerificationError):
                    raise RuntimeError(f'certificado TLS não verificado ({e.reason}); aponte SSL_CERT_FILE para o '
                                       'pacote de CAs do sistema ou rode "Install Certificates.command" do Python') from e
                err = e
            time.sleep(2 ** (k + 1))
        raise RuntimeError(f'falha após {tries} tentativas: {err}')


def text_of(el):
    return re.sub(r'\s+', ' ', ''.join(el.itertext())).strip() if el is not None else ''


def parse_article(el):
    """Extrai PMID, título, abstract (com rótulos de seção), periódico, ano e DOI de um PubmedArticle."""
    pmid = text_of(el.find('.//MedlineCitation/PMID')) or text_of(el.find('.//BookDocument/PMID')) or text_of(el.find('.//PMID'))
    title = text_of(el.find('.//Article/ArticleTitle')) or text_of(el.find('.//BookDocument/ArticleTitle')) \
        or text_of(el.find('.//BookTitle'))
    vern = text_of(el.find('.//Article/VernacularTitle'))
    parts = []
    abs_el = el.find('.//Article/Abstract')
    if abs_el is None:
        abs_el = el.find('.//BookDocument/Abstract')
    for at in (abs_el.findall('AbstractText') if abs_el is not None else []):
        t = text_of(at)
        if not t:
            continue
        lab = (at.get('Label') or '').strip()
        parts.append(f'{lab}: {t}' if lab and lab.upper() not in ('UNLABELLED', 'UNASSIGNED') else t)
    journal = text_of(el.find('.//Article/Journal/Title')) or text_of(el.find('.//Article/Journal/ISOAbbreviation'))
    year = text_of(el.find('.//Article/Journal/JournalIssue/PubDate/Year'))
    if not year:
        m = re.search(r'\d{4}', text_of(el.find('.//Article/Journal/JournalIssue/PubDate/MedlineDate'))
                      or text_of(el.find('.//ArticleDate/Year')))
        year = m.group(0) if m else ''
    doi = next((text_of(a) for a in el.findall('./PubmedData/ArticleIdList/ArticleId') if a.get('IdType') == 'doi'), '') or \
        next((text_of(a) for a in el.iter('ELocationID') if a.get('EIdType') == 'doi'), '')
    return dict(pmid=pmid, title=title, vernacular_title=vern or None, abstract='\n'.join(parts) or None,
                journal=journal or None, year=int(year) if year.isdigit() else None, doi=doi or None)


def cache_path(cache, pmid):
    return os.path.join(cache, f'{pmid}.xml')


def load_cached(cache, pmid):
    p = cache_path(cache, pmid)
    if not os.path.exists(p):
        return None
    root = ET.parse(p).getroot()
    el = next(iter(root), None) if root.tag == 'PubmedArticleSet' else root
    return parse_article(el) if el is not None else None


def fetch_batch(client, cache, pmids):
    """efetch em lote; salva cada artigo em cache e devolve {pmid: dados}."""
    raw = client.call('efetch.fcgi', dict(db='pubmed', id=','.join(pmids), retmode='xml'))
    root = ET.fromstring(raw)
    out = {}
    for el in list(root):
        if el.tag not in ('PubmedArticle', 'PubmedBookArticle'):
            continue
        d = parse_article(el)
        if not d['pmid']:
            continue
        wrap = ET.Element('PubmedArticleSet'); wrap.append(el)
        os.makedirs(cache, exist_ok=True)
        ET.ElementTree(wrap).write(cache_path(cache, d['pmid']), encoding='utf-8', xml_declaration=True)
        out[d['pmid']] = d
    return out


def pmid_by_doi(client, doi):
    raw = client.call('esearch.fcgi', dict(db='pubmed', term=f'{doi}[doi]', retmode='json'))
    ids = json.loads(raw).get('esearchresult', {}).get('idlist', [])
    return ids[0] if len(ids) == 1 else None


def collect(dirpath, ids):
    """Registros de artigos/_registros + registros mínimos de itens de busca com PMID e sem registro."""
    regdir = os.path.join(dirpath, 'artigos', '_registros')
    recs, sem_registro = {}, []
    for p in sorted(glob.glob(os.path.join(regdir, '*.json'))):
        r = load_json(p)
        rid = r.get('id') or os.path.basename(p)[:-5]
        if not valid_id(rid) or os.path.basename(p)[:-5] != rid:
            print(f'AVISO: ignorando {os.path.basename(p)} (ID inválido ou diferente do nome do arquivo)'); continue
        if ids and rid not in ids:
            continue
        recs[rid] = (p, r)
    for p in sorted(glob.glob(os.path.join(dirpath, 'buscas', 'S-*.json'))):
        for it in (load_json(p) or {}).get('items', []):
            rid = it.get('id')
            if not rid or rid in recs or (ids and rid not in ids):
                continue
            if not valid_id(rid):
                print(f'AVISO: item de busca com ID inválido ignorado: {str(rid)[:40]!r}'); continue
            pm = extract_pmid(it)
            if not pm:
                if rid not in sem_registro:
                    sem_registro.append(rid)
                continue
            r = dict(id=rid, title=it.get('title'), citation=(it.get('meta') or '').split(' | added')[0] or None,
                     url=it.get('href'), section=it.get('section'), sourced_from=it.get('src') or None,
                     pmid=pm, abstract=None, abstract_source=None, captured_at=now(),
                     origin='item_busca_cochrane', source_file=os.path.relpath(p, dirpath))
            recs[rid] = (os.path.join(regdir, rid + '.json'), r)
    return recs, sem_registro


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dir', required=True, help='diretório de trabalho do levantamento')
    ap.add_argument('--mode', choices=['completar', 'substituir'], default='completar')
    ap.add_argument('--ids', help='lista de IDs Cochrane separados por vírgula (padrão: todos)')
    ap.add_argument('--api-key', default=os.environ.get('NCBI_API_KEY'), help='chave NCBI (ou env NCBI_API_KEY)')
    ap.add_argument('--email', default=os.environ.get('NCBI_EMAIL'), help='e-mail de contato para o NCBI (ou env NCBI_EMAIL)')
    ap.add_argument('--offline', action='store_true', help='não acessa a rede; usa só artigos/_pubmed_cache')
    ap.add_argument('--buscar-pmid-por-doi', action='store_true',
                    help='para registros SEM PMID na Cochrane, procura o PMID pelo DOI informado pela Cochrane '
                         '(esearch); a checagem de título continua obrigatória')
    a = ap.parse_args()
    ids = {x.strip() for x in a.ids.split(',') if x.strip()} if a.ids else None
    cache = os.path.join(a.dir, 'artigos', '_pubmed_cache')
    client = Client(a.api_key, a.email)
    recs, sem_registro = collect(a.dir, ids)
    if not recs and not sem_registro:
        sys.exit(f'Nenhum registro em {os.path.join(a.dir, "artigos", "_registros")}.')

    stats = {k: [] for k in ('preenchido', 'ja_tinha_abstract', 'sem_pmid', 'pubmed_sem_abstract', 'titulo_divergente',
                             'nao_encontrado_no_pubmed', 'sem_cache_offline', 'erro', 'comparado')}
    report, todo = {}, {}
    for rid, (p, r) in recs.items():
        if r.get('abstract') and not r.get('abstract_source'):
            r['abstract_source'] = 'cochrane'
        pm = str(r.get('pmid') or '').strip()
        if not re.fullmatch(r'\d{1,9}', pm):
            pm = extract_pmid(r) or ''
        pm = pm or None
        via = 'cochrane'
        if pm and not r.get('pmid'):
            r['pmid'] = pm
        need = a.mode == 'substituir' or not r.get('abstract')
        if not need:
            stats['ja_tinha_abstract'].append(rid); report[rid] = 'ja_tinha_abstract'
            dump_json(r, p); continue
        doi_tried = False
        if not pm and a.buscar_pmid_por_doi and r.get('doi') and not a.offline:
            doi_tried = True
            try:
                pm = pmid_by_doi(client, r['doi']); via = 'doi'
            except Exception as e:
                print(f'ERRO {rid}: busca por DOI falhou: {e}')
        if not pm:
            stats['sem_pmid'].append(rid); report[rid] = 'sem_pmid'
            if not r.get('abstract'):
                r['pubmed_check'] = dict(status='sem_pmid', doi_consultado=doi_tried, checked_at=now())
            if r.get('origin') != 'item_busca_cochrane':
                dump_json(r, p)
            continue
        todo[rid] = (pm, via)

    data = {}
    for rid, (pm, _) in todo.items():
        if os.path.exists(cache_path(cache, pm)):
            try:
                data[pm] = load_cached(cache, pm)
            except ET.ParseError:
                pass
    missing = sorted({pm for pm, _ in todo.values() if pm not in data})
    failed = set()
    if missing and not a.offline:
        for i in range(0, len(missing), BATCH):
            chunk = missing[i:i + BATCH]
            try:
                data.update(fetch_batch(client, cache, chunk))
            except Exception as e:
                print(f'ERRO no lote {i // BATCH + 1} ({len(chunk)} PMIDs): {e}')
                failed.update(chunk)

    for rid, (pm, via) in todo.items():
        p, r = recs[rid]
        d = data.get(pm)
        chk = dict(pmid=pm, pmid_via=via, checked_at=now())
        if not d:
            st = 'sem_cache_offline' if a.offline else ('erro' if pm in failed else 'nao_encontrado_no_pubmed')
        else:
            ts = max(similarity(r.get('title'), d['title']), similarity(r.get('title'), d.get('vernacular_title')))
            chk.update(pubmed_title=d['title'], title_similarity=round(ts, 3), pubmed_journal=d['journal'],
                       pubmed_year=d['year'], pubmed_doi=d['doi'],
                       doi_match=(d['doi'].lower() == r['doi'].lower()) if d['doi'] and r.get('doi') else None,
                       year_match=(d['year'] == r.get('year')) if d['year'] and r.get('year') else None)
            if ts < TITLE_MIN:
                st = 'titulo_divergente'
            elif not d['abstract']:
                st = 'pubmed_sem_abstract'
            elif r.get('abstract') and r.get('abstract_source') != 'pubmed':
                sim = similarity(r['abstract'], d['abstract'])
                match = 'igual' if norm_text(r['abstract']) == norm_text(d['abstract']) else \
                    ('quase_igual' if sim >= ABSTRACT_NEAR else 'diferente')
                r.update(abstract_pubmed=d['abstract'], abstract_pubmed_pmid=pm, abstract_pubmed_match=match,
                         abstract_pubmed_similarity=round(sim, 3), abstract_pubmed_fetched_at=now())
                st = 'comparado'; chk['abstract_match'] = match
            else:
                r.update(abstract=d['abstract'], abstract_source='pubmed', abstract_pmid=pm, abstract_fetched_at=now())
                if via == 'doi':
                    r['pmid'] = pm; r['pmid_via'] = 'doi'
                st = 'preenchido'
        chk['status'] = st
        r['pubmed_check'] = chk
        stats[st].append(rid); report[rid] = chk
        # Registro mínimo criado a partir do item de busca só é salvo se o PubMed confirmou e preencheu;
        # senão build_packets congelaria um pacote sem metadados.
        if r.get('origin') != 'item_busca_cochrane' or st == 'preenchido':
            dump_json(r, p)
        if st in ('titulo_divergente', 'erro'):
            print(f'{st.upper()} {rid} PMID {pm}: Cochrane="{(r.get("title") or "")[:70]}" | '
                  f'PubMed="{((d or {}).get("title") or "")[:70]}"')

    for rid in sem_registro:
        report[rid] = 'item_de_busca_sem_registro_e_sem_pmid'
    rep_path = os.path.join(a.dir, 'artigos', '_pubmed_relatorio.json')
    prev = (load_json(rep_path) or {}).get('registros', {})  # execuções parciais (--ids) somam ao relatório
    prev.update(report)
    dump_json(dict(gerado_em=now(), modo=a.mode, offline=a.offline, registros=prev), rep_path)

    cmp_ = stats['comparado']
    m = {k: sum(1 for x in cmp_ if recs[x][1].get('abstract_pubmed_match') == k) for k in ('igual', 'quase_igual', 'diferente')}
    print(f'\nRESUMO fetch_pubmed (modo {a.mode}{", offline" if a.offline else ""})')
    rows = [('preenchidos pelo PubMed', 'preenchido'), ('já tinham abstract (Cochrane)', 'ja_tinha_abstract'),
            ('sem PMID', 'sem_pmid'), ('PubMed sem abstract', 'pubmed_sem_abstract'),
            ('título divergente (rejeitado)', 'titulo_divergente'), ('PMID não encontrado no PubMed', 'nao_encontrado_no_pubmed'),
            ('sem cache (offline)', 'sem_cache_offline'), ('erros', 'erro')]
    for label, k in rows:
        if stats[k] or k in ('preenchido', 'ja_tinha_abstract', 'sem_pmid', 'pubmed_sem_abstract', 'titulo_divergente', 'erro'):
            extra = f'  [{", ".join(stats[k])}]' if stats[k] and k != 'ja_tinha_abstract' and len(stats[k]) <= 15 else ''
            print(f'  {label}: {len(stats[k])}{extra}')
    if a.mode == 'substituir':
        print(f'  comparados com o abstract da Cochrane: {len(cmp_)} (igual {m["igual"]}, quase igual {m["quase_igual"]}, '
              f'diferente {m["diferente"]})' + (f'  diferentes: {[x for x in cmp_ if recs[x][1].get("abstract_pubmed_match") == "diferente"]}' if m['diferente'] else ''))
    if sem_registro:
        print(f'  itens de busca sem registro e sem PMID conhecido (não tratados): {len(sem_registro)}')
    print('Relatório:', rep_path)


if __name__ == '__main__':
    main()
