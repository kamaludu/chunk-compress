#!/usr/bin/env bash
# Script 1 — chunking + normalizzazione
set -euo pipefail
TMPDIR=./tmp
mkdir -p "$TMPDIR" ui_work chunks
chmod 700 "$TMPDIR"
for f in ui/*; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  sed -e 's/\r$//' -e 's/[[:space:]]\+$//' "$f" > "ui_work/$base"
  split -l 250 --numeric-suffixes=1 --additional-suffix=.chunk "ui_work/$base" "chunks/$base."
done
