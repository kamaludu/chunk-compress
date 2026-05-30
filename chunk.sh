#!/usr/bin/env bash
# Script 1 — chunking + normalizzazione
# Examples:
# ./chunk.sh my_path/
# ./chunk.sh ./my_path/my_file.sh
# ./chunk.sh "./my_path/*.sh"
# ./chunk.sh "src/a.sh src/b.sh"
# ./chunk.sh "src/**/*.sh"
set -euo pipefail

SRC="${1:-my_path}"     # default: my_path
OUTDIR="./chunks"
TMPDIR="./tmp"

mkdir -p "$TMPDIR" "$OUTDIR" ui_work
chmod 700 "$TMPDIR"

# Normalizza: file singolo, directory, glob, lista
resolve_sources() {
    # Se è un file singolo
    if [ -f "$SRC" ]; then
        printf '%s\n' "$SRC"
        return
    fi

    # Se è una directory
    if [ -d "$SRC" ]; then
        find "$SRC" -maxdepth 1 -type f
        return
    fi

    # Se è una lista di percorsi
    for item in $SRC; do
        for f in $item; do
            [ -f "$f" ] && printf '%s\n' "$f"
        done
    done
}

for f in $(resolve_sources); do
    base=$(basename "$f")
    sed -e 's/\r$//' -e 's/[[:space:]]\+$//' "$f" > "ui_work/$base"
    split -l 250 --numeric-suffixes=1 --additional-suffix=.chunk \
        "ui_work/$base" "$OUTDIR/$base."
done
