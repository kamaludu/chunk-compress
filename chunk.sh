#!/usr/bin/env bash
# Script 1 — chunking + normalizzazione
# Examples:
# ./chunk.sh my_path/
# ./chunk.sh ./my_path/my_file.sh
# ./chunk.sh "./my_path/*.sh"
# ./chunk.sh "src/a.sh src/b.sh"
# ./chunk.sh "src/**/*.sh"
set -euo pipefail

SRC="${1:?devi passare SRC}"
OUTDIR="./chunks"
TMPDIR="./tmp"
WORKDIR="./ui_work"
CHUNK_LINES=250

mkdir -p "$TMPDIR" "$OUTDIR" "$WORKDIR"
chmod 700 "$TMPDIR"

# resolve_sources: emette percorsi null-separated
resolve_sources() {
  # singolo file
  if [ -f "$SRC" ]; then
    printf '%s\0' "$SRC"
    return
  fi

  # directory (non ricorsiva)
  if [ -d "$SRC" ]; then
    find "$SRC" -maxdepth 1 -type f -print0
    return
  fi

  # lista o glob: iteriamo sugli elementi passati (split su whitespace)
  for item in $SRC; do
    # l'iterazione su $item espande i glob (es. "./src/*.sh")
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
