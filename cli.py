#!/usr/bin/env python3
"""
cli.py
Orchestratore della pipeline (aggiornato con chunking opzionale).
"""

import argparse
import sys
import json
from pathlib import Path
import core
import io_utils


def parse_args():
    p = argparse.ArgumentParser(description="Local reversible compressor (LLM-ready)")
    p.add_argument("--input", "-i", required=True, help="Directory o file‑lista")
    p.add_argument("--output", "-o", default="compressed_output", help="Directory output")
    p.add_argument("--L_min", type=int, default=64)
    p.add_argument("--N_min", type=int, default=2)
    p.add_argument("--B_min_lines", type=int, default=5)
    p.add_argument("--B_max_lines", type=int, default=20)
    p.add_argument("--verify-roundtrip", action="store_true")
    p.add_argument(
        "--no-export-mapping",
        nargs="?",
        const="",
        help=(
            "Se presente, disabilita l'export completo di mapping_subset.json per default. "
            "Puoi passare una lista separata da virgole di file (relativi all'input) da ESCLUDERE "
            "dall'export. Se fornito senza valore, esclude tutti i file (nessun mapping_subset.json)."
        ),
    )
    p.add_argument(
        "--export-manifest",
        action="store_true",
        help="Esporta manifest.json compatto dei file processati (paths/files/ph/v)",
    )
    p.add_argument(
        "--min_total_saving",
        type=int,
        default=100,
        help="Soglia totale risparmio per accettare una sostituzione (passata a select_replacements)",
    )
    p.add_argument(
        "--placeholder-sub",
        default="§§s{:03d}§§",
        help="Formato placeholder per substring (es. '§§s{:03d}§§')",
    )
    p.add_argument(
        "--placeholder-blk",
        default="§§b{:03d}§§",
        help="Formato placeholder per block (es. '§§b{:03d}§§')",
    )
    # Chunking options (opzionali)
    p.add_argument(
        "--chunk-output",
        action="store_true",
        help="Opzionale: genera chunk dei file compressi in OUT_DIR/chunks/",
    )
    p.add_argument(
        "--chunk-size",
        type=int,
        default=16000,
        help="Dimensione massima (caratteri) per chunk quando --chunk-output è attivo (default 16000)",
    )
    p.add_argument(
        "--include-pointless",
        action="store_true",
        help="Se presente, NON esclude le estensioni binarie/inutili durante lo scan (default: escludi).",
    )
    return p.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input non valido: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    io_utils.ensure_dir(output_dir)

    try:
        # 1) scan
        # comportamento di default: escludi le estensioni binarie o inutili; se --include-pointless è passato, non escludere
        file_metas = core.scan_files(str(input_path), exclude_pointless=not getattr(args, "include_pointless", False))


        # 2) load
        contents = core.load_contents(file_metas)

        # 2b) Regola fissa applicata di default:
        # Mantieni le righe vuote solo per formati documentazione (.md, .txt, .rst, .html, .tex, .adoc, .org)
        # Rimuovile per tutti gli altri formati.
        if not hasattr(core, "strip_empty_lines_by_extension"):
            print("Errore: funzione 'strip_empty_lines_by_extension' non trovata in core.py", file=sys.stderr)
            sys.exit(1)
        try:
            contents = core.strip_empty_lines_by_extension(contents)
        except Exception as e:
            print(f"Errore durante l'applicazione di strip_empty_lines_by_extension: {e}", file=sys.stderr)
            sys.exit(1)

        # 3) analyze
        candidates = core.find_repetitions(
            contents,
            L_min=args.L_min,
            N_min=args.N_min,
            B_min_lines=args.B_min_lines,
            B_max_lines=args.B_max_lines,
        )

        # 4) select
        replacements = core.select_replacements(
            candidates,
            placeholder_fmt_sub=args.placeholder_sub,
            placeholder_fmt_blk=args.placeholder_blk,
            min_total_saving=args.min_total_saving,
        )

        # 5) apply
        llm_ready, reverse_map = core.apply_placeholders(contents, replacements)

        # 6) write outputs (transformed files + reverse_map completo)
        _write_outputs(llm_ready, reverse_map, output_dir, input_path)

        # 6b) export reduced mapping per file (LLM-ready)
        # New required behavior:
        # - Default: export mapping_subset.json for ALL files processed.
        # - If --no-export-mapping is provided without value -> exclude all (no export).
        # - If --no-export-mapping is provided with a comma-separated value -> treat that as list of files to EXCLUDE from export.
        files = []
        no_export_val = getattr(args, "no_export_mapping", None)
        if no_export_val is None:
            # default: include all processed files (relative paths)
            for m in file_metas:
                try:
                    rel = Path(m["path"]).relative_to(input_path).as_posix()
                except Exception:
                    rel = Path(m["path"]).name
                files.append(rel)
        else:
            # user requested exclusions
            if no_export_val == "":
                # provided without value -> exclude all (no export)
                files = []
            else:
                excludes = [s.strip() for s in str(no_export_val).split(",") if s.strip()]
                for m in file_metas:
                    try:
                        rel = Path(m["path"]).relative_to(input_path).as_posix()
                    except Exception:
                        rel = Path(m["path"]).name
                    if rel in excludes:
                        continue
                    files.append(rel)

        if files:
            ref_files = []
            for f in files:
                try:
                    ref_files.append(str(Path(f).as_posix()))
                except Exception:
                    pass
                try:
                    ref_files.append(str((Path(f)).as_posix()))
                except Exception:
                    pass
            ref_files = list(dict.fromkeys(ref_files))
            subset = core.extract_mapping_for_files(reverse_map, ref_files)
            llm_subset = {"placeholders": {}}
            for ph, entry in (subset or {}).items():
                content = entry.get("content") if isinstance(entry, dict) else None
                if content is None:
                    rm_entry = reverse_map.get("placeholders", {}).get(ph) if isinstance(reverse_map, dict) else None
                    if isinstance(rm_entry, dict):
                        content = rm_entry.get("content")
                if content is None:
                    continue
                sha = entry.get("sha256") if isinstance(entry, dict) else reverse_map.get("placeholders", {}).get(ph, {}).get("sha256", "")
                length = entry.get("length") if isinstance(entry, dict) else len(content)
                llm_subset["placeholders"][ph] = {
                    "content": content,
                    "sha256": sha or "",
                    "length": length or len(content),
                }

            io_utils.write_atomic(
                output_dir / "mapping_subset.json",
                json.dumps(llm_subset, ensure_ascii=False, indent=2),
            )

            print(f"Exported mapping_subset.json for {len(files)} file(s): {', '.join(files)}")

        # 6c) export manifest compatto se richiesto
        if getattr(args, "export_manifest", False):
            try:
                manifest = core.build_manifest(file_metas, reverse_map, str(input_path))
                io_utils.write_atomic(
                    output_dir / "manifest.json",
                    json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
                )
                print(f"Manifest scritto in: {output_dir / 'manifest.json'}")
            except Exception as e:
                print(f"Errore durante la generazione del manifest: {e}", file=sys.stderr)

        # 6d) optional: chunk outputs (DOPO la scrittura normale)
        if getattr(args, "chunk_output", False):
            try:
                chunks_manifest = core.chunk_outputs(llm_ready, output_dir, args.chunk_size, input_path)
                chunks_dir = output_dir / "chunks"
                io_utils.ensure_dir(chunks_dir)
                if isinstance(chunks_manifest, dict) and "chunks_dir" not in chunks_manifest:
                    chunks_manifest["chunks_dir"] = "chunks"
                io_utils.write_atomic(
                    chunks_dir / "manifest.json",
                    json.dumps(chunks_manifest, ensure_ascii=False, indent=2),
                )
                print(f"Chunks scritti in: {chunks_dir} (manifest.json incluso)")
            except Exception as e:
                print(f"Errore durante la generazione dei chunk: {e}", file=sys.stderr)

        # 7) roundtrip
        if args.verify_roundtrip:
            ok, details = core.roundtrip_check(file_metas, llm_ready, reverse_map)
            if not ok:
                print("Roundtrip FAILED:", file=sys.stderr)
                for d in details:
                    print(" -", d, file=sys.stderr)
                try:
                    io_utils.write_atomic(output_dir / "roundtrip_failures.json", json.dumps(details, ensure_ascii=False, indent=2))
                except Exception:
                    pass
                sys.exit(2)

        # 8) report
        stats = core.estimate_savings(contents, llm_ready)
        _print_report(stats, replacements)

        print(f"OK. Output in: {output_dir}")

    except Exception as e:
        print("Errore:", e, file=sys.stderr)
        sys.exit(1)


