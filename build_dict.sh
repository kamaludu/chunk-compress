#!/usr/bin/env bash
# Script 2 — dizionario simboli
set -euo pipefail

SRC="${1:?devi passare SRC}"
TMPDIR="./tmp"
DICTDIR="./dict"
CHUNKDIR="./chunks"

mkdir -p "$TMPDIR" "$DICTDIR"
chmod 700 "$TMPDIR"

# Estrai simboli dai chunk generati
grep -Eo '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*\(\)[[:space:]]*\{' "$CHUNKDIR"/* 2>/dev/null \
  | sed 's/(.*//' | awk '{print $NF}' | sort -u > "$DICTDIR/fns.txt" || true

grep -Eo '^[[:space:]]*[A-Z_][A-Z0-9_]*=' "$CHUNKDIR"/* 2>/dev/null \
  | sed 's/=.*//' | awk '{print $NF}' | sort -u > "$DICTDIR/vars.txt" || true

python3 build_dict.py
