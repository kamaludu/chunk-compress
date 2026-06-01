#!/usr/bin/env python3
"""
core.py
Pipeline minima:
- scan_files
- load_contents
- find_repetitions (substring + blocchi)
- select_replacements
- apply_placeholders
- extract_mapping_for_files (estrazione LLM-ready o subset per export)
- roundtrip_check
- estimate_savings

Modifiche principali:
- extract_mapping_for_files ora accetta percorsi relativi o nomi file e
  restituisce un dizionario pid -> info (senza risolvere a path assoluti).
  Questo rende l'export LLM-ready semplice da costruire in cli.py.
"""

from pathlib import Path
import hashlib
from typing import Dict, List, Tuple, Any, Optional

import io_utils

# -------------------------
# Types (solo documentativi)
# -------------------------
# FileMeta: {"path": str, "size": int, "sha256": str}
# Candidate: {"id_hash": str, "type": "substring"|"block", "content": str,
#             "occurrences": [{"path": str, "start": int, "end": int}]}
# Replacement: {"id": str, "type": str, "placeholder": str, "content": str,
#               "occurrences": [{"path": str, "start": int, "end": int}]}


# -------------------------
# Scansione e caricamento
# -------------------------
def scan_files(input_path: str) -> List[Dict[str, Any]]:
    p = Path(input_path)
    files: List[Path] = []
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file():
                files.append(f)
    elif p.is_file():
        # input è un singolo file: processalo direttamente
        files.append(p)
    else:
        # file-lista: ogni riga è un percorso a file
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                fp = Path(line)
                if fp.is_file():
                    files.append(fp)

    metas: List[Dict[str, Any]] = []
    for f in files:
        try:
            sha = io_utils.sha256_file(f)
        except Exception:
            continue
        metas.append(
            {
                "path": str(f.resolve()),
                "size": f.stat().st_size,
                "sha256": sha,
            }
        )
    if not metas:
        raise RuntimeError("No valid files found in input")
    return metas


def load_contents(file_metas: List[Dict[str, Any]]) -> Dict[str, str]:
    contents: Dict[str, str] = {}
    for meta in file_metas:
        path = meta["path"]
        try:
            text = io_utils.read_utf8(path)
        except Exception:
            # file problematico: lo saltiamo, ma manteniamo manifest
            continue
        contents[path] = text
    return contents


# -------------------------
# Analisi ripetizioni
# -------------------------
def find_repetitions(
    contents: Dict[str, str],
    L_min: int,
    N_min: int,
    B_min_lines: int,
    B_max_lines: int,
    L_max: int = 2000,
) -> List[Dict[str, Any]]:
    substring_candidates = _find_substring_candidates(contents, L_min, N_min, L_max)
    block_candidates = _find_block_candidates(contents, B_min_lines, B_max_lines)
    candidates: List[Dict[str, Any]] = []
    candidates.extend(substring_candidates)
    candidates.extend(block_candidates)
    return candidates


