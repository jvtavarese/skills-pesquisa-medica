#!/usr/bin/env python3
"""Gera o relatório final a partir do diretório de trabalho.

Lê: briefing.json, buscas/historico.jsonl, resultados/triagem_previa.csv, artigos/manifesto_pacotes.json,
    artigos/ART-*/{metadados.json, parecer_A.json, parecer_B.json, decisao_juiz.json, elegibilidade_coordenador.json}
    e, se existir, artigos/ART-*/metadados_crossref.json (de enrich_crossref.py)
Gera: resultados/triagem_abstracts.md, resultados/Levantamento_Cochrane.pdf, resultados/Levantamento_Cochrane.html

Artigo válido = juiz decidiu `incluir` e não há elegibilidade_coordenador.json com eligible=false.

Metadados das referências: a Cochrane vem primeiro. Do Crossref (só quando o registro é confiável) entram
apenas campos vazios na Cochrane: doi, volume, issue, pages, year e autores (se a lista estiver vazia).
Valor da Cochrane nunca é trocado; divergências vão para a seção "Divergências de metadados" do .md.
Requer: reportlab (pip install reportlab).
Exemplo:  build_report.py --dir levantamento-x
"""
import argparse, csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--dir', required=True)
ap.add_argument('--name', default='Levantamento_Cochrane', help='nome base dos arquivos de saída')
a = ap.parse_args()
T = os.path.abspath(a.dir); A = os.path.join(T, 'artigos'); R = os.path.join(T, 'resultados')
os.makedirs(R, exist_ok=True)

B = load_json(os.path.join(T, 'briefing.json'))
if not B:
    sys.exit('briefing.json não encontrado (veja assets/briefing_modelo.md).')
hist = [json.loads(l) for l in open(os.path.join(T, 'buscas', 'historico.jsonl')) if l.strip()]
prev = list(csv.DictReader(open(os.path.join(R, 'triagem_previa.csv'))))
man = load_json(os.path.join(A, 'manifesto_pacotes.json'), {'packets': []})
arts = [p['article_id'] for p in man['packets']]
L = lambda art, f: load_json(os.path.join(A, art, f))
rec2art = {p['record_id']: p['article_id'] for p in man['packets']}

valid, rejected, pending = [], [], []
for art in arts:
    jz, ov = L(art, 'decisao_juiz.json'), L(art, 'elegibilidade_coordenador.json')
    if not jz:
        pending.append(art)
    elif jz['decision'] == 'incluir' and not (ov and ov.get('eligible') is False):
        valid.append(art)
    else:
        rejected.append(art)

AX = B.get('eixos', {})
names = B.get('buscas_nomes', {})
ORDER = {'direta': 0, 'apoio': 1, 'metodologica': 2, 'nenhuma': 3}
TYPE_EXCL = {'registro_ensaio', 'protocolo'}


def counts(h):
    sid = h['search_id']; sc = h.get('section_counts', {})
    total = sc.get('cochrane_review', 0) + sc.get('central_trial', 0)
    rows = [r for r in prev if sid in r['searches'].split(';')]
    reg = sum(r['disposition'] in TYPE_EXCL for r in rows)
    read = sum(r['id'] in rec2art for r in rows)
    used = [rec2art[r['id']] for r in rows if rec2art.get(r['id']) in valid]
    return total, reg, read, used


CR_FILL = ('doi', 'volume', 'issue', 'pages', 'year')


def crossref(art):
    """metadados_crossref.json utilizável (casou e é o mesmo artigo) ou None."""
    c = L(art, 'metadados_crossref.json')
    if not c or not c.get('matched_by'):
        return None
    sim = c.get('title_similarity')
    if c.get('confiavel') is False or (c.get('confiavel') is None and sim is not None and sim < 0.8):
        return None
    return c


def conflicting(c):
    """Divergência em ano/volume/DOI indica edição ou publicação diferente: não completar nada."""
    return any(d.get('field') in ('year', 'volume', 'doi') for d in c.get('discrepancies') or [])


