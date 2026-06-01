# README — Uso minimo del compressore locale LLM‑ready

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

| **Flag** | **Tipo** | **Descrizione** | **Range / note** | **Esempio** |
|---|---:|---|---|---|
| **--input, -i** | stringa | Directory o file‑lista (file di testo con un percorso per riga) da processare. | deve esistere | `--input ./project` |
| **--output, -o** | stringa | Directory di output dove vengono scritti i file compressi e le mappe. | viene creata se mancante | `--output ./out` |
| **--L_min** | intero | Lunghezza minima substring per il rolling hash (cattura ripetizioni corte). | pratico: **4**–2000; default **64** | `--L_min 24` |
| **--N_min** | intero | Numero minimo di occorrenze per considerare una substring candidata. | minimo **2** | `--N_min 2` |
| **--B_min_lines** | intero | Numero minimo di righe per candidati block. | minimo **1**; ≤ B_max_lines | `--B_min_lines 3` |
| **--B_max_lines** | intero | Numero massimo di righe per candidati block. | ≥ B_min_lines | `--B_max_lines 10` |
| **--min_total_saving** | intero | Risparmio totale minimo (caratteri) richiesto per accettare una sostituzione. | minimo **0**; tipico **20–200**; default **100** | `--min_total_saving 20` |
| **--placeholder-sub** | stringa formato | Formato per i placeholder delle substring; deve contenere un token di formato. | più corto → file più piccoli | `--placeholder-sub "§§s{:03d}§§"` |
| **--placeholder-blk** | stringa formato | Formato per i placeholder dei block; deve contenere un token di formato. | più corto → file più piccoli | `--placeholder-blk "§§b{:03d}§§"` |
| **--export-mapping-for** | stringa (lista) | Lista separata da virgole di nomi file (relativi a `--output`) per cui esportare `mapping_subset.json`. | nomi o percorsi relativi | `--export-mapping-for INSTALL.md,header.html` |
| **--export-manifest** | flag | Genera `manifest.json` compatto e LLM‑friendly in OUT_DIR (contiene `paths`, `files` con `i`/`sha`/`ph`, `ph` metadati `sha`/`len`, `v`); usa path relativi e evita path assoluti e file filtrati. | flag booleano | `--export-manifest` |
| **--verify-roundtrip** | flag | Esegue il controllo di roundtrip e fallisce se la ricostruzione non corrisponde. | flag booleano | `--verify-roundtrip` |

---

### Preset aggressivo consigliato

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

