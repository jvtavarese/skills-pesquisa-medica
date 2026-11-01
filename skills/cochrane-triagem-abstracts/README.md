# cochrane-triagem-abstracts

Skill de levantamento bibliográfico na **Cochrane Library** com triagem por abstract: dois leitores
independentes, um juiz e um relatório em PDF e HTML (para virar Google Docs), no formato
"busca → quantos vieram → quantos usei → referências".

Use **só no Claude Code** ou **só no Codex (ChatGPT)**. Não misture os dois no mesmo levantamento.

## Instalação

| Ferramenta | Onde colocar a pasta `cochrane-triagem-abstracts/` |
|---|---|
| Claude Code | `~/.claude/skills/` (todos os projetos) ou `<projeto>/.claude/skills/` |
| Codex | `~/.codex/skills/` (ou `~/.agents/skills/`) |

Requisito: Python 3 com `reportlab` (`pip install reportlab`).

## O que você precisa mandar (input)

O mínimo é o **briefing do projeto**:

```
TÍTULO:
<título do projeto>

OBJETIVO GERAL:
<um parágrafo>

OBJETIVOS ESPECÍFICOS:
1. ...
2. ...

META: <número de artigos, ou "todos os válidos">     (opcional; padrão: todos)
ANOS: <ex.: 2021–2026>                              (opcional; padrão: sem filtro)
BUSCAS JÁ FEITAS: <strings booleanas>               (opcional; a skill propõe)
```

Pode ser colado na conversa, em arquivo ou como link do Google Docs.

**Exemplo de pedido:**
> Usa a skill cochrane-triagem-abstracts com o briefing abaixo. Quero todos os artigos válidos, sem filtro
> de anos, e no final o PDF e o HTML para o Google Docs.
> [briefing]

### Navegador ou exportação manual
- Se o navegador da ferramenta estiver disponível (Claude in Chrome ou o navegador embutido no Claude;
  o navegador ou a extensão do Codex), a skill pesquisa sozinha.
- Se não estiver, ela vai pedir que você rode cada string em https://www.cochranelibrary.com/advanced-search
  e exporte o resultado: **Select all → Export selected citation(s) → Plain text → Include abstract →
  Download**. Depois é só mandar os arquivos dizendo a qual busca cada um pertence.

## O que você recebe

```
levantamento-<tema>/
├── briefing.json
├── CRITERIOS_LEITURA.md          critérios congelados (iguais para leitores e juiz)
├── buscas/historico.jsonl        cada busca: string, contagens, data, URL
├── artigos/ART-NNNN/             pacote.md (abstract), parecer_A/B.json, decisao_juiz.json
└── resultados/
    ├── Levantamento_Cochrane.pdf
    ├── Levantamento_Cochrane.html    → para subir no Google Drive como Google Docs
    ├── triagem_abstracts.md          decisões A/B/juiz com motivos
    └── triagem_previa.csv            todos os registros e o destino de cada um
```

Para virar Google Docs: no Drive, ative ⚙️ Configurações → "Converter uploads", depois Novo → Upload
de arquivo → o `.html`.

## Regras que a skill segue
- Só usa a Cochrane e só o abstract exibido nela. Não usa texto completo nem outras bases.
- Não contam: registros de ensaio sem artigo publicado, protocolos, duplicatas e versões repetidas do mesmo estudo.
- Os leitores A e B trabalham em contextos separados. O juiz relê o abstract e decide; não faz votação.
- Se faltarem artigos para a meta, entrega os que encontrou e explica por quê.
