# Uso minimo del compressore locale LLM‑ready

Piccolo compressore reversibile per testo, pensato per LLM: placeholder + manifest + chunking + roundtrip verificabile.

---

**Clone locale:**
```sh
git clone --depth 1 --branch main https://github.com/kamaludu/chunk-compress.git chunk-compress
```
---

## 1. Struttura del progetto
Metti questi file nella stessa directory:

```
core.py
cli.py
io_utils.py
```

## 2. Requisiti
- Python 3.8+
- Nessuna libreria esterna
- Funziona su Linux, macOS, Termux/Android

## 3. Preparazione input
Puoi fornire:

### A) Una **directory**
Esempio:
```
/home/cristian/progetto/
```

### B) Una **file‑lista**
Un file di testo con un percorso per riga:
```
src/a.py
src/b.py
docs/readme.md
```

## 4. Esecuzione base
Comando:

```
python3 cli.py --input <percorso_input> --output out
```

Esempi:

```
python3 cli.py --input ./mio_codice --output ./out
```

oppure:

```
python3 cli.py --input filelist.txt --output ./out
```

## 5. Parametri utili
- `--L_min` lunghezza minima substring (default 64)
- `--N_min` occorrenze minime (default 2)
- `--B_min_lines` dimensione minima blocchi (default 5)
- `--B_max_lines` dimensione massima blocchi (default 20)
- `--verify-roundtrip` verifica integrità totale

Esempio completo:

```
python3 cli.py --input ./src --output ./out --L_min 80 --N_min 2 --verify-roundtrip
```

## 6. Output generati
Dentro la directory `out/` troverai:

### 1) **File compressi LLM‑ready**
Stessa struttura dei file originali, ma con placeholder tipo:
```
§§S:001§§
§§B:002§§
```

### 2) **reverse_map.json**
Contiene:
- mapping placeholder → contenuto originale
- posizioni originali
- metadati

Serve per ricostruire i file originali.

### 3) **Report**
Stampato a terminale:
- caratteri originali
- caratteri compressi
- risparmio %
- numero placeholder

## 7. Come usare gli output in una chat LLM
1. Apri `out/`  
2. Copia i file compressi (sono molto più piccoli)  
3. Incollali nella chat LLM  
4. Se il modello deve ricostruire parti originali, incolla anche `reverse_map.json`  
   (o solo le parti necessarie)

## 8. Flusso tipico
1. Metti i tuoi file in una directory  
2. Lancia il comando  
3. Ottieni file compressi  
4. Incolla in chat LLM  
5. Risparmi token e mantieni reversibilità totale

---

## Parametri CLI e descrizione
(ordinati alfabeticamente)

| **Flag** | **Tipo** | **Descrizione** | **Range / note** | **Esempio** |
|---|---:|---|---|---|
| **--B_max_lines** | intero | Numero massimo di righe per candidati block. | ≥ B_min_lines | `--B_max_lines 10` |
| **--B_min_lines** | intero | Numero minimo di righe per candidati block. | minimo 1 | `--B_min_lines 3` |
| **--chunk-output** | flag | Genera chunk dei file compressi in `OUT_DIR/chunks/`. | flag booleano | `--chunk-output` |
| **--chunk-size** | intero | Dimensione massima dei chunk in caratteri. | default 16000 | `--chunk-size 16000` |
| **--export-manifest** | flag | Genera `manifest.json` compatto (paths, files, ph, v). | flag booleano | `--export-manifest` |
| **--export-mapping-for** | stringa (lista) | Lista separata da virgole di file relativi a `--output` per cui esportare `mapping_subset.json`. | nomi o percorsi relativi | `--export-mapping-for INSTALL.md,header.html` |
| **--input, -i** | stringa | Directory o file‑lista da processare. | deve esistere | `--input ./project` |
| **--L_min** | intero | Lunghezza minima substring per rolling hash. | 4–2000; default 64 | `--L_min 24` |
| **--min_total_saving** | intero | Risparmio minimo richiesto per accettare una sostituzione. | minimo 0; default 100 | `--min_total_saving 20` |
| **--N_min** | intero | Occorrenze minime per considerare una substring candidata. | minimo 2 | `--N_min 2` |
| **--output, -o** | stringa | Directory di output. | creata se mancante | `--output ./out` |
| **--placeholder-blk** | stringa formato | Formato placeholder per block. | più corto → output più piccolo | `--placeholder-blk "§§b{:03d}§§"` |
| **--placeholder-sub** | stringa formato | Formato placeholder per substring. | più corto → output più piccolo | `--placeholder-sub "§§s{:03d}§§"` |
| **--verify-roundtrip** | flag | Verifica roundtrip e fallisce se non coincide. | flag booleano | `--verify-roundtrip` |

