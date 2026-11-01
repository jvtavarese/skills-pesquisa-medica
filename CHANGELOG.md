# Changelog

## cochrane-triagem-abstracts

### v1.1.0
- **Crossref** (`enrich_crossref.py`): confere as referências pelo DOI (ou por título e ano, com casamento
  estrito), preenche só os campos que a Cochrane não trouxe e lista as divergências no relatório.
- **PubMed opcional** (`fetch_pubmed.py`, ativado por `FONTE DO ABSTRACT: cochrane+pubmed`): busca o
  abstract de registros CENTRAL pelo PMID quando a página da Cochrane não pôde ser lida. Só aceita o texto
  se o título bater, e o pacote informa a fonte. A descoberta e as contagens continuam 100% Cochrane.
- `--buscar-pmid-por-doi` (opcional): encontra o PMID pelo DOI quando a Cochrane não informa (ex.:
  registros vindos do CINAHL).
- Certificados SSL: os scripts usam certifi ou o bundle do sistema e nunca desligam a verificação.
- Registros passam a guardar `pmid`; pacotes e metadados informam a fonte do abstract.
- Documentação: nova seção "APIs: o que podem e o que não podem" em `references/busca_cochrane.md`.

### v1.0.0
- Primeira versão pública: busca na Cochrane Library, triagem por abstract com Leitor A/B independentes
  e um juiz, relatório em PDF e HTML (Google Docs), modo navegador ou exportação manual, Claude Code ou
  Codex.
