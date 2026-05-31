#!/usr/bin/env python3
"""
cli.py
Orchestratore della pipeline:
- parsing argomenti
- validazione input
- chiamate a core.py
- stampa report

- export mapping_subset.json in formato LLM-ready (solo placeholder -> {content, sha256, length})
- export manifest compatto (paths/files/ph/v)
- quando si costruisce la lista di file per l'export non si usa .resolve() (evita path assoluti)
- comportamento LLM-ready di default per mapping_subset.json quando si usa --export-mapping-for
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
        "--export-mapping-for",
        help="Comma-separated list di nomi file (relativi a OUTPUT) per cui esportare il mapping ridotto (scrive mapping_subset.json in output dir)",
        default="",
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
        default="<<s{:03d}>>",
        help="Formato placeholder per substring (es. '<<s{:03d}>>')",
    )
    p.add_argument(
        "--placeholder-blk",
        default="<<b{:03d}>>",
        help="Formato placeholder per block (es. '<<b{:03d}>>')",
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
        file_metas = core.scan_files(str(input_path))

        # 2) load
        contents = core.load_contents(file_metas)

        # 3) analyze
        candidates = core.find_repetitions(
            contents,
            L_min=args.L_min,
            N_min=args.N_min,
            B_min_lines=args.B_min_lines,
            B_max_lines=args.B_max_lines,
        )

        # 4) select (passiamo soglia e formati placeholder)
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

        # 6b) export reduced mapping per file (LLM-ready) -- comportamento di default quando richiesto
        if getattr(args, "export_mapping_for", ""):
            files = [s.strip() for s in args.export_mapping_for.split(",") if s.strip()]
            if files:
                # costruiamo una lista di riferimenti ai file senza risolvere a path assoluti
                # includiamo sia il percorso relativo rispetto a output_dir sia rispetto a input_path
                ref_files = []
                for f in files:
                    try:
                        # riferimento relativo in output (come apparirà nei file compressi)
                        ref_files.append(str(Path(f).as_posix()))
                    except Exception:
                        pass
                    try:
                        # riferimento relativo rispetto all'input root (se il file esiste lì)
                        ref_files.append(str((Path(f)).as_posix()))
                    except Exception:
                        pass

                # deduplica mantenendo ordine
                ref_files = list(dict.fromkeys(ref_files))

                # chiediamo a core di estrarre il subset; ci aspettiamo un dict placeholder -> entry
                subset = core.extract_mapping_for_files(reverse_map, ref_files)

                # costruiamo la versione LLM-ready: solo placeholder -> {content, sha256, length}
                llm_subset = {"placeholders": {}}
                for ph, entry in (subset or {}).items():
                    # entry potrebbe essere una struttura complessa; estraiamo i campi utili
                    content = entry.get("content") if isinstance(entry, dict) else None
                    if content is None:
                        # se entry è una lista di occorrenze, recuperiamo il contenuto dal reverse_map principale
                        rm_entry = reverse_map.get("placeholders", {}).get(ph) if isinstance(reverse_map, dict) else None
                        if isinstance(rm_entry, dict):
                            content = rm_entry.get("content")
                    if content is None:
                        # skip se non troviamo contenuto
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

        # 7) roundtrip
        if args.verify_roundtrip:
            ok, details = core.roundtrip_check(file_metas, llm_ready, reverse_map)
            if not ok:
                print("Roundtrip FAILED:", file=sys.stderr)
                for d in details:
                    print(" -", d, file=sys.stderr)
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
    """
    for abs_path, text in llm_ready.items():
        abs_p = Path(abs_path)
        try:
            rel = abs_p.relative_to(input_root)
        except Exception:
            # se non è sotto input_root, usiamo il nome file o il percorso relativo fornito
            rel = Path(abs_p.name)

        out_path = output_dir / rel
        io_utils.ensure_dir(out_path.parent)
        io_utils.write_atomic(out_path, text)

    # scriviamo la reverse_map completa (solo locale, utile per ricostruzione e debug)
    io_utils.write_atomic(
        output_dir / "reverse_map.json",
        json.dumps(reverse_map, ensure_ascii=False, indent=2),
    )


def _print_report(stats, replacements):
    print("\n=== REPORT ===")
    print(f"Original chars: {stats['orig_total']}")
    print(f"Compressed chars: {stats['new_total']}")
    print(f"Saved chars: {stats['saved_chars']} ({stats['saved_pct']}%)")
    print(f"Placeholders: {len(replacements)}")
    print("==============\n")


if __name__ == "__main__":
    main()
