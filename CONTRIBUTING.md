# Como contribuir

Obrigado por querer ajudar. Este repositório só funciona se pesquisadores, estudantes e desenvolvedores
melhorarem as skills juntos.

## Formas de contribuir

| Você quer… | Faça assim |
|---|---|
| Reportar um problema | Abra uma issue com o modelo **Bug**. Diga a ferramenta (Claude Code ou Codex), o briefing (pode anonimizar), o que esperava e o que aconteceu. |
| Sugerir melhoria | Issue com o modelo **Melhoria**. |
| Propor uma skill nova | Issue com o modelo **Nova skill**, antes de escrever código, para alinharmos o escopo. |
| Corrigir algo | Fork → branch → pull request. PRs pequenos e focados são revisados mais rápido. |
| Adaptar para outra base/área | Fork livre. Se a adaptação servir a muita gente, abra um PR criando uma skill irmã (ex.: `pubmed-triagem-abstracts`). |

## Estrutura de uma skill

```
skills/<nome-da-skill>/
├── SKILL.md          obrigatório: frontmatter (name, description) + instruções
├── README.md         para humanos: instalação, input, output, limitações
├── scripts/          código determinístico (Python stdlib + dependências declaradas)
├── references/       textos que o agente lê sob demanda
└── assets/           modelos e arquivos usados na saída
```

Comece copiando `templates/skill-modelo/`.

## Regras para uma skill entrar aqui

1. **Funciona só no Claude Code ou só no Codex, sem misturar.** Documente como ela se comporta em cada um
   (navegador, subagentes, comandos).
2. **Input claro.** O README diz exatamente o que a pessoa precisa mandar, com exemplo.
3. **Sem invenção de dados.** Metadados, números e citações vêm de fonte verificável; o que faltar fica
   marcado como ausente.
4. **Sem dados pessoais ou de pacientes.** Nada de prontuário, nome de paciente ou dado sensível em
   exemplos, testes ou commits.
5. **Testada.** Descreva no PR como você testou (caso real anonimizado, amostra sintética, etc.) e o
   resultado.
6. **Scripts com `--help`.** Cada script explica o próprio uso.
7. **Português primeiro.** Textos para o usuário em português; termos técnicos e de busca podem ficar em
   inglês.

## Checklist do pull request

- [ ] `SKILL.md` com `name` e `description` (a descrição diz o que faz e quando usar)
- [ ] `README.md` da skill com input, output e limitações
- [ ] Testei no Claude Code e/ou no Codex (diga qual)
- [ ] Nenhum dado pessoal, credencial ou caminho da minha máquina
- [ ] Atualizei a tabela de skills no `README.md` principal (se for skill nova)

## Validação rápida

Se você tem o `skill-creator` do Claude, rode:

```bash
python -m scripts.quick_validate skills/<nome-da-skill>
```

Sem ele, confira manualmente se o frontmatter do `SKILL.md` tem `name` e `description`.

## Conduta

Seja gentil e objetivo. Crítica é ao trabalho, nunca à pessoa. Veja o
[código de conduta](CODE_OF_CONDUCT.md).
