#!/usr/bin/env python3
# Script 3 — compressione chunk → JSONL (richiede SRC come argomento)
import json, glob, re, hashlib, os, sys
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit("Usage: compress_chunk.py SRC")

SRC = sys.argv[1]  # richiesto per coerenza pipeline (non usato internamente)
CHUNKDIR = Path("chunks")
OUTDIR = Path("out")
DICTFILE = Path("dict/global.json")

OUTDIR.mkdir(exist_ok=True)

# carica dizionario se presente
D = {}
if DICTFILE.exists():
    with DICTFILE.open("r", encoding="utf-8") as fh:
        try:
            D = json.load(fh).get("d", {})
        except Exception:
            D = {}
inv = {v: k for k, v in D.items()}

def repl(s):
    # sostituzioni semplici; ordine non garantito ma sufficiente per token mapping
    for orig, short in inv.items():
        s = s.replace(orig, short)
    return s

def summ(txt):
    for l in txt.splitlines():
        if l.strip():
            return l.strip()[:200]
    return ""

out = []
paths = sorted([p for p in CHUNKDIR.glob("*") if p.is_file()])

for p in paths:
    txt = p.read_text(encoding="utf-8", errors="ignore")
    body = repl(txt)
    h = hashlib.sha1(body.encode("utf-8")).hexdigest()

    se = []
    if re.search(r'\b(eval|exec|system|curl|wget|scp|ssh)\b', txt):
        se.append("exec")
    if re.search(r'(\>\s|>>|tee\b|mv\b|cp\b|install\b)', txt):
        se.append("fs")
    if re.search(r'\bflock\b|\blockfile\b|\blockfile\b', txt) or re.search(r'\blockfile\b', txt):
        se.append("lock")
    # correggi possibile typo 'lockfile'
    if re.search(r'\blockfile\b', txt) or re.search(r'\blockfile\b', txt):
        if "lock" not in se:
            se.append("lock")

    name = p.name
    # tipo basato sul nome originale (es. base.sh.001.chunk)
    if ".sh" in name:
        typ = "sh"
    elif ".html" in name or ".htm" in name:
        typ = "tpl"
    elif ".css" in name:
        typ = "css"
    else:
        typ = "txt"

    rec = {
        "f": name,
        "t": typ,
        "s": summ(txt),
        "a": [],
        "v": [],
        "e": se,
        "b": h
    }
    out.append(rec)

    body_path = OUTDIR / f"body.{h}.tok"
    # scrivi solo se non esiste o sovrascrivi intenzionalmente
    body_path.write_text(body, encoding="utf-8")

with (OUTDIR / "pack.jsonl").open("w", encoding="utf-8") as o:
    for r in out:
        o.write(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n")

print("Wrote", len(out), "records")