def meta(art):
    """Metadados da Cochrane completados (só campos vazios) pelo Crossref. Não altera os arquivos."""
    m = dict(L(art, 'metadados.json'))
    c = crossref(art)
    m['_crossref'] = bool(c)
    if c and not conflicting(c):
        for f in CR_FILL:
            if m.get(f) in (None, '', []) and c.get(f) not in (None, '', []):
                m[f] = c[f]
                if f == 'issue':  # Crossref às vezes usa "suppl_1"
                    m[f] = re.sub(r'(?i)^suppl(?:ement)?[_ .]*(\w+)$', r'Suppl \1', str(c[f]))
        if not [x for x in m.get('authors') or [] if x] and c.get('authors'):
            m['authors'] = c['authors']
    return m


def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\u2010', '-').replace('\u2011', '-')


def ref(art, link_tag='link'):
    m = meta(art)
    au = [x for x in m.get('authors', []) if x]
    aus = ', '.join(au[:6]) + (', et al' if len(au) > 6 else '')
    title = (m.get('title') or '').rstrip('.')
    if title.isupper():
        title = title.capitalize()
    vol = ''
    if m.get('volume'):
        vol = f";{m['volume']}" + (f"({m['issue']})" if m.get('issue') else '') + (f":{m['pages']}" if m.get('pages') else '')
    s = f"{esc(aus)}. {esc(title)}. <i>{esc(m.get('journal') or m.get('citation') or '')}</i>. {m.get('year') or ''}{esc(vol)}."
    if m.get('doi'):
        s += f" doi:<{link_tag} href='https://doi.org/{m['doi']}'>{esc(m['doi'])}</{'link' if link_tag == 'link' else 'a'}>"
    if 'onference' in (m.get('publication_type') or ''):
        s += ' [Resumo de congresso]'
    return s


def note(art, link_tag='link'):
    m, jz = meta(art), L(art, 'decisao_juiz.json')
    ax = ', '.join(AX.get(x, x) for x in jz.get('axes_supported', []))
    close = 'link' if link_tag == 'link' else 'a'
    return (f"Contribuição: {jz['relevance_class']}{f' ({esc(ax)})' if ax else ''} · objetivos "
            f"{', '.join(jz.get('objective_mapping') or []) or '-'} · confiança {jz['confidence']} · Cochrane "
            f"{m['record_id']} (<{link_tag} href='{m['cochrane_url']}'>abrir registro</{close}>)"
            + (' · metadados conferidos no Crossref' if m['_crossref'] else ''))


final_order = sorted(valid, key=lambda x: (ORDER.get(L(x, 'decisao_juiz.json')['relevance_class'], 9),
                                           L(x, 'decisao_juiz.json').get('axes_supported', []), x))
n_type = sum(r['disposition'] in TYPE_EXCL for r in prev)
obs = B.get('observacoes', []) + [
    f'Lidos e não usados: {len(rejected)} artigos (fora do tema pelo abstract, sem abstract, protocolo ou versão repetida). '
    'Detalhes em resultados/triagem_abstracts.md.']
if pending:
    obs.append(f'Ainda sem decisão do juiz: {len(pending)} artigos.')
direct = sum(L(x, 'decisao_juiz.json')['relevance_class'] == 'direta' for x in valid)
resumo = (f"Base: <b>Cochrane Library</b> (busca avançada, campo <i>Title Abstract Keyword</i>"
          f"{', filtro ' + esc(B['filtro_anos']) if B.get('filtro_anos') else ', sem filtro de data ou idioma'}). "
          "Seleção pelo título e pelo abstract exibido na própria Cochrane, com dois leitores independentes e um juiz. "
          "Registros de ensaio sem artigo publicado, protocolos e versões repetidas do mesmo estudo foram descartados. "
          f"<b>{len(valid)} artigos válidos</b> no total ({direct} com evidência direta para a pergunta central).")