def _find_substring_candidates(
    contents: Dict[str, str], L_min: int, N_min: int, L_max: int
) -> List[Dict[str, Any]]:
    # Rolling hash su finestre L_min
    base = 257
    mod = 2**61 - 1

    def roll_hash_init(s: str) -> Tuple[int, int]:
        h = 0
        power = 1
        for ch in s:
            h = (h * base + ord(ch)) % mod
            power = (power * base) % mod
        return h, power

    def roll_hash_next(h: int, power: int, left: str, right: str) -> int:
        h = (h * base - ord(left) * power + ord(right)) % mod
        return h

    index: Dict[int, List[Tuple[str, int]]] = {}
    for path, text in contents.items():
        n = len(text)
        if n < L_min:
            continue
        window = text[0:L_min]
        h, power = roll_hash_init(window)
        index.setdefault(h, []).append((path, 0))
        for i in range(1, n - L_min + 1):
            h = roll_hash_next(h, power, text[i - 1], text[i + L_min - 1])
            index.setdefault(h, []).append((path, i))

    candidates: Dict[str, Dict[str, Any]] = {}
    for h, occs in index.items():
        if len(occs) < N_min:
            continue
        # gruppo di occorrenze con stesso hash di finestra L_min
        # scegliamo la prima come seed
        seed_path, seed_start = occs[0]
        seed_text = contents[seed_path]

        # estensione greedy limitata da L_max
        extended_occurrences: List[Tuple[str, int, int]] = []
        for path, start in occs:
            t = contents[path]
            a = start
            b = start + L_min
            # estendi a sinistra
            while a > 0 and (seed_start > 0) and (start - a) < (seed_start) and (seed_start - (start - a)) > 0:
                if t[a - 1] != seed_text[seed_start - (start - a)]:
                    break
                if (b - (a - 1)) > L_max:
                    break
                a -= 1
            # estendi a destra
            while b < len(t) and (seed_start + (b - start)) < len(seed_text):
                if t[b] != seed_text[seed_start + (b - start)]:
                    break
                if (b + 1 - a) > L_max:
                    break
                b += 1
            extended_occurrences.append((path, a, b))

        if len(extended_occurrences) < N_min:
            continue
        # per semplicità, usiamo l'intervallo della seed
        seed_a, seed_b = extended_occurrences[0][1], extended_occurrences[0][2]
        content = seed_text[seed_a:seed_b]
        if len(content) < L_min:
            continue
        id_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        cand = candidates.setdefault(
            id_hash,
            {"id_hash": id_hash, "type": "substring", "content": content, "occurrences": []},
        )
        for path, a, b in extended_occurrences:
            cand["occurrences"].append({"path": path, "start": a, "end": b})

    # filtra candidati con occorrenze reali >= N_min
    result: List[Dict[str, Any]] = []
    for c in candidates.values():
        if len(c["occurrences"]) >= N_min:
            result.append(c)
    return result


def _find_block_candidates(
    contents: Dict[str, str], B_min_lines: int, B_max_lines: int
) -> List[Dict[str, Any]]:
    # usiamo poche dimensioni fisse per evitare esplosione
    sizes: List[int] = []
    if B_min_lines <= B_max_lines:
        sizes = [B_min_lines]
        mid = (B_min_lines + B_max_lines) // 2
        if mid != B_min_lines and mid <= B_max_lines:
            sizes.append(mid)
        if B_max_lines not in sizes:
            sizes.append(B_max_lines)
    sizes = sorted(set(sizes))

    index: Dict[str, List[Tuple[str, int, int, str]]] = {}
    for path, text in contents.items():
        lines = text.splitlines(keepends=True)
        L = len(lines)
        for size in sizes:
            if size <= 0 or size > L:
                continue
            for i in range(0, L - size + 1):
                block = "".join(lines[i : i + size])
                h = hashlib.sha256(block.encode("utf-8")).hexdigest()
                index.setdefault(h, []).append((path, i, size, block))

    candidates: List[Dict[str, Any]] = []
    for h, occs in index.items():
        if len(occs) < 2:
            continue
        # canonical block = primo
        _, line_idx, size, block = occs[0]
        content = block
        id_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        cand = {"id_hash": id_hash, "type": "block", "content": content, "occurrences": []}
        for path, li, sz, blk in occs:
            text = contents[path]
            start = _line_index_to_char_offset(text, li)
            end = start + len(blk)
            cand["occurrences"].append({"path": path, "start": start, "end": end})
        candidates.append(cand)
    return candidates


def _line_index_to_char_offset(text: str, line_index: int) -> int:
    if line_index <= 0:
        return 0
    lines = text.splitlines(keepends=True)
    return sum(len(lines[i]) for i in range(0, min(line_index, len(lines))))


