#!/usr/bin/env python3
"""Cria pacotes imutáveis artigos/ART-NNNN/ para cada linha `candidato` de triagem_previa.csv.

Cada pacote: pacote.md (metadados + abstract integral exibido) e metadados.json, somente leitura,
com sha256 em artigos/manifesto_pacotes.json. IDs ART já atribuídos são preservados entre execuções;
pacotes existentes nunca são reescritos.

Requer artigos/_registros/<ID>.json (de parse_record_page.py ou parse_export.py).
Exemplo:  build_packets.py --dir levantamento-x
"""
import argparse, csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump_json, load_json, sha256

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', required=True)
a = ap.parse_args()
A = os.path.join(a.dir, 'artigos')
man_path = os.path.join(A, 'manifesto_pacotes.json')
man = load_json(man_path, {'packets': []})
by_rec = {p['record_id']: p for p in man['packets']}
n = max([int(p['article_id'][4:]) for p in man['packets']] or [0])
rows = list(csv.DictReader(open(os.path.join(a.dir, 'resultados', 'triagem_previa.csv'))))
missing, created = [], 0
for r in rows:
    if r['disposition'] != 'candidato' or r['id'] in by_rec:
        continue
    reg = load_json(os.path.join(A, '_registros', r['id'] + '.json'))
    if not reg:
        missing.append(r['id']); continue
    n += 1; aid = f'ART-{n:04d}'; d = os.path.join(A, aid)
    os.makedirs(d, exist_ok=True)
    label = ('Revisão Cochrane' if reg.get('section') == 'cochrane_review'
             else 'Artigo indexado no CENTRAL (Cochrane Central Register of Controlled Trials) — não é revisão Cochrane')
    meta = dict(article_id=aid, record_id=r['id'], title=reg.get('title'), authors=reg.get('authors', []),
                citation=reg.get('citation'), journal=reg.get('journal'), year=reg.get('year'), volume=reg.get('volume'),
                issue=reg.get('issue'), pages=reg.get('pages'), doi=reg.get('doi'), accession=reg.get('accession'),
                publication_type=reg.get('publication_type'), language=reg.get('language'),
                sourced_from=reg.get('sourced_from'), cochrane_url=reg.get('url'), cochrane_section=reg.get('section'),
                item_label=label, search_ids=r['searches'].split(';'), retrieved_at=reg.get('captured_at'),
                capture_origin=reg.get('origin'), access_level='resumo' if reg.get('abstract') else 'registro',
                abstract_available=bool(reg.get('abstract')))
    ab = reg.get('abstract') or 'ESTE REGISTRO NÃO EXIBE ABSTRACT NA COCHRANE ("This CENTRAL record does not have an abstract.")'
    md = f"""# Pacote de leitura {aid}

> Pacote imutável. Fonte única: Cochrane Library. Avaliação somente pelo abstract abaixo.

| Campo | Valor |
|---|---|
| ID do pacote | {aid} |
| ID Cochrane | {r['id']} |
| Tipo | {label} |
| Tipo de publicação (Cochrane) | {meta['publication_type']} |
| Título | {meta['title']} |
| Autores | {', '.join(meta['authors'])} |
| Referência | {meta['citation']} |
| DOI (informado pela Cochrane) | {meta['doi']} |
| Idioma | {meta['language']} |
| Origem do registro | {meta['sourced_from']} |
| URL Cochrane | {meta['cochrane_url']} |
| Buscas de origem | {', '.join(meta['search_ids'])} |
| Capturado em | {meta['retrieved_at']} |

## Abstract integral exibido na Cochrane

{ab}
"""
    open(os.path.join(d, 'pacote.md'), 'w').write(md)
    dump_json(meta, os.path.join(d, 'metadados.json'))
    for f in ('pacote.md', 'metadados.json'):
        os.chmod(os.path.join(d, f), 0o444)
    man['packets'].append(dict(article_id=aid, record_id=r['id'], title=meta['title'], abstract=bool(reg.get('abstract')),
                               sha256={'pacote.md': sha256(os.path.join(d, 'pacote.md'))}))
    created += 1
dump_json(man, man_path)
print(f'{created} pacotes novos; total {len(man["packets"])} -> {man_path}')
if missing:
    print('SEM REGISTRO (capture a página ou a exportação):', ', '.join(missing))
