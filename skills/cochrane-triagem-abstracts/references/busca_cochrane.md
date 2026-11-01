# Busca na Cochrane Library

## Sintaxe (busca avançada, conferida em 2026-11)
- `AND`, `OR`, `NOT`, parênteses, aspas para frase.
- Curingas `*` e `?` **não funcionam dentro de aspas**. Frase com curinga: `(family NEXT caregiver*)`.
- Proximidade: `NEAR`, `NEAR/x`, `NEXT`.
- Campo padrão: *Title Abstract Keyword* (com variações de palavra).
- Seções: Cochrane Reviews, Cochrane Protocols, Trials (CENTRAL), Editorials, Special Collections.

## Como montar as famílias
1. Blocos a partir do briefing: População (P), Exposição/intervenção (E), quem mais o projeto envolve
   (ex.: cuidador, C) e Desfecho/instrumento (O). Sinônimos em inglês, siglas e termos britânicos.
2. Famílias do específico ao amplo:
   - Q1 = todos os blocos (relação central);
   - Q2, Q3 = combinações parciais (P+E+C, P+C+O…);
   - Q4 = P+E;
   - Q5, Q6 = os instrumentos citados no briefing (ex.: MRCI, ZBI), sozinhos e depois `AND P`.
3. Zero resultados também é dado: registre e siga.

## O que conta como elegível
- Revisão Cochrane concluída: sim.
- Registro CENTRAL de **artigo publicado** (origem PubMed, Embase, CINAHL…): sim, rotulado "artigo indexado
  no CENTRAL — não é revisão Cochrane". Resumo de congresso conta, mas marque como tal.
- Registro de ensaio (ICTRP, ClinicalTrials.gov) sem artigo: não.
- Protocolo (de revisão ou de ensaio, inclusive artigo-protocolo em periódico): não.
- Editorial/comentário: só se trouxer contribuição metodológica explícita.
- Duas versões do mesmo estudo: conta uma.

## Formato de `buscas/S-NNNN.json` (modo navegador)
```json
{"search_id": "S-0001", "family": "Q1", "query": "...", "section_counts": {"cochrane_review": 0, "central_trial": 44},
 "items": [{"id": "CN-02761934", "title": "...", "href": "/central/doi/10.1002/central/CN-02761934/full",
            "meta": "BMC nephrology, 2024, 25(1), 350 | added to CENTRAL: ...", "src": "PubMed", "section": "central_trial"}]}
```

## APIs: o que podem e o que não podem
A Cochrane Library não tem API pública de busca. O conteúdo é hospedado pela Wiley, e o acesso
programático depende de licença.
- **CENTRAL não é replicável por API.** PubMed e Europe PMC não reproduzem a busca nem as contagens do
  CENTRAL. Por isso a descoberta é sempre feita na própria Cochrane (navegador ou exportação manual).
- **PubMed (E-utilities)** serve para buscar o abstract de um registro CENTRAL que já tem PMID
  (`fetch_pubmed.py`, opcional, rotulado no pacote). Variáveis opcionais: `NCBI_API_KEY`
  (até 10 req/s) e `NCBI_EMAIL`. Atenção: o PMID guardado pela Cochrane pode estar desatualizado
  (artigo republicado com outro PMID); o script registra `nao_encontrado_no_pubmed` e não inventa.
- Se der erro de certificado SSL (comum no Python do python.org no macOS), rode
  "Install Certificates.command" da pasta do Python ou `pip install certifi`. Os scripts nunca
  desligam a verificação.
- **Crossref** serve para conferir e completar referências pelo DOI (`enrich_crossref.py`).
  Variável opcional: `CROSSREF_MAILTO`.
- **Revisões Cochrane via PubMed** (`"Cochrane Database Syst Rev"[Journal]`) e **Europe PMC** podem
  ser buscas auxiliares, mas precisam ser registradas e mostradas separadas das buscas da Cochrane,
  sem somar às contagens.

## Modo manual (sem navegador)
Peça à pessoa, para cada string:
1. Colar a string em https://www.cochranelibrary.com/advanced-search e clicar **Run search**.
2. Anotar os números das abas **Cochrane Reviews** e **Trials** (e do filtro de anos, se usado).
3. Em cada aba com resultados: **Select all** → **Export selected citation(s)** → **Plain text** (ou RIS)
   → marcar **Include abstract** → **Download**.
4. Enviar os arquivos dizendo a qual string pertencem.

Converta com `scripts/parse_export.py --search-id S-0001 arquivo.txt`. Se o formato não for reconhecido,
leia o arquivo e monte o JSON à mão, sem inventar campos ausentes.
