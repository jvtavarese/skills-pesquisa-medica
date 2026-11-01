# Levar o relatório para o Google Docs

O `.html` gerado por `build_report.py` vira um Google Doc formatado (títulos, tabela, negritos, links).

## Caminho recomendado: a pessoa faz o upload
Passe estes passos (funcionou na prática):
1. Google Drive → engrenagem ⚙️ → **Configurações** → marcar **"Converter uploads no formato dos Editores
   de arquivos Google"**.
2. **Novo → Upload de arquivo** (ou arrastar) → escolher `resultados/Levantamento_Cochrane.html`.
3. O arquivo aparece com ícone azul do Google Docs. Renomear se quiser.
4. Se aparecer como HTML: a conversão estava desligada; ligar, apagar e subir de novo. "Abrir com" não
   converte HTML.

Não mude configurações da conta da pessoa por conta própria; mostre os passos.

## Alternativa: conector do Google Drive
Se houver conector do Drive no ambiente e o HTML for pequeno (< ~30 KB), `create_file` com
`contentMimeType: "text/html"` cria o Doc direto. Relatórios grandes (dezenas de referências) não cabem
de forma confiável numa chamada — prefira o upload pela pessoa.

Atenção: o conector e o navegador podem estar logados em contas Google diferentes. Confirme em qual conta
o arquivo deve ficar.