# -------------------------
# Selezione sostituzioni
# -------------------------
def select_replacements(
    candidates: List[Dict[str, Any]],
    placeholder_fmt_sub: str = "<<S:{:03d}>>",
    placeholder_fmt_blk: str = "<<B:{:03d}>>",
    min_total_saving: int = 100,
) -> List[Dict[str, Any]]:
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for c in candidates:
        content = c["content"]
        occs = c["occurrences"]
        if len(occs) < 2:
            continue
        if c["type"] == "substring":
            ph_len = len(placeholder_fmt_sub.format(1))
        else:
            ph_len = len(placeholder_fmt_blk.format(1))
        saving_per_occ = max(0, len(content) - ph_len)
        total_saving = saving_per_occ * (len(occs) - 1)
        if total_saving >= min_total_saving:
            scored.append((total_saving, c))

    # ordina per risparmio desc, poi lunghezza contenuto desc, poi id_hash
    scored.sort(key=lambda x: (-x[0], -len(x[1]["content"]), x[1]["id_hash"]))

    occupied: Dict[str, List[Tuple[int, int]]] = {}
    replacements: List[Dict[str, Any]] = []
    sid = 1
    bid = 1

    for total_saving, c in scored:
        occs = c["occurrences"]
        # verifica sovrapposizioni
        conflict = False
        for o in occs:
            path = o["path"]
            s = o["start"]
            e = o["end"]
            for (a, b) in occupied.get(path, []):
                if not (e <= a or s >= b):
                    conflict = True
                    break
            if conflict:
                break
        if conflict:
            continue

        if c["type"] == "substring":
            pid = f"S:{sid:03d}"
            placeholder = placeholder_fmt_sub.format(sid)
            sid += 1
        else:
            pid = f"B:{bid:03d}"
            placeholder = placeholder_fmt_blk.format(bid)
            bid += 1

        rep = {
            "id": pid,
            "type": c["type"],
            "placeholder": placeholder,
            "content": c["content"],
            "occurrences": occs,
        }
        replacements.append(rep)
        for o in occs:
            path = o["path"]
            occupied.setdefault(path, []).append((o["start"], o["end"]))

    # normalizza intervalli occupati
    for path in occupied:
        occupied[path].sort()
    return replacements


