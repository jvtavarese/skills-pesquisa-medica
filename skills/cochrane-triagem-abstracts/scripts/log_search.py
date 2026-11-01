#!/usr/bin/env python3
"""Acrescenta uma busca a buscas/historico.jsonl (nunca sobrescreve entradas anteriores).

Exemplo:
  log_search.py --dir levantamento-x --search-id S-0003 --family Q3 --query-file q3.txt \
      --reviews 0 --protocols 0 --trials 44 --url "https://www.cochranelibrary.com/advanced-search" \
      --note "P AND C AND O"
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import now

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', required=True, help='diretório de trabalho')
ap.add_argument('--search-id', required=True, help='S-NNNN')
ap.add_argument('--family', required=True, help='Q1, Q2, Q5b ...')
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument('--query'); g.add_argument('--query-file')
ap.add_argument('--field', default='Title Abstract Keyword')
ap.add_argument('--filters', default='none')
ap.add_argument('--reviews', type=int, default=0)
ap.add_argument('--protocols', type=int, default=0)
ap.add_argument('--trials', type=int, default=0)
ap.add_argument('--editorials', type=int, default=0)
ap.add_argument('--url', default='https://www.cochranelibrary.com/advanced-search')
ap.add_argument('--export-file', default=None, help='buscas/S-NNNN.json ou arquivo exportado')
ap.add_argument('--mode', choices=['navegador', 'manual'], default='navegador')
ap.add_argument('--note', default='')
a = ap.parse_args()

q = a.query if a.query else open(a.query_file).read().strip()
path = os.path.join(a.dir, 'buscas', 'historico.jsonl')
os.makedirs(os.path.dirname(path), exist_ok=True)
if os.path.exists(path):
    for line in open(path):
        if line.strip() and json.loads(line)['search_id'] == a.search_id:
            sys.exit(f'{a.search_id} já existe em {path}; use um novo ID (reformulação = nova busca).')
entry = dict(search_id=a.search_id, family=a.family, query=q, field=a.field, filters=a.filters,
             section_counts=dict(cochrane_review=a.reviews, cochrane_protocol=a.protocols,
                                 central_trial=a.trials, editorial=a.editorials),
             executed_at=now(), url=a.url, export_file=a.export_file, mode=a.mode, note=a.note)
with open(path, 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
print('ok', a.search_id, entry['section_counts'])
