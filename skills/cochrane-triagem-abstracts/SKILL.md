---
name: cochrane-triagem-abstracts
description: >-
  Levantamento bibliográfico na Cochrane Library com triagem por abstract feita por dois leitores
  independentes e um juiz, terminando num relatório no estilo "busca → quantos vieram → quantos usei →
  referências" em PDF e pronto para Google Docs. Use sempre que alguém pedir para buscar, selecionar,
  triar ou levantar artigos na Cochrane (CENTRAL ou revisões) para um projeto, TCC, iniciação científica,
  revisão ou introdução de artigo, mesmo que não diga "triagem" — por exemplo "acha 10 artigos na
  Cochrane sobre X", "faz a busca da Cochrane do meu projeto", "quero as strings de busca e quantos
  artigos vieram", ou quando colarem um briefing com título, objetivo geral e objetivos específicos
  pedindo literatura. Funciona inteiramente no Claude Code OU inteiramente no Codex (ChatGPT).
---

# Triagem Cochrane por abstract

Transforma o briefing de um projeto em uma lista auditável de artigos da Cochrane Library, cada um
lido por dois leitores independentes e decidido por um juiz, e entrega um relatório bonito.

O valor da skill está em três garantias. Mantenha-as mesmo sob pressão para "bater a meta":
1. **Rastreabilidade** — toda busca, contagem, URL e abstract vem de páginas da Cochrane e fica salvo.
2. **Independência** — os leitores A e B não veem o parecer um do outro; o juiz decide relendo o abstract,
   nunca por votação.
3. **Honestidade** — se não houver artigos suficientes, entregue os que existem e diga isso. Não afrouxe
   critérios, não invente metadados, não use texto completo nem outras bases.

## 1. Input — o que a pessoa precisa fornecer

Peça só o que faltar. O mínimo é o **briefing do projeto**:

| Campo | Obrigatório | Exemplo |
|---|---|---|
| Título do projeto | sim | "Impacto da complexidade farmacoterapêutica na sobrecarga do cuidador…" |
| Objetivo geral | sim | um parágrafo |
| Objetivos específicos | sim | lista numerada |
| Meta de artigos | não (padrão: **todos os válidos**) | "10" ou "todos" |
| Filtro de anos | não (padrão: sem filtro) | "2021–2026" |
| Strings de busca prontas | não (a skill propõe) | booleanas da Cochrane |
| Exportações da Cochrane | não (só no modo manual) | arquivos `.txt`/`.ris` **com abstract** |
| Fonte do abstract | não (padrão: `cochrane`) | `cochrane` ou `cochrane+pubmed` (ver 3.4) |

O briefing pode chegar como texto colado, arquivo `.md`/`.docx`/`.pdf` ou link do Google Docs (leia com
o conector do Drive, se houver). O modelo de briefing está em `assets/briefing_modelo.md` — ofereça-o
quando a pessoa não souber o que mandar.

Converta o briefing em `briefing.json` no diretório de trabalho (formato em `assets/briefing_modelo.md`)
e confirme com a pessoa em uma mensagem curta antes de buscar.

## 2. Identifique o ambiente (uma vez, no início)

A skill roda **só no Claude Code** ou **só no Codex**. Nunca misture: tudo — busca, leitores, juiz — usa
as ferramentas do ambiente em que você está. Leia `references/ambientes.md` e decida:

- **Navegador**: qual navegador nativo existe (Claude in Chrome / navegador embutido / Orca no Claude;
  navegador ou extensão de Chrome no Codex). Se nenhum funcionar, use o **modo manual** (a pessoa exporta
  da Cochrane e envia os arquivos).
- **Contextos independentes**: como abrir leitores A, B e juiz em contextos novos (subagentes no Claude
  Code; `codex exec` ou subagentes no Codex).

Diga à pessoa, em uma linha, qual caminho vai usar.

## 3. Fluxo

Crie um diretório de trabalho (ex.: `levantamento-<tema>/`) com `briefing.json`, `buscas/`, `artigos/`,
`resultados/`. Os scripts ficam em `scripts/` desta skill; rode-os com `python3 <skill>/scripts/<nome>`.
Todos têm `--help`.

### 3.1 Estratégia de busca
1. A partir do briefing, monte blocos de conceitos (população, exposição/intervenção, desfecho, e o que
   mais o projeto pedir) e famílias de busca do mais específico ao mais amplo — a relação central primeiro,
   depois combinações parciais, depois os instrumentos/escalas citados. Veja `references/busca_cochrane.md`
   para a sintaxe (frases com curinga usam `NEXT`, não aspas).
2. Se a pessoa trouxe strings, use-as como estão e só acrescente reformulações justificadas.
3. Busque no campo *Title Abstract Keyword*, aplique só os filtros pedidos.

### 3.2 Executar e registrar
Para cada busca, registre com `scripts/log_search.py` (consulta literal, filtros, contagens por seção,
data, URL). Registre também buscas com zero resultados. Busca que retorna centenas de itens fora da
população: registre a contagem e crie uma reformulação restrita, registrada como nova busca.

- **Modo navegador**: rode a busca, liste todos os resultados (título, ID CN-/CD, fonte, citação) e salve
  em `buscas/S-NNNN.json` (formato em `references/busca_cochrane.md`).
- **Modo manual**: peça à pessoa, para cada string, a contagem exibida e a exportação "Plain text" ou RIS
  com *Include abstract* marcado. Converta com `scripts/parse_export.py`.

