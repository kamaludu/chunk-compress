#!/usr/bin/env python3
"""
io_utils.py
Funzioni di I/O sicuro:
- lettura UTF-8
- scrittura atomica
- hashing
- gestione directory
"""

import os
import tempfile
import hashlib
from pathlib import Path


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def read_utf8(path: str) -> str:
    p = Path(path)
    with p.open("rb") as f:
        data = f.read()
    # decodifica strict: se fallisce, solleva eccezione
    return data.decode("utf-8")


def write_atomic(path: Path, data):
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            if isinstance(data, str):
                f.write(data.encode("utf-8"))
            else:
                f.write(data)
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
