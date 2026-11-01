#!/usr/bin/env python3
"""Junta todas as buscas (buscas/S-*.json), remove repetidos e faz a pré-triagem automática por tipo.

Saída: <dir>/resultados/triagem_previa.csv com uma linha por registro único:
  id, searches, section, source, title, citation, disposition, reason

disposition automática:
  registro_ensaio   registro ICTRP/ClinicalTrials.gov sem artigo publicado
  protocolo         protocolo (seção de protocolos ou título/abstract de protocolo)
  sem_abstract      registro cujo abstract já se sabe ausente
  candidato         segue para leitura (padrão)

Depois de rodar, edite o CSV: troque `candidato` por `excluido_titulo` (fora dos objetivos, com motivo)
ou `versao_sobreposta` (motivo: "mesmo estudo de <ID>"). Rodar de novo PRESERVA essas edições manuais.
"""
import argparse, csv, glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import is_protocol, is_registry, load_json, norm_title

AUTO = {'registro_ensaio', 'protocolo', 'sem_abstract', 'candidato', 'duplicata'}
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', required=True)
a = ap.parse_args()

out_path = os.path.join(a.dir, 'resultados', 'triagem_previa.csv')
manual = {}
if os.path.exists(out_path):
    for r in csv.DictReader(open(out_path)):
        if r['disposition'] not in AUTO:
            manual[r['id']] = (r['disposition'], r['reason'])

recs, order = {}, []
for p in sorted(glob.glob(os.path.join(a.dir, 'buscas', 'S-*.json'))):
    s = json.load(open(p))
    sid = s.get('search_id') or os.path.basename(p)[:-5]
    for it in s.get('items', []):
        rid = it['id']
        if rid not in recs:
            recs[rid] = dict(it, searches=[]); order.append(rid)
        if sid not in recs[rid]['searches']:
            recs[rid]['searches'].append(sid)

rows, by_title = [], {}
for rid in order:
    it = recs[rid]
    reg = load_json(os.path.join(a.dir, 'artigos', '_registros', rid + '.json'), {}) or {}
    probe = dict(it, **{k: v for k, v in reg.items() if v})
    nt = norm_title(it.get('title'))
    if rid in manual:
        disp, reason = manual[rid]
    elif nt and nt in by_title:
        disp, reason = 'duplicata', f'mesmo título de {by_title[nt]}'
    elif is_registry(probe):
        disp, reason = 'registro_ensaio', 'registro de ensaio (ICTRP/CT.gov) sem artigo publicado'
    elif is_protocol(probe):
        disp, reason = 'protocolo', 'protocolo sem resultados'
    elif reg and not reg.get('abstract'):
        disp, reason = 'sem_abstract', 'a página/exportação Cochrane não exibe abstract'
    else:
        disp, reason = 'candidato', ''
    by_title.setdefault(nt, rid)
    rows.append(dict(id=rid, searches=';'.join(it['searches']), section=it.get('section', ''),
                     source=it.get('src', ''), title=it.get('title', ''), citation=(it.get('meta') or '').split(' | added')[0],
                     disposition=disp, reason=reason))

os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['id'])
    w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows), 'registros únicos ->', out_path)
print(dict(Counter(r['disposition'] for r in rows)))
