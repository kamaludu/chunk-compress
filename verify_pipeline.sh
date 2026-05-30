#!/usr/bin/env bash
# Script 4 - Verifica automatica (richiede SRC come argomento)
set -euo pipefail

SRC="${1:?devi passare SRC}"
TMPDIR="./tmp"
CHUNKDIR="./chunks"
OUTDIR="./out"
DICTFILE="./dict/global.json"

[ -d "$TMPDIR" ] || { echo "Create tmp/: mkdir -p $TMPDIR && chmod 700 $TMPDIR"; exit 1; }
[ -d "$CHUNKDIR" ] || { echo "Missing chunks/ directory"; exit 1; }
[ -d "$OUTDIR" ] || { echo "Missing out/ directory"; exit 1; }

echo "SRC: $SRC"

# conteggi robusti
chunk_count=$(find "$CHUNKDIR" -maxdepth 1 -type f | wc -l)
pack_records=0
[ -f "$OUTDIR/pack.jsonl" ] && pack_records=$(wc -l < "$OUTDIR/pack.jsonl")

echo "chunks: $chunk_count"
echo "pack records: $pack_records"

# dict entries
dict_entries=0
if [ -f "$DICTFILE" ]; then
  dict_entries=$(python3 - <<PY
import json,sys
p='$DICTFILE'
try:
    d=json.load(open(p)).get('d',{})
    print(len(d))
except Exception:
    print(0)
PY
)
fi
echo "dict entries: $dict_entries"

# sizes (du) con controllo zero
orig=0
pack=0
if [ -e "$SRC" ]; then
  orig=$(du -sb "$SRC" 2>/dev/null | cut -f1 || echo 0)
fi
pack=$(du -sb "$OUTDIR" 2>/dev/null | cut -f1 || echo 0)

echo "orig: $orig"
echo "pack: $pack"
python3 - <<PY
orig=$orig; pack=$pack
if orig and pack:
    ratio=round((1-pack/orig)*100,2)
else:
    ratio=None
print("ratio_pct:", ratio)
PY

# Roundtrip test (prime 3 bodies) - ricostruzione usando mapping short->orig
echo "Roundtrip test (first 3 bodies)"
if [ -f "$OUTDIR/pack.jsonl" ]; then
  # elenco primi 3 file body.*.tok in modo robusto
  mapfile -t bodies < <(find "$OUTDIR" -maxdepth 1 -type f -name 'body.*.tok' -print0 | xargs -0 -n1 | sort | head -n3)
  for f in "${bodies[@]}"; do
    h=$(basename "$f" | sed 's/body\.//;s/\.tok//')
    python3 - <<PY
import json,os,sys
dfile='${DICTFILE}'
bfile='${f}'
if not os.path.exists(bfile):
    print('missing', bfile); sys.exit(0)
D={}
if os.path.exists(dfile):
    try:
        D=json.load(open(dfile)).get('d',{})
    except Exception:
        D={}
# invert mapping: short -> orig
inv = {v:k for k,v in D.items()}
b = open(bfile,'r',encoding='utf-8').read()
# replace short tokens with originals (longest-first to avoid partial collisions)
for short in sorted(inv.keys(), key=len, reverse=True):
    b = b.replace(short, inv[short])
print('---', '${h}', 'len', len(b))
PY
  done
else
  echo "No pack.jsonl found; skipping roundtrip."
fi

# Missing function symbols (sample)
echo "Missing function symbols (sample)"
find "$CHUNKDIR" -type f -print0 2>/dev/null | xargs -0 grep -Eo '([a-zA-Z_][a-zA-Z0-9_]*\(\))' 2>/dev/null \
  | sed 's/()//' | sort -u > "$TMPDIR/chunk_fns.txt" || true

python3 - <<PY
import json,os,sys
dfile='${DICTFILE}'
tmp='${TMPDIR}/chunk_fns.txt'
if not os.path.exists(dfile):
    print('no dict'); sys.exit(0)
D=set(json.load(open(dfile)).get('d',{}).values())
C=set(open(tmp).read().splitlines()) if os.path.exists(tmp) else set()
miss=sorted(list(C - D))
print(len(miss))
print('\\n'.join(miss[:10]))
PY

# Side-effect tags
echo "Side-effect tags:"
if [ -f "$OUTDIR/pack.jsonl" ]; then
  python3 - <<PY
import json,sys
from collections import Counter
c=Counter()
for l in open('out/pack.jsonl','r',encoding='utf-8'):
    try:
        r=json.loads(l)
    except Exception:
        continue
    for e in r.get('e',[]): c[e]+=1
print(dict(c))
PY
else
  echo "{}"
fi

echo "Done"
