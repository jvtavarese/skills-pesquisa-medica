#!/usr/bin/env python3
"""Gera o prompt de um leitor (A ou B) ou do juiz (J) para um lote de artigos.

O mesmo texto serve para subagente do Claude Code, `claude -p`, `codex exec` ou worker do Orca.
Exemplos:
  make_prompts.py --dir levantamento-x --role A --articles ART-0001,ART-0002 > prompt_A.txt
  make_prompts.py --dir levantamento-x --role J --range 1-30 > prompt_J.txt
"""
import argparse, os

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', required=True)
ap.add_argument('--role', required=True, choices=['A', 'B', 'J'])
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument('--articles', help='lista separada por vírgula')
g.add_argument('--range', help='ex.: 1-30 (números ART)')
a = ap.parse_args()
T = os.path.abspath(a.dir)
arts = a.articles.split(',') if a.articles else [f'ART-{i:04d}' for i in range(int(a.range.split('-')[0]), int(a.range.split('-')[1]) + 1)]
arts = [x for x in arts if os.path.isdir(os.path.join(T, 'artigos', x))]
C = f'{T}/CRITERIOS_LEITURA.md'
check = 'python3 -c "import json,sys;json.load(open(sys.argv[1]))" <arquivo>'
if a.role in 'AB':
    lst = '\n'.join(f'- {x}: ler {T}/artigos/{x}/pacote.md -> escrever {T}/artigos/{x}/parecer_{a.role}.json' for x in arts)
    print(f"""LEITOR {a.role} — triagem independente por abstract.
ALVO: os pacotes abaixo.
{lst}
TAREFA: para cada pacote, escrever UM arquivo parecer_{a.role}.json no formato "Saída do LEITOR" de {C} (reader_id="{a.role}").
RESTRIÇÕES: leia SOMENTE {C} e os pacote.md listados. Proibido abrir parecer_A/parecer_B/decisao_juiz de qualquer artigo, outros arquivos, internet, navegador, URLs, texto completo, memória sobre os estudos, inferir dados ausentes ou usar subagentes. Citações em abstract_evidence devem ser trechos LITERAIS do abstract. Sem abstract ou abstract insuficiente => "incerto".
PERMISSÃO DE ESCRITA: apenas os parecer_{a.role}.json listados.
CONCLUSÃO VERIFICÁVEL: cada arquivo existe, é JSON válido ({check}) e tem todos os campos. Termine com um resumo de uma linha por artigo (ID: decisão/classe/confiança).""")
else:
    lst = '\n'.join(f'- {x}: ler {T}/artigos/{x}/pacote.md, parecer_A.json e parecer_B.json -> escrever {T}/artigos/{x}/decisao_juiz.json' for x in arts)
    print(f"""JUIZ — decisão fundamentada por abstract.
ALVO: os artigos abaixo.
{lst}
TAREFA: para cada artigo, RELER o abstract do pacote.md, examinar os dois pareceres e escrever decisao_juiz.json no formato "Saída do JUIZ" de {C}. Decida pela evidência do abstract, não por votação: mesmo com A e B concordes, inclua só se o abstract sustentar claramente um eixo; com divergência, explique qual leitura o abstract sustenta. Sinalize em eligibility_flags se o item parecer protocolo, registro sem resultados ou versão do mesmo estudo de outro artigo do lote.
RESTRIÇÕES: use somente {C}, o pacote.md e os dois pareceres de cada artigo. Proibido internet, navegador, URLs, texto completo, outros arquivos, memória sobre os estudos, inferir dados ausentes, subagentes. Não altere pareceres. Citações literais. "incerto" quando o abstract for insuficiente.
PERMISSÃO DE ESCRITA: apenas os decisao_juiz.json listados.
CONCLUSÃO VERIFICÁVEL: cada arquivo existe, é JSON válido ({check}), tem todos os campos e source_reread=true. Termine com um resumo de uma linha por artigo e liste os eligibility_flags.""")
