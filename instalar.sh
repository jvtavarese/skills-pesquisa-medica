#!/usr/bin/env bash
# Instala as skills deste repositório no Claude Code ou no Codex.
# Uso: ./instalar.sh claude|codex [nome-da-skill]
set -euo pipefail
destino_de() {
  case "$1" in
    claude) echo "$HOME/.claude/skills" ;;
    codex)  echo "$HOME/.codex/skills" ;;
    *) echo "Uso: $0 claude|codex [nome-da-skill]" >&2; exit 1 ;;
  esac
}
DEST=$(destino_de "${1:-}")
RAIZ="$(cd "$(dirname "$0")" && pwd)/skills"
mkdir -p "$DEST"
for s in "$RAIZ"/*/; do
  nome=$(basename "$s")
  [ -n "${2:-}" ] && [ "$2" != "$nome" ] && continue
  rm -rf "${DEST:?}/$nome"; cp -R "$s" "$DEST/$nome"
  echo "✔ $nome instalada em $DEST/$nome"
done
python3 -c "import reportlab" 2>/dev/null || echo "Aviso: instale o reportlab para gerar PDFs: pip install reportlab"
echo "Pronto. Abra uma nova sessão do ${1} para a skill aparecer."
