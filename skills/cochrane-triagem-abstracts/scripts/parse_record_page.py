#!/usr/bin/env python3
"""Converte o texto de páginas de registro da Cochrane em registros JSON.

Entrada: arquivos .txt com o innerText completo da página
  (ex.: https://www.cochranelibrary.com/central/doi/10.1002/central/CN-02761934/full),
  nomeados <ID>.txt (ex.: CN-02761934.txt).
Saída: <dir>/artigos/_registros/<ID>.json
  Inclui `pmid` quando o Accession Number da Cochrane traz "PUBMED <n>" (usado por fetch_pubmed.py)
  e `abstract_source` = "cochrane" quando a página exibe abstract.
  Atenção: rodar de novo sobrescreve o registro (inclusive um abstract completado pelo PubMed;
  basta rodar fetch_pubmed.py outra vez).

Exemplo:
  parse_record_page.py --dir levantamento-x artigos/_paginas/*.txt
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NO_ABSTRACT, dump_json, extract_pmid, now, record_url, split_citation, valid_id


def parse(text):
    i = text.find('Related content\n')
    body = text[i + len('Related content\n'):] if i >= 0 else text
    cut = body.find('Cochrane is a global')
    body = body[:cut] if cut > 0 else body
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    k = 0
    for j, l in enumerate(lines):
        if l.startswith('Cochrane Central Register of Controlled Trials') or l.startswith('Cochrane Database of Systematic Reviews'):
            k = j + 1; break
    if k < len(lines) and 'access' in lines[k].lower():
        k += 1
    title = lines[k] if k < len(lines) else ''
    authors = lines[k + 1] if k + 1 < len(lines) else ''
    cit = lines[k + 2] if k + 2 < len(lines) else ''
    if 'added to CENTRAL' in authors:  # registro sem autores: a linha de autores é a citação
        cit, authors = authors, ''
    m = re.search(r'\nAbstract\n(.*?)\n(Information|Keywords)\n', body, re.S)
    ab = m.group(1).strip() if m else None
    if ab and NO_ABSTRACT in ab:
        ab = None
    info = {}
    m2 = re.search(r'\nInformation\n(.*?)\nKeywords\n', body, re.S) or re.search(r'\nInformation\n(.*)$', body, re.S)
    if m2:
        il = [l.strip() for l in m2.group(1).split('\n') if l.strip() and l.strip() != 'Copy DOI']
        j = 0
        while j < len(il):
            if il[j].endswith(':') and j + 1 < len(il) and not il[j + 1].endswith(':'):
                info[il[j][:-1]] = il[j + 1]; j += 2
            else:
                j += 1
    src = re.search(r'Sourced from:\n\s*([^\n]+)', body)
    c = split_citation(cit.split(' | added')[0])
    acc = info.get('Accession Number')
    pmid = extract_pmid(acc) or extract_pmid(re.findall(r'(?:pubmed\.ncbi\.nlm\.nih\.gov|ncbi\.nlm\.nih\.gov/pubmed)/\d+', text))
    return dict(title=title, authors=[a.strip() for a in authors.split(',') if a.strip()],
                citation=cit.split(' | added')[0], **c,
                doi=(info.get('DOI of original publication') or '').replace('https://doi.org/', '') or None,
                accession=acc, pmid=pmid, publication_type=info.get('Publication Type'),
                language=info.get('Language'), sourced_from=src.group(1).strip() if src else None,
                abstract=ab, abstract_source='cochrane' if ab else None, record_id=info.get('ID Number'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dir', required=True)
    ap.add_argument('pages', nargs='+')
    a = ap.parse_args()
    for p in a.pages:
        rid = os.path.basename(p).rsplit('.', 1)[0]
        if not valid_id(rid):
            print(f'AVISO: {os.path.basename(p)} ignorado (nome deve ser o ID Cochrane, ex.: CN-02761934.txt)'); continue
        r = parse(open(p).read())
        r.update(id=rid, url=record_url(rid), section='cochrane_review' if rid.upper().startswith('CD') else 'central_trial',
                 captured_at=now(), origin='pagina_cochrane', source_file=os.path.relpath(p, a.dir))
        if r.get('record_id') and r['record_id'] != rid:
            print(f'AVISO {rid}: página diz ID {r["record_id"]}')
        dump_json(r, os.path.join(a.dir, 'artigos', '_registros', rid + '.json'))
        print(rid, '| abstract' if r['abstract'] else '| SEM ABSTRACT', '| PMID ' + (r['pmid'] or '-'), '|', (r['title'] or '')[:70])
