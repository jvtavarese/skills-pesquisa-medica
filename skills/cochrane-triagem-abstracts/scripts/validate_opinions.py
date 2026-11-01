#!/usr/bin/env python3
"""Valida pareceres e decisões: JSON, campos, valores permitidos e citações literais do abstract.

Exemplos:
  validate_opinions.py --dir levantamento-x --range 1-30 --files parecer_A.json,parecer_B.json
  validate_opinions.py --dir levantamento-x --range 1-30 --files decisao_juiz.json
Imprime só problemas (e um resumo). Código de saída 1 se houver problema.
"""
import argparse, json, os, re

R = ['article_id', 'reader_id', 'decision', 'relevance_class', 'axes_supported', 'objective_mapping', 'abstract_evidence',
     'reason', 'missing_information', 'confidence', 'read_only_packet', 'independence_statement']
J = ['article_id', 'decision', 'relevance_class', 'axes_supported', 'objective_mapping', 'abstract_evidence', 'reason',
     'reader_a_decision', 'reader_b_decision', 'divergences', 'resolution', 'missing_information', 'limitations',
     'confidence', 'source_reread', 'independence_statement']
norm = lambda s: re.sub(r'[\s‐\-–—"“”\'’.…]+', ' ', (s or '').lower()).strip()

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', required=True)
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument('--articles'); g.add_argument('--range')
ap.add_argument('--files', required=True)
a = ap.parse_args()
A = os.path.join(a.dir, 'artigos')
arts = a.articles.split(',') if a.articles else [f'ART-{i:04d}' for i in range(int(a.range.split('-')[0]), int(a.range.split('-')[1]) + 1)]
arts = [x for x in arts if os.path.isdir(os.path.join(A, x))]
bad = 0; tally = {}
for art in arts:
    ab = norm(open(os.path.join(A, art, 'pacote.md')).read().split('## Abstract integral')[-1])
    for f in a.files.split(','):
        p = os.path.join(A, art, f)
        if not os.path.exists(p):
            print(f'{art}/{f}: FALTANDO'); bad += 1; continue
        try:
            d = json.load(open(p))
        except Exception as e:
            print(f'{art}/{f}: JSON INVÁLIDO {e}'); bad += 1; continue
        judge = f.startswith('decisao')
        miss = [k for k in (J if judge else R) if k not in d]
        allowed = ['incluir', 'excluir', 'incerto'] if judge else ['relevante', 'nao_relevante', 'incerto']
        probs = []
        if miss: probs.append(f'campos faltando {miss}')
        if d.get('decision') not in allowed: probs.append(f'decision={d.get("decision")}')
        if d.get('confidence') not in ('alta', 'moderada', 'baixa'): probs.append(f'confidence={d.get("confidence")}')
        if d.get('relevance_class') not in ('direta', 'apoio', 'metodologica', 'nenhuma'): probs.append(f'class={d.get("relevance_class")}')
        if d.get('article_id') != art: probs.append(f'article_id={d.get("article_id")}')
        nonlit = [e.get('quote', '')[:50] for e in d.get('abstract_evidence', []) if norm(e.get('quote')) and norm(e.get('quote')) not in ab]
        if nonlit: probs.append(f'citações não literais {nonlit}')
        if probs:
            print(f'{art}/{f}: ' + '; '.join(probs)); bad += 1
        tally.setdefault(f, {}).setdefault(d.get('decision'), 0)
        tally[f][d.get('decision')] += 1
print('RESUMO', json.dumps(tally, ensure_ascii=False), '| problemas:', bad)
raise SystemExit(1 if bad else 0)
