#!/usr/bin/env python3
"""
io_utils.py
Funzioni di I/O sicuro (esteso con helper opzionali per JSON).
"""

import os
import tempfile
import hashlib
from pathlib import Path
from typing import Union
import json

PathLike = Union[str, Path]


def ensure_dir(path: PathLike) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def read_utf8(path: PathLike) -> str:
    p = Path(path)
    with p.open("rb") as f:
        data = f.read()
    return data.decode("utf-8")


def write_atomic(path: Path, data: Union[str, bytes]) -> None:
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
                pass
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def sha256_file(path: PathLike) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# Minimal helper: scrive JSON in modo atomico (utile per manifest)
def write_json_atomic(path: Path, obj: object, **json_kwargs) -> None:
    """
    Serializza obj in JSON e lo scrive in modo atomico.
    Usa write_atomic internamente.
    """
    data = json.dumps(obj, ensure_ascii=False, **json_kwargs)
    write_atomic(path, data)