# ------------------------------------------------------------------ Markdown
md = [f"# Triagem por abstract — Cochrane Library\n\n**{B['titulo']}**\n",
      f"Válidos: **{len(valid)}** · lidos e não usados: {len(rejected)} · pendentes: {len(pending)}\n",
      "| Artigo | Título | A | B | Juiz | Classe | Confiança | Coordenador | Motivo do juiz |", "|---|---|---|---|---|---|---|---|---|"]
for art in arts:
    m, pa, pb, jz, ov = (L(art, f) for f in ('metadados.json', 'parecer_A.json', 'parecer_B.json', 'decisao_juiz.json', 'elegibilidade_coordenador.json'))
    cell = lambda d: d['decision'] if d else '—'
    md.append(f"| {art} | {(m['title'] or '')[:80].replace('|', '/')} | {cell(pa)} | {cell(pb)} | {cell(jz)} | "
              f"{jz['relevance_class'] if jz else '—'} | {jz['confidence'] if jz else '—'} | "
              f"{(ov or {}).get('status', '—')} | {(jz or {}).get('reason', '')[:300].replace('|', '/').replace(chr(10), ' ')} |")
md_cell = lambda v: str(v if v not in (None, '') else '—').replace('|', '/').replace('\n', ' ')
div = []
for art in arts:
    c = L(art, 'metadados_crossref.json')
    if not c or not c.get('matched_by'):
        continue
    usado = 'sim' if crossref(art) else 'não (registro do Crossref não parece o mesmo artigo)'
    for d in c.get('discrepancies') or []:
        div.append(f"| {art} | {d.get('field')} | {md_cell(d.get('cochrane'))} | {md_cell(d.get('crossref'))} | {usado} |")
if div:
    md += ['', '## Divergências de metadados (Cochrane × Crossref)', '',
           'O relatório mantém sempre o valor da Cochrane; o Crossref só completa campos vazios. '
           'Confira manualmente as linhas abaixo antes de citar.', '',
           '| Artigo | Campo | Cochrane | Crossref | Crossref usado para completar? |', '|---|---|---|---|---|'] + div
open(os.path.join(R, 'triagem_abstracts.md'), 'w').write('\n'.join(md) + '\n')

# ------------------------------------------------------------------ PDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, HRFlowable, KeepTogether, PageTemplate, Paragraph, Spacer, Table, TableStyle

FONT_DIRS = ['/System/Library/Fonts/Supplemental/', '/usr/share/fonts/truetype/dejavu/', 'C:/Windows/Fonts/']
CANDIDATES = {'Body': ['Georgia.ttf', 'DejaVuSerif.ttf', 'georgia.ttf'], 'Body-B': ['Georgia Bold.ttf', 'DejaVuSerif-Bold.ttf', 'georgiab.ttf'],
              'Body-I': ['Georgia Italic.ttf', 'DejaVuSerif-Italic.ttf', 'georgiai.ttf'], 'Sans': ['Arial.ttf', 'DejaVuSans.ttf', 'arial.ttf'],
              'Sans-B': ['Arial Bold.ttf', 'DejaVuSans-Bold.ttf', 'arialbd.ttf']}
FALLBACK = {'Body': 'Times-Roman', 'Body-B': 'Times-Bold', 'Body-I': 'Times-Italic', 'Sans': 'Helvetica', 'Sans-B': 'Helvetica-Bold'}
FN = {}
for key, files in CANDIDATES.items():
    path = next((d + f for d in FONT_DIRS for f in files if os.path.exists(d + f)), None)
    if path:
        pdfmetrics.registerFont(TTFont(key, path)); FN[key] = key
    else:
        FN[key] = FALLBACK[key]
if FN['Body'] == 'Body':
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily('Body', normal='Body', bold=FN['Body-B'], italic=FN['Body-I'], boldItalic=FN['Body-B'])

