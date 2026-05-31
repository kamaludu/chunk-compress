#!/usr/bin/env python3
"""
cli.py
Orchestratore della pipeline:
- parsing argomenti
- validazione input
- chiamate a core.py
- stampa report
"""

import argparse
import sys
from pathlib import Path
import core
import io_utils


def parse_args():
    p = argparse.ArgumentParser(description="Local reversible compressor (LLM-ready)")
    p.add_argument("--input", "-i", required=True, help="Directory o file-lista")
    p.add_argument("--output", "-o", default="compressed_output", help="Directory output")
    p.add_argument("--L_min", type=int, default=64)
    p.add_argument("--N_min", type=int, default=2)
    p.add_argument("--B_min_lines", type=int, default=5)
    p.add_argument("--B_max_lines", type=int, default=20)
    p.add_argument("--verify-roundtrip", action="store_true")
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

        # 4) select
        replacements = core.select_replacements(candidates)

        # 5) apply
        llm_ready, reverse_map = core.apply_placeholders(contents, replacements)

        # 6) write outputs
        _write_outputs(llm_ready, reverse_map, output_dir, input_path)

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
        except ValueError:
            # fallback: usa solo il nome file
            rel = abs_p.name

        out_path = output_dir / rel
        io_utils.ensure_dir(out_path.parent)
        io_utils.write_atomic(out_path, text)

    io_utils.write_atomic(output_dir / "reverse_map.json",
                          json.dumps(reverse_map, ensure_ascii=False, indent=2))


def _print_report(stats, replacements):
    print("\n=== REPORT ===")
    print(f"Original chars: {stats['orig_total']}")
    print(f"Compressed chars: {stats['new_total']}")
    print(f"Saved chars: {stats['saved_chars']} ({stats['saved_pct']}%)")
    print(f"Placeholders: {len(replacements)}")
    print("==============\n")


if __name__ == "__main__":
    main()
