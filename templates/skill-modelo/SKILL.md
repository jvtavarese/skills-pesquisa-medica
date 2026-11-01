---
name: nome-da-skill
description: >-
  O que a skill faz, em uma frase. Depois, QUANDO usar: liste os pedidos típicos de quem pesquisa
  ("faz a tabela de extração dos artigos", "avalia o risco de viés destes ECRs"...), inclusive pedidos
  que não citam o nome da tarefa. Diga que funciona inteiramente no Claude Code OU inteiramente no Codex.
---

# Nome da skill

Um parágrafo dizendo o resultado que a pessoa recebe e por que a skill existe.

## 1. Input — o que a pessoa precisa fornecer

| Campo | Obrigatório | Exemplo |
|---|---|---|
| ... | sim | ... |

Peça só o que faltar. Se houver modelo, aponte para `assets/`.

## 2. Ambiente

Como a skill se comporta no Claude Code e no Codex (navegador, subagentes, comandos). Nunca misture os dois.

## 3. Fluxo

1. Passo, com o porquê.
2. Passo, com o script que usar (`scripts/...`, todos com `--help`).
3. Verificação antes de entregar.

## 4. Entrega

O que dizer à pessoa no fim: resultado, limites, caminhos dos arquivos.

## Regras de honestidade

- Não invente dados. O que faltar fica marcado como ausente.
- Se o resultado for insuficiente, diga isso em vez de afrouxar critérios.
