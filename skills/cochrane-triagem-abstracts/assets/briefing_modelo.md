# Modelo de briefing (o que mandar para a skill)

Copie, preencha e cole na conversa (ou mande o link do Google Docs com esse conteúdo):

```
TÍTULO:
<título do projeto>

OBJETIVO GERAL:
<um parágrafo>

OBJETIVOS ESPECÍFICOS:
1. ...
2. ...

META: <número de artigos, ou "todos os válidos">          (opcional)
ANOS: <ex.: 2021–2026, ou "sem filtro">                   (opcional)
BUSCAS JÁ FEITAS: <strings booleanas, se tiver>          (opcional)
```

Exemplo de pedido completo:
> "Usa a skill cochrane-triagem-abstracts com este briefing. Quero todos os artigos válidos, sem filtro de
> anos, e no final o PDF e o HTML para o Google Docs."

# Formato interno: `briefing.json`

```json
{
  "titulo": "Impacto da Complexidade Farmacoterapêutica ...",
  "objetivo_geral": "Avaliar a relação entre ...",
  "objetivos_especificos": ["<b>Mapear a farmacoterapia</b> ...", "..."],
  "codigos_objetivos": {"OG": "relação central", "OE1": "...", "OE2": "...", "OE3": "...", "OE4": "..."},
  "eixos": {"a": "complexidade/MRCI em DRC", "b": "farmacoterapia/polifarmácia em DRC",
            "c": "sobrecarga do cuidador em DRC", "d": "farmacoterapia × cuidador", "e": "metodológico MRCI/ZBI"},
  "meta": "todos",
  "filtro_anos": null,
  "buscas_nomes": {"S-0001": "Busca 1 — relação central", "S-0002": "Busca 2 — ..."},
  "observacoes": ["Texto livre para a seção OBSERVAÇÕES do relatório."]
}
```
`objetivos_especificos` aceita `<b>`/`<i>`. `eixos` alimenta a linha "Contribuição" de cada referência.
`buscas_nomes` dá o rótulo de cada busca no relatório (se faltar, usa a família).
