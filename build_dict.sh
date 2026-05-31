#!/usr/bin/env bash
# Script 2 — dizionario simboli
# legge .pipeline_src, genera dict/*.txt e dict/global.json
set -euo pipefail

PIPEFILE=".pipeline_src"
TMPDIR="./tmp"
DICTDIR="./dict"
CHUNKDIR="./chunks"

[ -f "$PIPEFILE" ] || { echo "Run chunk.sh first to create $PIPEFILE"; exit 1; }
SRC="$(cat "$PIPEFILE")"

mkdir -p "$TMPDIR" "$DICTDIR"
chmod 700 "$TMPDIR"

tmpfns="$TMPDIR/fns.tmp"
tmpvars="$TMPDIR/vars.tmp"
: > "$tmpfns"
: > "$tmpvars"

# raccogli simboli da tutti i chunk (gestisce nomi con spazi)
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  # funzioni stile shell: name() {
  grep -Eo '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*\(\)[[:space:]]*\{' "$f" 2>/dev/null \
    | sed 's/(.*//' | awk '{print $NF}' >> "$tmpfns" || true

  # variabili costanti in MAIUSCOLO=
  grep -Eo '^[[:space:]]*[A-Z_][A-Z0-9_]*=' "$f" 2>/dev/null \
    | sed 's/=.*//' | awk '{print $NF}' >> "$tmpvars" || true
done < <(find "$CHUNKDIR" -type f -print0 2>/dev/null)

# dedup e output finale (file vuoti se niente trovato)
sort -u "$tmpfns" -o "$DICTDIR/fns.txt" || :
sort -u "$tmpvars" -o "$DICTDIR/vars.txt" || :

# chiama lo script Python per costruire il dict globale (passando SRC via env)
SRC="$SRC" python3 build_dict.py
echo "Built dict in $DICTDIR/global.json"
