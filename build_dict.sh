#!/usr/bin/env bash
# Script 2 — dizionario simboli
set -euo pipefail
TMPDIR=./tmp
mkdir -p "$TMPDIR" dict
chmod 700 "$TMPDIR"
grep -Eo '^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*\(\)[[:space:]]*\{' chunks/* 2>/dev/null \
  | sed 's/[[:space:]]*(.*//' | awk '{print $NF}' | sort -u > dict/fns.txt || true
grep -Eo '^[[:space:]]*[A-Z_][A-Z0-9_]*=' chunks/* 2>/dev/null \
  | sed 's/=.*//' | awk '{print $NF}' | sort -u > dict/vars.txt || true
grep -Eo 'id="[a-zA-Z0-9_-]+"' templates/* 2>/dev/null \
  | sed 's/.*id="//;s/"//' | sort -u > dict/ids.txt || true
grep -Eo 'class="[a-zA-Z0-9_ -]+"' templates/* 2>/dev/null \
  | sed 's/.*class="//;s/"//' | tr ' ' '\n' | sort -u > dict/classes.txt || true
python3 build_dict.py
