# Skills de pesquisa médica

**Skills abertas para quem faz pesquisa em saúde usar com o Claude Code ou com o Codex (ChatGPT).**

Fazer levantamento bibliográfico toma semanas de residentes, pós-graduandos, alunos de iniciação
científica e TCC. Boa parte desse tempo vai em trabalho repetitivo: montar a string, contar resultados,
descartar registros de ensaio, ler abstract por abstract, formatar referências. Este repositório junta
**skills**, que são pacotes de instruções e scripts que ensinam um agente de IA a fazer essas tarefas
do jeito que um pesquisador cuidadoso faria, com rastreabilidade e sem inventar dados.

Este repositório é da comunidade. Use, adapte, corrija e crie as suas.

---

## Skills disponíveis

| Skill | O que faz | Status |
|---|---|---|
| [`cochrane-triagem-abstracts`](skills/cochrane-triagem-abstracts/) | Busca na Cochrane Library a partir do briefing do seu projeto. Cada abstract passa por dois leitores independentes e um juiz. Entrega um relatório em PDF e Google Docs no formato "busca → quantos vieram → quantos usei → referências". | v1.1.0 · estável, testada em caso real · usa PubMed e Crossref de forma opcional |

Tem uma ideia de skill? [Abra uma sugestão](../../issues/new?template=nova-skill.md).

---

## Como usar em 2 minutos

Cada skill funciona **ou só no Claude Code ou só no Codex**. Escolha uma ferramenta e use só ela do
começo ao fim do levantamento.

### Opção 1: peça ao seu agente
Cole o link deste repositório no Claude Code ou no Codex e peça:

> Instale a skill `cochrane-triagem-abstracts` deste repositório:
> https://github.com/jvtavarese/skills-pesquisa-medica

### Opção 2: pelo terminal

```bash
git clone https://github.com/jvtavarese/skills-pesquisa-medica.git
cd skills-pesquisa-medica
./instalar.sh claude      # Claude Code  -> ~/.claude/skills
./instalar.sh codex       # Codex        -> ~/.codex/skills
```

Requisito das skills com relatório: Python 3 e `pip install reportlab`.

### Depois de instalar
Mande o briefing do seu projeto:

```
Usa a skill cochrane-triagem-abstracts com este briefing. Quero todos os artigos válidos
e o PDF + HTML para o Google Docs.

TÍTULO: ...
OBJETIVO GERAL: ...
OBJETIVOS ESPECÍFICOS:
1. ...
2. ...
```

Mais detalhes no [README da skill](skills/cochrane-triagem-abstracts/README.md).

---

## Princípios de toda skill daqui

1. **Rastreável:** toda busca, contagem e abstract tem origem verificável e fica salvo.
2. **Honesta:** se não houver evidência suficiente, a skill diz isso. Não afrouxa critério para bater
   meta e não inventa metadado.
3. **Independente onde importa:** quando há julgamento, como na triagem, ele é feito por avaliadores
   separados e arbitrado com justificativa, não por votação.
4. **Humano no comando:** a skill acelera o trabalho, e a decisão científica continua sendo sua. Leia
   [uso responsável](docs/uso-responsavel.md).

---

## Contribua

A comunidade de pesquisa médica no Brasil (e fora dele) é cheia de gente que já resolveu um pedaço
desse problema na raça. Traga a sua parte:

- 🐛 **Achou um erro?** Uma busca que falhou, uma referência mal formatada, uma decisão estranha do
  juiz. [Reporte aqui](../../issues/new?template=bug.md).
- 🌱 **Quer ramificar?** Faça um fork e adapte a skill para PubMed, LILACS, SciELO, BVS ou Embase, para
  outro estilo de referência (Vancouver, ABNT) ou para outra área (enfermagem, farmácia, odontologia).
- 🧪 **Quer criar uma skill nova?** Extração de dados para tabela de evidências, avaliação de risco de
  viés, checagem PRISMA, cálculo amostral, resumo para clube de revista... Comece pelo
  [modelo](templates/skill-modelo/SKILL.md) e pelo [guia de contribuição](CONTRIBUTING.md).
- 📣 **Usou numa pesquisa?** Conte nas [Discussions](../../discussions). Casos reais ajudam a melhorar
  as skills.

Toda contribuição passa por um critério simples: **um pesquisador cuidadoso assinaria embaixo do
resultado?**

---

## Licença

[MIT](LICENSE). Use em projetos acadêmicos, institucionais ou comerciais. Se publicar algo feito com
estas skills, citar o repositório é bem-vindo, mas não obrigatório.