INK, ACCENT, MUTED = colors.HexColor('#1f2a37'), colors.HexColor('#1d5c63'), colors.HexColor('#5b6675')
SOFT, RULE, CODEBG = colors.HexColor('#eef4f4'), colors.HexColor('#c9d6d8'), colors.HexColor('#f6f7f9')
st = {
    'title': ParagraphStyle('t', fontName=FN['Body-B'], fontSize=17, leading=22, textColor=INK, spaceAfter=4),
    'kicker': ParagraphStyle('k', fontName=FN['Sans-B'], fontSize=8.5, leading=11, textColor=ACCENT, spaceAfter=6),
    'h1': ParagraphStyle('h1', fontName=FN['Sans-B'], fontSize=11, leading=14, textColor=ACCENT, spaceBefore=12, spaceAfter=5),
    'body': ParagraphStyle('b', fontName=FN['Body'], fontSize=10, leading=14.5, textColor=INK, spaceAfter=4),
    'li': ParagraphStyle('li', fontName=FN['Body'], fontSize=10, leading=14.5, textColor=INK, leftIndent=14, bulletIndent=2, spaceAfter=3),
    'query': ParagraphStyle('q', fontName=FN['Sans'], fontSize=8.6, leading=12, textColor=INK, backColor=CODEBG,
                            borderPadding=(6, 7, 6, 7), borderColor=RULE, borderWidth=0.5, spaceBefore=4, spaceAfter=8),
    'count': ParagraphStyle('c', fontName=FN['Sans'], fontSize=9, leading=12, textColor=MUTED, spaceAfter=6),
    'ref': ParagraphStyle('r', fontName=FN['Body'], fontSize=9.6, leading=13.6, textColor=INK, leftIndent=22, firstLineIndent=-22, spaceAfter=2),
    'note': ParagraphStyle('n', fontName=FN['Sans'], fontSize=8.2, leading=11, textColor=MUTED, leftIndent=22, spaceAfter=8),
    'cell': ParagraphStyle('cell', fontName=FN['Sans'], fontSize=8.4, leading=10.5, textColor=INK),
    'cellb': ParagraphStyle('cellb', fontName=FN['Sans-B'], fontSize=8.4, leading=10.5, textColor=colors.white),
    'small': ParagraphStyle('s', fontName=FN['Sans'], fontSize=8, leading=10.5, textColor=MUTED),
}
LINKC = "<link href='{h}' color='#1d5c63'>{t}</link>"


def pdf_link(s):  # cor nos links do PDF
    return s.replace("<link href=", "<link color='#1d5c63' href=")


def deco(c, d):
    c.saveState(); c.setStrokeColor(ACCENT); c.setLineWidth(2)
    c.line(18 * mm, A4[1] - 12 * mm, A4[0] - 18 * mm, A4[1] - 12 * mm)
    c.setFont(FN['Sans'], 7.5); c.setFillColor(MUTED)
    c.drawString(18 * mm, 10 * mm, 'Levantamento bibliográfico · Cochrane Library')
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(d.page)); c.restoreState()


pdf_path = os.path.join(R, a.name + '.pdf')
doc = BaseDocTemplate(pdf_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=17 * mm,
                      title='Levantamento Cochrane', author='cochrane-triagem-abstracts')
doc.addPageTemplates([PageTemplate(frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='f')], onPage=deco)])
E = [Paragraph('LEVANTAMENTO BIBLIOGRÁFICO · COCHRANE LIBRARY', st['kicker']),
     Paragraph('<b>TÍTULO:</b>', st['h1']), Paragraph(esc(B['titulo']), st['title']),
     Paragraph('<b>OBJETIVO GERAL:</b>', st['h1']), Paragraph(B['objetivo_geral'], st['body']),
     Paragraph('<b>OBJETIVOS ESPECÍFICOS:</b>', st['h1'])]
for i, t in enumerate(B.get('objetivos_especificos', []), 1):
    E.append(Paragraph(t, st['li'], bulletText=f'{i}.'))
