#!/usr/bin/env python3
# eseguito da: build_dict.sh
import json,glob,os
def key(i): return f"S{i}"
items=[]
for p in sorted(glob.glob('dict/*.txt')):
    with open(p,'r',encoding='utf-8',errors='ignore') as f:
        for l in f:
            s=l.strip()
            if s and s not in items:
                items.append(s)
D={key(i+1):items[i] for i in range(len(items))}
os.makedirs('dict',exist_ok=True)
with open('dict/global.json','w',encoding='utf-8') as o:
    json.dump({"d":D}, o, separators=(',',':'), ensure_ascii=False)
print(len(D))
