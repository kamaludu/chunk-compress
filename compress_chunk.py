#!/usr/bin/env python3
import json,glob,re,hashlib,os,sys
os.makedirs('out',exist_ok=True)
D=json.load(open('dict/global.json'))['d'] if os.path.exists('dict/global.json') else {}
inv={v:k for k,v in D.items()}
def repl(s):
    for orig,short in inv.items():
        s=s.replace(orig, short)
    return s
def summ(txt):
    for l in txt.splitlines():
        if l.strip():
            return l.strip()[:200]
    return ""
out=[]
for p in sorted(glob.glob('chunks/*')):
    txt=open(p,'r',encoding='utf-8',errors='ignore').read()
    body=repl(txt)
    h=hashlib.sha1(body.encode()).hexdigest()
    se=[]
    if re.search(r'\b(eval|exec|system|curl|wget|scp|ssh)\b', txt): se.append('exec')
    if re.search(r'(\>\s|>>|tee\b|mv\b|cp\b|install\b)', txt): se.append('fs')
    if re.search(r'\bflock\b|\blockfile\b', txt): se.append('lock')
    typ='sh' if p.endswith('.sh') or '.sh.' in p else ('tpl' if '.html.' in p else 'css')
    rec={"f":os.path.basename(p),"t":typ,"s":summ(txt),"a":[],"v":[],"e":se,"b":h}
    out.append(rec)
    open(os.path.join('out',f'body.{h}.tok'),'w',encoding='utf-8').write(body)
with open('out/pack.jsonl','w',encoding='utf-8') as o:
    for r in out: o.write(json.dumps(r,separators=(',',':'),ensure_ascii=False)+"\n")
print("Wrote",len(out),"records")
