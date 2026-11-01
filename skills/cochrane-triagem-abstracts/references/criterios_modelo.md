# Critérios de leitura por abstract — v1.0 (idênticos para Leitor A, Leitor B e Juiz)

Projeto: {{TITULO}}

## Escopo
- Avalie SOMENTE o abstract e os metadados do `pacote.md` (capturados da Cochrane Library).
- Proibido: internet, URLs, texto completo, outras bases, memória sobre o estudo, inferir dados ausentes.
- Registros CENTRAL são "artigos indexados", não revisões Cochrane.
- Sem abstract ou abstract insuficiente para julgar: decisão `incerto`.

## Eixos de relevância (o abstract deve sustentar CLARAMENTE ao menos um)
{{EIXOS}}
<!-- Exemplo (projeto DRC/MRCI/ZBI):
- (a) complexidade do regime / MRCI em DRC;
- (b) medicamentos, polifarmácia, doses, formas ou instruções em DRC;
- (c) sobrecarga, estresse ou impacto psicossocial de cuidadores informais de pacientes com DRC;
- (d) relação entre manejo farmacoterapêutico e sobrecarga do cuidador em DRC (relação central);
- (e) uso do MRCI ou ZBI com contribuição metodológica explícita (fora da população, só este eixo vale).
-->

Regras:
- Menção incidental NÃO basta: o eixo precisa ser objetivo, exposição ou desfecho do estudo.
- Aproximações não são o instrumento: {{APROXIMACOES}}
  <!-- ex.: "número de medicamentos ≠ MRCI; estresse ≠ ZBI" -->
- Eficácia de um fármaco/intervenção isolada só conta se tocar diretamente um eixo.
- Fora da população-alvo, só o eixo metodológico pode valer, e apenas com contribuição explícita ao instrumento.

## Classes
- `direta`: sustenta a relação central do projeto na população-alvo.
- `apoio`: sustenta claramente um dos lados da relação na população-alvo.
- `metodologica`: contribuição explícita à mensuração/aplicação/interpretação de um instrumento do projeto.
- `nenhuma`: não relevante ou incerto.

## Objetivos do projeto (para objective_mapping)
{{OBJETIVOS}}
<!-- ex.: OG: ...; OE1: ...; OE2: ...; OE3: ...; OE4: ... -->

## Saída do LEITOR (JSON único, UTF-8)
{
  "article_id": "ART-NNNN",
  "reader_id": "A" | "B",
  "decision": "relevante" | "nao_relevante" | "incerto",
  "relevance_class": "direta" | "apoio" | "metodologica" | "nenhuma",
  "axes_supported": ["a", ...],
  "objective_mapping": ["OG", "OE1", ...],
  "abstract_evidence": [{"location": "seção/frase", "quote": "trecho LITERAL curto do abstract"}],
  "reason": "justificativa em português",
  "missing_information": ["..."],
  "confidence": "alta" | "moderada" | "baixa",
  "read_only_packet": true,
  "independence_statement": "Li apenas pacote.md e CRITERIOS_LEITURA.md; não li parecer de outro leitor nem pesquisei fontes externas."
}

## Saída do JUIZ (JSON único)
{
  "article_id": "ART-NNNN",
  "decision": "incluir" | "excluir" | "incerto",
  "relevance_class": "direta" | "apoio" | "metodologica" | "nenhuma",
  "axes_supported": [...], "objective_mapping": [...],
  "abstract_evidence": [{"location": "...", "quote": "..."}],
  "reason": "fundamentação própria após reler o abstract",
  "reader_a_decision": "...", "reader_b_decision": "...",
  "divergences": "divergências entre A e B (ou 'nenhuma')",
  "resolution": "como o abstract resolve a divergência (sem votação)",
  "eligibility_flags": ["protocolo", "possivel_duplicata:ART-NNNN", ...],
  "missing_information": [...], "limitations": [...],
  "confidence": "alta" | "moderada" | "baixa",
  "source_reread": true,
  "independence_statement": "Reli o abstract; usei apenas pacote, critérios e os dois pareceres."
}
`incluir` só quando o abstract sustenta claramente um eixo. `incerto` não conta como válido.
