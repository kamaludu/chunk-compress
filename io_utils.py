#!/usr/bin/env python3
"""
Compressore locale LLM‑ready
File: io_utils.py
Copyright (C) 2026 Cristian Evangelisti
License: GPL-3.0-or-later
SPDX-License-Identifier: GPL-3.0-or-later
Source: https://github.com/kamaludu/chunk-compress

Descrizione:
Funzioni di I/O sicuro (esteso con helper opzionali per JSON).
"""

import os
import tempfile
import hashlib
from pathlib import Path
from typing import Union, Optional
import json

PathLike = Union[str, Path]


def ensure_dir(path: PathLike) -> None:
    """
    Crea la directory (ricorsiva) se non esiste.
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def read_bytes(path: PathLike) -> bytes:
    """
    Legge e restituisce i bytes del file.
    """
    p = Path(path)
    with p.open("rb") as f:
        return f.read()


def read_text(path: PathLike, encoding: str = "utf-8", errors: str = "strict") -> str:
    """
    Legge un file come testo (UTF-8 di default).
    errors può essere 'strict'|'replace'|'ignore' a seconda delle esigenze.
    """
    p = Path(path)
    with p.open("r", encoding=encoding, errors=errors) as f:
        return f.read()


# backward-compatible alias
def read_utf8(path: PathLike) -> str:
    return read_text(path, encoding="utf-8", errors="strict")


def safe_remove(path: PathLike) -> None:
    """
    Rimuove un file se esiste; ignora errori.
    """
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
    except Exception:
        pass


def write_atomic(path: PathLike, data: Union[str, bytes], encoding: str = "utf-8") -> None:
    """
    Scrive data in modo atomico su 'path'.
    - Se data è str, viene codificato con 'encoding'.
    - Usa tempfile.mkstemp nella stessa directory per garantire atomicità con os.replace.
    - Sincronizza il file su disco quando possibile.
    """
    p = Path(path)
    ensure_dir(p.parent)

    fd = None
    tmp_path = None
    try:
        # mkstemp crea un file descriptor aperto; lo useremo per scrivere bytes
        fd, tmp_path = tempfile.mkstemp(prefix=p.name + ".", dir=str(p.parent))
        # apri il fd come file binario
        with os.fdopen(fd, "wb") as f:
            if isinstance(data, str):
                b = data.encode(encoding)
            else:
                b = data
            f.write(b)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                # fsync può fallire su alcuni FS (es. tmpfs) — non fatale
                pass
        # sostituisci in modo atomico
        os.replace(tmp_path, str(p))
        tmp_path = None
    finally:
        # cleanup se qualcosa è andato storto
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def sha256_file(path: PathLike) -> str:
    """
    Calcola SHA256 di un file (bytes).
    """
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str, encoding: str = "utf-8") -> str:
    """
    Calcola SHA256 di una stringa (codificata in UTF-8 di default).
    """
    return hashlib.sha256(s.encode(encoding)).hexdigest()


def write_json_atomic(path: PathLike, obj: object, **json_kwargs) -> None:
    """
    Serializza obj in JSON e lo scrive in modo atomico.
    Usa write_atomic internamente.
    json_kwargs vengono passati a json.dumps (indent, separators, ensure_ascii, ecc.).
    """
    # default: indent=2 per leggibilità, ensure_ascii=False per UTF-8
    kwargs = {"ensure_ascii": False, "indent": 2}
    kwargs.update(json_kwargs)
    data = json.dumps(obj, **kwargs)
    write_atomic(path, data, encoding="utf-8")
