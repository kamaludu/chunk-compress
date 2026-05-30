#!/usr/bin/env python3
# Eseguito da: build_dict.sh
import json, glob, os, sys, tempfile, shutil

# Accetta SRC per coerenza pipeline (opzionale, non usato internamente)
SRC = os.environ.get("SRC") or (sys.argv[1] if len(sys.argv) > 1 else None)

os.makedirs('dict', exist_ok=True)

items = []
seen = set()

for p in sorted(glob.glob('dict/*.txt')):
    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as fh:
            for l in fh:
                s = l.strip()
                if s and s not in seen:
                    seen.add(s)
                    items.append(s)
    except Exception:
        continue

def key(i): return f"S{i}"

D = {key(i+1): items[i] for i in range(len(items))}

# scrittura atomica del file globale
tmpfd, tmppath = tempfile.mkstemp(dir='dict', prefix='global.', suffix='.json')
with os.fdopen(tmpfd, 'w', encoding='utf-8') as o:
    json.dump({"d": D}, o, separators=(',', ':'), ensure_ascii=False)
shutil.move(tmppath, 'dict/global.json')

print(len(D))