E += [Spacer(1, 6), HRFlowable(width='100%', thickness=0.8, color=RULE, spaceBefore=4, spaceAfter=4),
      Paragraph('<b>RESUMO DA BUSCA</b>', st['h1']), Paragraph(resumo, st['body'])]
rows = [[Paragraph(x, st['cellb']) for x in ['Busca', 'Vieram', 'Registros / protocolos', 'Lidos (abstract)', 'Usados']]]
for h in hist:
    t, r, c, u = counts(h)
    rows.append([Paragraph(esc(names.get(h['search_id'], f"{h['search_id']} · {h['family']}")), st['cell'])] +
                [Paragraph(str(x), st['cell']) for x in (t, r, c, len(u))])
rows.append([Paragraph(f'<b>{x}</b>', st['cell']) for x in ('Total (sem repetições)', len(prev), n_type, len(arts), len(valid))])
tb = Table(rows, colWidths=[78 * mm, 18 * mm, 30 * mm, 26 * mm, 20 * mm], repeatRows=1)
tb.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), ACCENT), ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, SOFT]),
                        ('LINEABOVE', (0, -1), (-1, -1), 0.8, ACCENT), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
E += [tb, Paragraph('“Vieram” = resultados exibidos pela Cochrane. “Lidos” = artigos publicados, sem duplicatas, enviados à '
                    'leitura do abstract. Um artigo pode aparecer em mais de uma busca; o total desconta repetições.', st['small']),
      HRFlowable(width='100%', thickness=0.8, color=RULE, spaceBefore=8, spaceAfter=0)]
num, seen = 0, {}
for h in hist:
    t, r, c, used = counts(h)
    E.append(KeepTogether([Paragraph(f"<b>{esc(names.get(h['search_id'], h['search_id'] + ' · ' + h['family']))}</b>", st['h1']),
                           Paragraph(esc(h['query']), st['query']),
                           Paragraph(f'total: <b>{t}</b> ; registros/protocolos: {r} ; lidos: {c} ; <b>usados: {len(used)}</b>', st['count'])]))
    if not used:
        E.append(Paragraph(esc(h.get('note')) if (t and h.get('note')) else
                           ('Nenhum artigo utilizado nesta busca.' if t else 'A busca não retornou resultados.'), st['note']))
    for art in used:
        num += 1
        rep = f' (também na referência {seen[art]})' if art in seen else ''
        seen.setdefault(art, num)
        E.append(KeepTogether([Paragraph(f'{num}.&nbsp;&nbsp;{pdf_link(ref(art))}', st['ref']),
                               Paragraph(pdf_link(note(art)) + esc(rep), st['note'])]))
E += [HRFlowable(width='100%', thickness=0.8, color=RULE, spaceBefore=8, spaceAfter=0),
      Paragraph(f'<b>LISTA FINAL — {len(valid)} ARTIGOS VÁLIDOS (sem repetição)</b>', st['h1'])]
for i, art in enumerate(final_order, 1):
    E.append(KeepTogether([Paragraph(f'{i}.&nbsp;&nbsp;{pdf_link(ref(art))}', st['ref']), Paragraph(pdf_link(note(art)), st['note'])]))
E.append(Paragraph('<b>OBSERVAÇÕES</b>', st['h1']))
for t in obs:
    E.append(Paragraph(t, st['li'], bulletText='•'))
doc.build(E)

