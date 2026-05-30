#!/usr/bin/env bash
# Script 4 -  Verifica automatica
set -euo pipefail
TMPDIR=./tmp
[ -d "$TMPDIR" ] || { echo "Create tmp/: mkdir -p tmp && chmod 700 tmp"; exit 1; }
echo "chunks:" $(ls -1 chunks 2>/dev/null | wc -l)
echo "pack records:" $(wc -l < out/pack.jsonl 2>/dev/null || echo 0)
echo "dict entries:" $(python3 - <<PY
import json,sys
p='dict/global.json'
print(json.load(open(p))['d'].__len__() if __import__('os').path.exists(p) else 0)
PY)
orig=$(du -sb ui | cut -f1)
pack=$(du -sb out | cut -f1)
python3 - <<PY
orig=$orig; pack=$pack
print("orig",orig,"pack",pack,"ratio_pct",round((1-pack/orig)*100,2))
PY
echo "Roundtrip test (first 3 bodies)"
for f in $(ls out/body.*.tok 2>/dev/null | head -n3); do
  h=$(basename "$f" | sed 's/body\.//;s/\.tok//')
  python3 - <<PY
import json,sys
D=json.load(open('dict/global.json'))['d']
b=open('$f','r',encoding='utf-8').read()
for k,v in D.items(): b=b.replace(k,v)
print('---', '$h', 'len', len(b))
PY
done
echo "Missing function symbols (sample)"
grep -Eo '([a-zA-Z_][a-zA-Z0-9_]*\(\))' chunks/* 2>/dev/null | sed 's/()//' | sort -u > tmp/chunk_fns.txt || true
python3 - <<PY
import json,sys,os
if not os.path.exists('dict/global.json'): print('no dict'); sys.exit(0)
D=set(json.load(open('dict/global.json'))['d'].values())
C=set(open('tmp/chunk_fns.txt').read().splitlines()) if os.path.exists('tmp/chunk_fns.txt') else set()
miss=sorted(list(C-D))
print(len(miss))
print('\\n'.join(miss[:10]))
PY
echo "Side-effect tags:"
python3 - <<PY
import json
from collections import Counter
c=Counter()
for l in open('out/pack.jsonl','r',encoding='utf-8'):
    r=json.loads(l)
    for e in r.get('e',[]): c[e]+=1
print(dict(c))
PY
echo "Done"
