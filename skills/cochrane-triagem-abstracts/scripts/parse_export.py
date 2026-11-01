#!/usr/bin/env python3
"""Converte exportações da Cochrane (Plain text ou RIS, com abstract) em busca + registros.

Saídas:
  <dir>/buscas/<search-id>.json        lista de itens da busca (para prescreen.py)
  <dir>/artigos/_registros/<ID>.json   um registro por artigo (para build_packets.py)

Exemplo:
  parse_export.py --dir levantamento-x --search-id S-0003 --family Q3 \
      --section central_trial export_trials.txt
Se o formato não for reconhecido, o script avisa; leia o arquivo e monte o JSON manualmente,
sem inventar campos ausentes.
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NO_ABSTRACT, dump_json, now, record_url

PLAIN_MULTI = {'AU', 'KY', 'PT', 'XR'}


def parse_plain(text):
    recs = []
    for block in re.split(r'\n?Record #\d+ of \d+\s*\n', '\n' + text):
        if not block.strip():
            continue
        fields, last = {}, None
        for line in block.split('\n'):
            m = re.match(r'^([A-Z][A-Z0-9]{1,3}):\s?(.*)$', line)
            if m:
                last = m.group(1); fields.setdefault(last, []).append(m.group(2).strip())
            elif last and line.strip():
                fields[last][-1] += ' ' + line.strip()
        if 'ID' in fields or 'TI' in fields:
            recs.append(fields)
    out = []
    for f in recs:
        g = lambda k: f[k][0] if k in f and f[k] else None
        rid = g('ID') or ''
        ab = g('AB')
        out.append(dict(id=rid, title=g('TI'), authors=f.get('AU', []), journal=g('SO'),
                        year=int(g('YR')) if (g('YR') or '').isdigit() else None, volume=g('VL'), issue=g('NO'),
                        pages=g('PG'), doi=(g('DOI') or '').replace('https://doi.org/', '') or None,
                        accession=g('PM') or g('EM') or g('AN'), publication_type='; '.join(f.get('PT', [])) or None,
                        language=g('LA'), sourced_from=', '.join(f.get('XR', [])) or None,
                        abstract=None if not ab or NO_ABSTRACT in ab else ab, url=g('US') or (record_url(rid) if rid else None)))
    return out


def parse_ris(text):
    out = []
    for block in re.split(r'\nER\s+-.*', text):
        f, last = {}, None
        for line in block.split('\n'):
            m = re.match(r'^([A-Z][A-Z0-9])\s{1,2}-\s?(.*)$', line)
            if m:
                last = m.group(1); f.setdefault(last, []).append(m.group(2).strip())
            elif last and line.strip():
                f[last][-1] += ' ' + line.strip()
        if not f:
            continue
        g = lambda *ks: next((f[k][0] for k in ks if k in f and f[k]), None)
        url = g('UR', 'L2')
        rid = g('ID', 'AN') or ''
        if not re.match(r'^(CN-\d+|CD\d+)', rid):
            m = re.search(r'(CN-\d+|CD\d+(?:\.PUB\d+)?)', ' '.join([url or ''] + f.get('ID', []) + f.get('AN', [])), re.I)
            rid = m.group(1).upper() if m else rid
        sp, ep = g('SP'), g('EP')
        yr = g('PY', 'Y1')
        ab = g('AB', 'N2')
        out.append(dict(id=rid or '', title=g('TI', 'T1'), authors=f.get('AU', []) + f.get('A1', []), journal=g('JO', 'T2', 'JF'),
                        year=int(yr[:4]) if yr and yr[:4].isdigit() else None, volume=g('VL'), issue=g('IS'),
                        pages=f'{sp}-{ep}' if sp and ep else sp, doi=g('DO'), accession=g('AN'),
                        publication_type=g('M3', 'TY'), language=g('LA'), sourced_from=g('DB'),
                        abstract=None if not ab or NO_ABSTRACT in ab else ab, url=url or (record_url(rid) if rid else None)))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dir', required=True)
    ap.add_argument('--search-id', required=True)
    ap.add_argument('--family', default='')
    ap.add_argument('--section', choices=['central_trial', 'cochrane_review'], default='central_trial')
    ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    recs = []
    for p in a.files:
        t = open(p, encoding='utf-8', errors='replace').read()
        r = parse_ris(t) if re.search(r'^TY\s{1,2}-', t, re.M) else parse_plain(t)
        if not r:
            sys.exit(f'Formato não reconhecido em {p}. Leia o arquivo e monte os registros manualmente.')
        recs += r
    items = []
    for r in recs:
        if not r['id']:
            print('AVISO: registro sem ID:', (r['title'] or '')[:60]); continue
        cit = ', '.join(str(x) for x in [r['journal'], r['year']] if x)
        if r['volume']:
            cit += f", {r['volume']}" + (f"({r['issue']})" if r['issue'] else '')
        if r['pages']:
            cit += f", {r['pages']}"
        r.update(citation=cit, section=a.section, captured_at=now(), origin='exportacao_cochrane')
        dump_json(r, os.path.join(a.dir, 'artigos', '_registros', r['id'] + '.json'))
        items.append(dict(id=r['id'], title=r['title'], href=r['url'], meta=cit, src=r['sourced_from'] or '',
                          section=a.section, has_abstract=bool(r['abstract'])))
    path = os.path.join(a.dir, 'buscas', a.search_id + '.json')
    prev = __import__('json').load(open(path)) if os.path.exists(path) else dict(search_id=a.search_id, family=a.family, items=[])
    seen = {i['id'] for i in prev['items']}
    prev['items'] += [i for i in items if i['id'] not in seen]
    dump_json(prev, path)
    print(f'{len(items)} registros ({sum(i["has_abstract"] for i in items)} com abstract) -> {path}')
