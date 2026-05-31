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
from typing import Union


PathLike = Union[str, Path]


def ensure_dir(path: PathLike) -> None:
    """
    Crea la directory (e i genitori) se non esistono.
    Accetta str o Path.
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def read_utf8(path: PathLike) -> str:
    """
    Legge un file come UTF-8; solleva eccezione se la decodifica fallisce.
    """
    p = Path(path)
    with p.open("rb") as f:
        data = f.read()
    return data.decode("utf-8")


def write_atomic(path: Path, data: Union[str, bytes]) -> None:
    """
    Scrive in modo atomico: scrive su file temporaneo nella stessa directory,
    fsynca e poi sostituisce il file di destinazione.
    """
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            if isinstance(data, str):
                b = data.encode("utf-8")
            else:
                b = data
            f.write(b)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                # fsync può fallire su alcuni filesystem (es. in-memory); ignoriamo l'errore non critico
                pass
        os.replace(tmp, str(path))
    finally:
        # nel caso os.replace lanciasse, assicuriamoci di rimuovere il tmp residuo
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def sha256_file(path: PathLike) -> str:
    """
    Calcola sha256 di un file; accetta str o Path.
    """
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    """
    Calcola sha256 di una stringa (UTF-8).
    """
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