# -------------------------
# Applicazione placeholder
# -------------------------
def apply_placeholders(
    contents: Dict[str, str], replacements: List[Dict[str, Any]]
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    per_file: Dict[str, List[Dict[str, Any]]] = {}
    for r in replacements:
        for o in r["occurrences"]:
            per_file.setdefault(o["path"], []).append(
                {
                    "start": o["start"],
                    "end": o["end"],
                    "id": r["id"],
                    "placeholder": r["placeholder"],
                    "content": r["content"],
                    "type": r["type"],
                }
            )

    llm_ready: Dict[str, str] = {}
    reverse_map: Dict[str, Any] = {
        "placeholders": {},
        "metadata": {"tool": "simple_local_compressor"},
    }

    for path, text in contents.items():
        repls = per_file.get(path, [])
        if not repls:
            llm_ready[path] = text
            continue
        repls.sort(key=lambda x: x["start"])
        out_parts: List[str] = []
        last = 0
        for r in repls:
            s = r["start"]
            e = r["end"]
            if s < last:
                # sovrapposizione inattesa, salta
                continue
            out_parts.append(text[last:s])
            out_parts.append(r["placeholder"])
            last = e
            pid = r["id"]
            entry = reverse_map["placeholders"].setdefault(
                pid,
                {
                    "type": r["type"],
                    "content": r["content"],
                    "sha256": hashlib.sha256(r["content"].encode("utf-8")).hexdigest(),
                    "length": len(r["content"]),
                    "occurrences": [],
                    "token": r["placeholder"],
                },
            )
            entry["occurrences"].append({"path": path, "start": s, "end": e})
        out_parts.append(text[last:])
        llm_ready[path] = "".join(out_parts)

    return llm_ready, reverse_map


def extract_mapping_for_files(reverse_map: dict, paths: list) -> dict:
    """
    Restituisce un dizionario pid -> info contenente solo i placeholder
    che hanno almeno un'occurrence in uno dei path indicati.

    Parametri:
      - reverse_map: dizionario completo come caricato da reverse_map.json
      - paths: lista di path (relativi o nomi file) dei file di output per i quali
               vogliamo estrarre i placeholder.

    Confronti effettuati:
      - confronto su basename (Path.name)
      - confronto su suffix (occ_path.endswith(provided_path)) per supportare percorsi relativi
    """
    from pathlib import Path

    # Normalizza i path forniti dall'utente: manteniamo i valori così come sono (non risolviamo)
    norm = [p.strip() for p in paths if p and p.strip()]
    norm_set = set(norm)
    norm_names = {Path(p).name for p in norm_set}

    out: Dict[str, Any] = {}
    placeholders = reverse_map.get("placeholders", {})
    for pid, info in placeholders.items():
        occs = info.get("occurrences", [])
        for occ in occs:
            occ_path = occ.get("path")
            if not occ_path:
                continue
            occ_name = Path(occ_path).name
            matched = False
            # match by basename
            if occ_name in norm_names:
                matched = True
            else:
                # match by suffix: supporta percorsi relativi forniti come "dir/file" o "file"
                for p in norm:
                    if occ_path.endswith(p):
                        matched = True
                        break
            if matched:
                out[pid] = info
                break
    return out


# -------------------------
# Roundtrip check
# -------------------------
def roundtrip_check(
    file_metas: List[Dict[str, Any]],
    llm_ready: Dict[str, str],
    reverse_map: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    meta_by_path = {m["path"]: m for m in file_metas}
    placeholders = reverse_map.get("placeholders", {})
    details: List[str] = []
    ok_all = True

    for path, meta in meta_by_path.items():
        original_sha = meta["sha256"]
        transformed = llm_ready.get(path)
        if transformed is None:
            # file non trasformato: ricontrolla sha originale
            cur_sha = io_utils.sha256_file(path)
            if cur_sha != original_sha:
                ok_all = False
                details.append(f"Original file changed unexpectedly: {path}")
            continue

        # ricostruzione basata su sostituzione globale dei placeholder
        recon = transformed
        # sostituiamo usando i placeholder registrati in reverse_map
        # notare: reverse_map usa pid come chiave (es. "S:001") e contiene "content"
        # i placeholder effettivi nel testo sono quelli generati da select_replacements (es. "<<s001>>")
        # per semplicità qui proviamo a sostituire ogni placeholder token presente nella mappa:
        for pid, info in placeholders.items():
            # cerchiamo il token effettivo nel testo: proviamo diverse forme comuni
            token_candidates = []
            # forma con pid diretto
            token_candidates.append(f"<<{pid}>>")
            # forma senza due punti (S001) e con lettere minuscole/maiuscole
            token_candidates.append(f"<<{pid.replace(':','')}>>")
            token_candidates.append(f"<<{pid.replace(':','').lower()}>>")
            token_candidates.append(f"<<{pid.replace(':','').upper()}>>")
            for token in token_candidates:
                if token in recon:
                    recon = recon.replace(token, info["content"])

        recon_sha = io_utils.sha256_text(recon)
        if recon_sha != original_sha:
            ok_all = False
            details.append(
                f"Mismatch for {path}: original {original_sha} != reconstructed {recon_sha}"
            )

    return ok_all, details

# -------------------------
# Manifest
# -------------------------
def build_manifest(file_metas: List[Dict[str, Any]], reverse_map: Dict[str, Any], input_root: str) -> Dict[str, Any]:
    """
    Costruisce il manifest compatto:
    {
      "paths": [...],
      "files": [{"i":idx,"sha":sha,"ph":[...]}...],
      "ph": {"S:001":{"sha":"...","len":120}, ...},
      "v":1
    }
    - file_metas: output di scan_files()
    - reverse_map: struttura completa da apply_placeholders()
    - input_root: path usato come root per rendere i path relativi
    """
    from pathlib import Path

    root = Path(input_root)
    # ordina file_metas per path per stabilità
    metas_sorted = sorted(file_metas, key=lambda m: m["path"])
    paths: List[str] = []
    files: List[Dict[str, Any]] = []
    path_to_idx: Dict[str, int] = {}

    for idx, m in enumerate(metas_sorted):
        # path relativo rispetto a root; se non sotto root, usa basename
        try:
            rel = Path(m["path"]).relative_to(root)
            p = str(rel).replace("\\", "/")
        except Exception:
            p = Path(m["path"]).name
        paths.append(p)
        path_to_idx[m["path"]] = idx
        files.append({"i": idx, "sha": m.get("sha256", ""), "ph": []})

    # placeholders index: minimal metadata
    ph_index: Dict[str, Dict[str, Any]] = {}
    placeholders = reverse_map.get("placeholders", {})
    for pid, info in placeholders.items():
        ph_index[pid] = {"sha": info.get("sha256", ""), "len": info.get("length", 0)}

        # per ogni occurrence, aggiungi il pid alla entry file corrispondente
        for occ in info.get("occurrences", []):
            occ_path = occ.get("path")
            if occ_path in path_to_idx:
                idx = path_to_idx[occ_path]
                if pid not in files[idx]["ph"]:
                    files[idx]["ph"].append(pid)
            else:
                # tentativo di match su basename se path assoluto differente
                for m in metas_sorted:
                    if Path(m["path"]).name == Path(occ_path).name:
                        idx = path_to_idx[m["path"]]
                        if pid not in files[idx]["ph"]:
                            files[idx]["ph"].append(pid)
                        break

    manifest = {"paths": paths, "files": files, "ph": ph_index, "v": 1}
    return manifest

# -------------------------
# Chunks 
# -------------------------
def chunk_outputs(
    llm_ready: Dict[str, str],
    output_dir: Path,
    chunk_size: int,
    input_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Divide i testi compressi (llm_ready: abs_path -> contenuto) in chunk testuali.
    Scrive i chunk in OUT_DIR/chunks/<relative_path>/0001.txt ...
    Restituisce un manifest strutturato come richiesto:
    {
      "files": {
        "<relative_path>": {
          "chunks": ["chunks/<rel_path>/0001.txt", ...],
          "sha256_full": "<sha256_del_file_compresso_intero>",
          "chunk_size": <chunk_size_usato>,
          "total_len": <len_caratteri_file_compresso>
        }, ...
      },
      "v": 1
    }
    - input_root: Path usato per calcolare path relativi; se None, si usa basename.
    """
    out_manifest: Dict[str, Any] = {"files": {}, "v": 1}
    chunks_root = Path(output_dir) / "chunks"
    io_utils.ensure_dir(chunks_root)

    for abs_path, text in llm_ready.items():
        abs_p = Path(abs_path)
        # calcola path relativo rispetto a input_root se fornito
        if input_root:
            try:
                rel = abs_p.relative_to(input_root)
                rel_path = rel.as_posix()
            except Exception:
                rel_path = abs_p.name
        else:
            rel_path = abs_p.name

        # directory per i chunk: chunks/<rel_path> (sostituiamo separatori con '/')
        chunk_dir = chunks_root / Path(rel_path)
        io_utils.ensure_dir(chunk_dir)

        total_len = len(text)
        sha_full = io_utils.sha256_text(text)
        chunks_list: List[str] = []

        if total_len == 0:
            # scrivi un chunk vuoto per consistenza
            chunk_name = f"{1:04d}.txt"
            chunk_path = chunk_dir / chunk_name
            io_utils.write_atomic(chunk_path, "")
            chunks_list.append(str(Path("chunks") / Path(rel_path) / chunk_name).replace("\\", "/"))
        else:
            # suddividi in chunk di dimensione chunk_size (caratteri)
            idx = 1
            start = 0
            while start < total_len:
                end = min(start + chunk_size, total_len)
                part = text[start:end]
                chunk_name = f"{idx:04d}.txt"
                chunk_path = chunk_dir / chunk_name
                io_utils.write_atomic(chunk_path, part)
                chunks_list.append(str(Path("chunks") / Path(rel_path) / chunk_name).replace("\\", "/"))
                idx += 1
                start = end

        out_manifest["files"][rel_path] = {
            "chunks": chunks_list,
            "sha256_full": sha_full,
            "chunk_size": chunk_size,
            "total_len": total_len,
        }

    return out_manifest
  
# -------------------------
# Stima risparmio
# -------------------------
def estimate_savings(
    original_contents: Dict[str, str], llm_ready: Dict[str, str]
) -> Dict[str, Any]:
    orig_total = sum(len(v) for v in original_contents.values())
    new_total = sum(len(v) for v in llm_ready.values())
    saved_chars = orig_total - new_total
    saved_pct = (saved_chars / orig_total * 100.0) if orig_total > 0 else 0.0
    return {
        "orig_total": orig_total,
        "new_total": new_total,
        "saved_chars": saved_chars,
        "saved_pct": round(saved_pct, 2),
    }