---

**Preset completo:**

```sh
python3 cli.py \
  --input ../groqbash/groqbash \                # obbligatorio
  --output ./out \                              # opzionale (default: ./compressed_output)
  --L_min 30 \                                   # opzionale (default: 64)
  --N_min 2 \                                    # opzionale (default: 2)
  --B_min_lines 3 \                              # opzionale (default: 5)
  --B_max_lines 10 \                             # opzionale (default: 20)
  --min_total_saving 20 \                        # opzionale (default: 100)
  --placeholder-sub "§§s{:03d}§§" \              # opzionale (default: §§s{:03d}§§)
  --placeholder-blk "§§b{:03d}§§" \              # opzionale (default: §§b{:03d}§§)
  --export-mapping-for groqbash \                # opzionale (genera mapping_subset.json)
  --export-manifest \                            # opzionale (manifest basato su input originale)
  --verify-roundtrip \                           # opzionale (consigliato)
  --chunk-output \                               # opzionale (genera chunk)
  --chunk-size 18000                             # opzionale (default: 16000)
```

---

**Preset aggressivo**

```sh
python3 cli.py \
  --input ../groqbash/groqbash \
  --output ./out \
  --L_min 24 \
  --N_min 2 \
  --B_min_lines 3 \
  --B_max_lines 10 \
  --min_total_saving 20 \
  --placeholder-sub "§§s{:03d}§§" \
  --placeholder-blk "§§b{:03d}§§" \
  --export-mapping-for groqbash
```

---

### Nota rapida
- **Obiettivo**: abbassare `L_min` e `min_total_saving` e usare placeholder più corti per rendere i singoli file `out/...` molto piccoli; la **reverse_map.json** crescerà.  
- **Estrazione automatica**: usa `--export-mapping-for` per ottenere `out/mapping_subset.json` contenente solo i placeholder rilevanti per i file selezionati.

---

## Comandi per generare il manifest

Di seguito i comandi esatti da eseguire con la `cli.py` aggiornata. Sostituisci `INPUT_DIR` e `OUT_DIR` con i percorsi reali.

- **Genera solo il manifest** (scansione + manifest compatto):
```sh
python3 cli.py --input INPUT_DIR --output OUT_DIR --export-manifest
```

- **Esegui tutta la pipeline e genera anche il manifest** (scan, compressione, reverse_map, mapping_subset opzionale, manifest):
```sh
python3 cli.py --input INPUT_DIR --output OUT_DIR --export-manifest
```

- **Genera mapping_subset.json per file specifici e il manifest insieme**:
```sh
python3 cli.py --input INPUT_DIR --output OUT_DIR --export-mapping-for file1.txt,file2.md --export-manifest
```

- **Esempio reale per la tua cartella groqbash**:
```sh
python3 cli.py -i ../groqbash/groqbash -o ./out --export-manifest
```

---

### Dove trovare il manifest e cosa contiene
- **Percorso**: `OUT_DIR/manifest.json`  
- **Formato**: compatto e LLM‑friendly con chiavi `paths`, `files`, `ph`, `v` (come definito).

---

### Note operative rapide
- **Input può essere** una directory o un file‑lista (come già supportato da `scan_files`).  
- Se vuoi **escludere pattern** (es. `.lock`) modifica `core.scan_files()` o filtra `file_metas` prima di chiamare `core.build_manifest`.  
- Usa `--export-manifest` ogni volta che vuoi un manifest stabile e deterministico; il comando è idempotente.