# ------------------------------------------------------------------ HTML (para Google Docs)
C = '#1d5c63'
H = f'font-family:Arial;color:{C};font-size:12pt;font-weight:bold;'
NOTE = 'font-size:8.5pt;color:#5b6675;margin-left:24pt;'
REF = 'margin-left:24pt;text-indent:-24pt;'
th = f'background-color:{C};color:#ffffff;font-family:Arial;font-size:9pt;font-weight:bold;padding:4pt;'
td = 'font-family:Arial;font-size:9pt;padding:4pt;border-bottom:1px solid #c9d6d8;'
o = ['<html><head><meta charset="utf-8"></head><body>',
     f'<p style="font-family:Arial;font-size:9pt;font-weight:bold;color:{C};">LEVANTAMENTO BIBLIOGRÁFICO · COCHRANE LIBRARY</p>',
     f'<h2 style="{H}">TÍTULO:</h2>', f'<h1 style="font-family:Georgia;font-size:18pt;color:#1f2a37;">{esc(B["titulo"])}</h1>',
     f'<h2 style="{H}">OBJETIVO GERAL:</h2>', f'<p>{B["objetivo_geral"]}</p>', f'<h2 style="{H}">OBJETIVOS ESPECÍFICOS:</h2>',
     '<ol>' + ''.join(f'<li>{t}</li>' for t in B.get('objetivos_especificos', [])) + '</ol>', '<hr>',
     f'<h2 style="{H}">RESUMO DA BUSCA</h2>', f'<p>{resumo}</p>',
     '<table style="border-collapse:collapse;width:100%;"><tr>' + ''.join(f'<th style="{th}">{x}</th>' for x in ['Busca', 'Vieram', 'Registros / protocolos', 'Lidos (abstract)', 'Usados']) + '</tr>']
for i, h in enumerate(hist):
    t, r, c, u = counts(h); bg = 'background-color:#eef4f4;' if i % 2 else ''
    o.append('<tr>' + ''.join(f'<td style="{td}{bg}">{x}</td>' for x in (esc(names.get(h['search_id'], h['search_id'] + ' · ' + h['family'])), t, r, c, len(u))) + '</tr>')
o.append('<tr>' + ''.join(f'<td style="{td}"><b>{x}</b></td>' for x in ('Total (sem repetições)', len(prev), n_type, len(arts), len(valid))) + '</tr></table>')
o += ['<hr>']
num, seen = 0, {}
for h in hist:
    t, r, c, used = counts(h)
    o += [f'<h2 style="{H}">{esc(names.get(h["search_id"], h["search_id"] + " · " + h["family"]))}</h2>',
          f'<p style="font-family:Arial;font-size:9pt;background-color:#f6f7f9;"><b>{esc(h["query"])}</b></p>',
          f'<p style="font-family:Arial;font-size:9.5pt;color:#5b6675;">total: <b>{t}</b> ; registros/protocolos: {r} ; lidos: {c} ; <b>usados: {len(used)}</b></p>']
    if not used:
        o.append(f'<p style="{NOTE}">' + (esc(h.get('note')) if (t and h.get('note')) else ('Nenhum artigo utilizado nesta busca.' if t else 'A busca não retornou resultados.')) + '</p>')
    for art in used:
        num += 1
        rep = f' (também na referência {seen[art]})' if art in seen else ''
        seen.setdefault(art, num)
        o += [f'<p style="{REF}">{num}.&nbsp;&nbsp;{ref(art, "a")}</p>', f'<p style="{NOTE}">{note(art, "a")}{esc(rep)}</p>']
o += ['<hr>', f'<h2 style="{H}">LISTA FINAL — {len(valid)} ARTIGOS VÁLIDOS (sem repetição)</h2>']
for i, art in enumerate(final_order, 1):
    o += [f'<p style="{REF}">{i}.&nbsp;&nbsp;{ref(art, "a")}</p>', f'<p style="{NOTE}">{note(art, "a")}</p>']
o += [f'<h2 style="{H}">OBSERVAÇÕES</h2>', '<ul>' + ''.join(f'<li>{t}</li>' for t in obs) + '</ul>', '</body></html>']
open(os.path.join(R, a.name + '.html'), 'w').write('\n'.join(o))
print(f'válidos={len(valid)} rejeitados={len(rejected)} pendentes={len(pending)}')
print(pdf_path); print(os.path.join(R, a.name + '.html')); print(os.path.join(R, 'triagem_abstracts.md'))