def _write_outputs(llm_ready, reverse_map, output_dir: Path, input_root: Path):
    """
    Scrive i file trasformati preservando la struttura relativa rispetto all'input.
    Raccoglie errori di scrittura e li solleva come RuntimeError se presenti.
    """
    errors = []
    for abs_path, text in llm_ready.items():
        abs_p = Path(abs_path)
        try:
            rel = abs_p.relative_to(input_root)
        except Exception:
            rel = Path(abs_p.name)

        out_path = output_dir / rel
        io_utils.ensure_dir(out_path.parent)
        try:
            io_utils.write_atomic(out_path, text)
        except Exception as e:
            errors.append((str(out_path), str(e)))

    try:
        io_utils.write_atomic(
            output_dir / "reverse_map.json",
            json.dumps(reverse_map, ensure_ascii=False, indent=2),
        )
    except Exception as e:
        errors.append((str(output_dir / "reverse_map.json"), str(e)))

    if errors:
        for p, err in errors:
            print(f"Errore scrittura {p}: {err}", file=sys.stderr)
        raise RuntimeError("Errori durante la scrittura degli output")


def _print_report(stats, replacements):
    print("\n=== REPORT ===")
    print(f"Original chars: {stats['orig_total']}")
    print(f"Compressed chars: {stats['new_total']}")
    print(f"Saved chars: {stats['saved_chars']} ({stats['saved_pct']}%)")
    print(f"Placeholders: {len(replacements)}")
    print("==============\n")


if __name__ == "__main__":
    main()
