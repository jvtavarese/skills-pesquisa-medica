# Ambientes: Claude Code **ou** Codex

Escolha um ambiente e use só as ferramentas dele do começo ao fim. Misturar (ex.: leitores no Codex e
juiz no Claude) quebra a rastreabilidade e exige duas assinaturas.

## Como saber onde você está
- **Claude Code**: você tem ferramentas como `Agent`/`Task`, `Bash`, `Read`, `Write`, e possivelmente
  `mcp__claude-in-chrome__*` ou `mcp__Claude_Browser__*`.
- **Codex**: você roda no Codex CLI/IDE/app (ChatGPT); tem shell e `apply_patch`; o binário `codex` existe
  no PATH; navegador vem do próprio Codex (navegador embutido ou extensão do Chrome), se habilitado.

## Navegador

Teste uma vez abrindo `https://www.cochranelibrary.com/advanced-search` e lendo o título da página.

| Ambiente | Opções, na ordem | Observações |
|---|---|---|
| Claude Code | 1. Claude in Chrome (`mcp__claude-in-chrome__*`) 2. navegador embutido do app (`mcp__Claude_Browser__*`) 3. Orca (`orca goto/snapshot/eval`) se a sessão roda no Orca | Carregue as ferramentas deferidas numa única busca. Evite diálogos `alert`. |
| Codex | 1. navegador embutido do Codex 2. extensão Codex para Chrome | Use o que estiver habilitado; não instale Playwright/Chrome externo sem a pessoa pedir. |
| Nenhum funciona | **modo manual** | A pessoa roda as strings e envia as exportações (ver `busca_cochrane.md`). |

Dicas que valem para qualquer navegador:
- A busca avançada é um formulário: preencha a caixa "Type a search term" e clique "Run search". Mudar
  a URL não refaz a busca (a página devolve a última busca da sessão). Confira que o cabeçalho
  "N Trials matching <sua consulta>" bate com a consulta antes de anotar números.
- As abas "Cochrane Reviews" e "Trials" têm contagens separadas; registre as duas.
- Paginação: siga o link "Next" (25 por página). Extraia cada item de `.search-results-item`
  (`h3 a` = título/link, checkbox `value` = ID CN-, `.search-result-metadata-text` = citação,
  `.external-database-reference` = origem PubMed/Embase/ICTRP/CT.gov).
- Página de registro: leia `document.body.innerText` inteiro e salve. Se o texto disser
  "This CENTRAL record does not have an abstract.", o registro não tem abstract.

## Contextos independentes (leitor A, leitor B, juiz)

O objetivo é que cada leitor comece com contexto vazio, receba o mesmo prompt e não veja o outro parecer.

### Claude Code
- Use a ferramenta `Agent` (subagente `general-purpose`), um subagente por leitor por lote. Dispare A e B
  **na mesma resposta** (paralelo). O juiz só depois que os dois terminarem.
- Alternativa sem subagentes: `claude -p "$(cat prompt_A.txt)" --allowedTools "Read,Write,Bash"` em
  processos separados.
- Se a sessão estiver no Orca com orquestração, `orca orchestration worker-start --agent claude` também
  serve (A e B como dois workers `claude`).

### Codex
- Use `codex exec` em processos separados, um por leitor:
  `codex exec --skip-git-repo-check -C <dir> "$(cat prompt_A.txt)" > logs/A.log 2>&1 &`
  e o mesmo para B; espere ambos (`wait`) e só então rode o juiz.
- Se o Codex da pessoa oferecer subagentes nativos, eles servem também, desde que cada um comece vazio.
- No Orca: `orca orchestration worker-start --agent codex`.

### Em qualquer ambiente
- Leitores e juiz **só** podem ler `CRITERIOS_LEITURA.md` e os `pacote.md` listados (o juiz também os
  dois pareceres). Isso está escrito nos prompts gerados por `make_prompts.py`.
- Depois de cada lote, rode `validate_opinions.py`. Se possível, confira nos logs/transcrições que nenhum
  leitor abriu `parecer_` do outro.
- Não reenvie um lote por "silêncio": verifique se o processo ainda roda ou se os arquivos já existem.