### 3.3 Pré-triagem e deduplicação
Rode `scripts/prescreen.py`: junta as buscas, remove repetidos e marca automaticamente registros de
ensaio (ICTRP/ClinicalTrials.gov), protocolos e registros sem abstract. Depois, você lê os títulos que
sobraram e marca no CSV os claramente fora dos objetivos, com motivo curto. Na dúvida, mande para leitura
— a pré-triagem por título é só uma peneira grossa. Versões do mesmo estudo (resumo de congresso + artigo,
preprint + artigo): mantenha a versão em periódico e marque as outras como `versao_sobreposta`.

### 3.4 Pacotes imutáveis
- **Modo navegador**: abra a página de cada candidato
  (`https://www.cochranelibrary.com/central/doi/10.1002/central/<CN-ID>/full`), salve o texto da página em
  `artigos/_paginas/<ID>.txt` e rode `scripts/parse_record_page.py` para gerar o registro.
- **Modo manual**: o abstract já veio na exportação.
- **Complemento PubMed (opcional, só com `cochrane+pubmed`)**: quando o registro CENTRAL veio do PubMed,
  a Cochrane informa o PMID. `scripts/fetch_pubmed.py --dir <dir>` busca na API do PubMed o abstract
  **desse mesmo registro** para quem ficou sem abstract (página não abriu, navegador bloqueado,
  exportação sem abstract). Ele só aceita o texto se o título do PubMed bater com o da Cochrane, e o
  pacote informa a fonte ("Abstract integral (PubMed PMID …)"). A **descoberta e as contagens continuam
  100% Cochrane**: o PubMed nunca adiciona artigos à lista. Use isso para reduzir dependência do
  navegador, não para ampliar a busca. Com a fonte `cochrane` (padrão), não use este passo; registros
  sem abstract continuam `sem_abstract`.
  - Registros sem PMID na Cochrane (comuns quando vêm do CINAHL) podem ser tentados com
    `--buscar-pmid-por-doi`: procura o PMID pelo DOI informado pela Cochrane, com a mesma checagem de
    título.
  - Depois de preencher, rode `prescreen.py` de novo antes do `build_packets.py`; senão os registros
    recém-preenchidos continuam marcados `sem_abstract`.
  - Rodar `parse_record_page.py` de novo sobrescreve o registro; rode `fetch_pubmed.py` em seguida.

Então `scripts/build_packets.py` cria `artigos/ART-NNNN/pacote.md` + `metadados.json` (somente leitura,
com hash). Registros CENTRAL são rotulados "artigo indexado no CENTRAL — não é revisão Cochrane".

### 3.5 Critérios congelados
Preencha `references/criterios_modelo.md` com os eixos de relevância derivados dos objetivos do briefing
e salve como `CRITERIOS_LEITURA.md`. Os eixos devem permitir que um artigo ajude **parte** do projeto
(ex.: só o lado da exposição, só o lado do desfecho, ou só o instrumento), porque a relação central quase
nunca existe pronta. Mostre os eixos à pessoa numa mensagem curta. A partir daqui o arquivo não muda.

### 3.6 Leitores e juiz
Gere os prompts com `scripts/make_prompts.py` e rode-os conforme `references/ambientes.md`:
1. **Piloto**: 3 artigos de perfis diferentes. Leitor A e B em paralelo; valide com
   `scripts/validate_opinions.py`; depois o juiz. Confira se os JSON vieram completos e se as citações são
   literais. Corrija o prompt antes de seguir, se preciso.
2. **Lotes**: o restante, em lotes de até ~30 artigos por leitor. Sempre A e B antes do juiz.
3. Quando o juiz apontar algo de elegibilidade (protocolo, duplicata, mesmo estudo), verifique no pacote e
   registre sua decisão em `artigos/ART-NNNN/elegibilidade_coordenador.json` — não edite pareceres.

Continue até atingir a meta ou esgotar os candidatos. Se a meta for "todos", leia todos.

### 3.7 Relatório
Antes, rode `scripts/enrich_crossref.py --dir <dir>`: ele confere os metadados de cada artigo no
Crossref (pelo DOI ou, sem DOI, por um casamento estrito de título e ano) e preenche só o que a
Cochrane não trouxe (DOI, volume, número, páginas). Valores da Cochrane nunca são sobrescritos; as
divergências vão para o relatório. Sem internet, pule este passo: o relatório funciona sem ele.

Depois rode `scripts/build_report.py` no diretório de trabalho. Ele gera:
- `resultados/triagem_abstracts.md` — tabela de decisões A/B/juiz com motivos;
- `resultados/Levantamento_Cochrane.pdf` — título, objetivos, tabela "vieram / registros / lidos / usados",
  cada busca com sua string e referências numeradas (AMA, com DOI e link Cochrane), lista final sem
  repetição e observações;
- `resultados/Levantamento_Cochrane.html` — mesma coisa, para virar Google Docs.

Abra o PDF (ou renderize uma página) e confira antes de entregar.

### 3.8 Google Docs
Se a pessoa quiser Google Docs, siga `references/google_docs.md`. O caminho confiável é a própria pessoa
fazer upload do `.html` com "Converter uploads" ligado; ofereça o passo a passo em vez de mudar
configurações da conta dela.

## 4. Entrega

Responda curto: quantos artigos válidos, como se dividem pelos objetivos, se existe evidência direta para
a pergunta central, o que ficou incerto e por quê, e os caminhos dos arquivos. Se faltou artigo para a meta,
diga quantos e por quê.

## 5. Retomada

Trabalho longo pode parar no meio. Mantenha `CHECKPOINT.md` no diretório de trabalho (objetivo, feito,
próximo passo, decisões) e atualize após cada etapa. Ao retomar, leia-o e confira os arquivos antes de
refazer qualquer coisa.
