#!/usr/bin/env bash
# Script 1 — chunking + normalizzazione
set -euo pipefail

# Uso:
# ./chunk.sh /percorso/alla/sorgente
# ./chunk.sh "./src/*.sh"
# SRC viene richiesto una sola volta qui e salvato in .pipeline_src

SRC="${1:?Usage: $0 SRC}"
OUTDIR="./chunks"
TMPDIR="./tmp"
WORKDIR="./ui_work"
CHUNK_LINES=250
PIPEFILE=".pipeline_src"

mkdir -p "$TMPDIR" "$OUTDIR" "$WORKDIR"
chmod 700 "$TMPDIR"

# salva SRC per gli altri script (un solo punto di configurazione)
printf '%s' "$SRC" > "$PIPEFILE"

# resolve_sources: emette percorsi null-separated
resolve_sources() {
  if [ -f "$SRC" ]; then
    printf '%s\0' "$SRC"
    return
  fi

  if [ -d "$SRC" ]; then
    find "$SRC" -maxdepth 1 -type f -print0
    return
  fi

  # lista o glob: iteriamo sugli elementi passati (split su whitespace)
  for item in $SRC; do
    for f in $item; do
      [ -f "$f" ] && printf '%s\0' "$f"
    done
  done
}

# processa ogni file (legge input null-separated)
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  # normalizza CRLF e trailing spaces
  sed -e 's/\r$//' -e 's/[[:space:]]\+$//' "$f" > "$WORKDIR/$base"
  # split in chunk di CHUNK_LINES righe
  split -l "$CHUNK_LINES" --numeric-suffixes=1 --additional-suffix=.chunk \
        "$WORKDIR/$base" "$OUTDIR/$base."
done < <(resolve_sources)

echo "Wrote chunks to $OUTDIR; SRC saved in $PIPEFILE"
