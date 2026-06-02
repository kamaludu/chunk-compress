[![Compressore locale LLM‑ready](https://img.shields.io/badge/Compressore locale LLM‑ready-00aa55?style=for-the-badge&label=%E2%9E%9C&labelColor=004d00)](README.md)

# Compressore locale LLM‑ready  
Compressione reversibile per testo, ottimizzata per LLM (placeholder + manifest + chunking + roundtrip verificabile)

---

## 1. Clona il progetto
```sh
git clone --depth 1 --branch main https://github.com/kamaludu/chunk-compress.git chunk-compress
```

---

## 2. Struttura del progetto
Assicurati che questi file siano nella stessa directory:

```
core.py
cli.py
io_utils.py
```

---

## 3. Requisiti
- Python 3.8+
- Nessuna libreria esterna
- Funziona su qualsiasi shell con Python disponibile

---

## 4. Preparazione input
Puoi fornire:

**A) Una directory**  
Esempio:
```
/home/user/progetto/
```

**B) Una file‑lista**  
Un file di testo con un percorso per riga:
```
src/a.py
src/b.py
docs/readme.md
```

---

## 5. Esecuzione base
```sh
python3 cli.py --input <percorso_input> --output out
```

Se non specifichi `--output`, verrà usata automaticamente:

```
./compressed_output/
```

---

## 6. Parametri principali
- `--L_min` lunghezza minima substring (default 64)
- `--N_min` occorrenze minime (default 2)
- `--B_min_lines` righe minime per blocchi (default 5)
- `--B_max_lines` righe massime per blocchi (default 20)
- `--verify-roundtrip` verifica integrità totale

Esempio:
```sh
python3 cli.py --input ./src --output ./out --L_min 80 --verify-roundtrip
```

---

## 7. Output generati
Dentro la directory `out/` troverai:

**1) File compressi LLM‑ready**
Stessa struttura dei file originali, ma con placeholder:

```
§§s001§§   (substring)
§§b001§§   (block)
```

**2) mapping_subset.json**
Contiene **solo i placeholder effettivamente usati nei file compressi**.

- È generato **automaticamente per tutti i file processati**.
- È pensato per essere incollato in una chat LLM.
- È molto più piccolo di `reverse_map.json`.

Puoi controllarne la generazione con:

- `--no-export-mapping` → **nessun mapping_subset.json**
- `--no-export-mapping file1,file2,...` → esclude solo quei file

**3) reverse_map.json**
Contiene il mapping **completo**:

- placeholder → contenuto originale
- posizioni originali
- metadati

È utile per verifiche locali, ma **troppo grande per essere incollato in una chat**.

**4) manifest.json** (solo se `--export-manifest`)
Manifest compatto della struttura originale:

- paths
- files
- placeholder usati
- versioning

**5) chunks/** (solo se `--chunk-output`)
Contiene:

```
chunks/
  chunk_0001.txt
  chunk_0002.txt
  ...
  manifest.json   ← manifest dei chunk
```

Il `chunks/manifest.json` descrive:

- quali chunk compongono ogni file
- ordine dei chunk
- SHA256 atteso (se presente)

---

## 8. Struttura completa della directory di output

Esempio tipico dopo l’esecuzione:

```
out/
  src/
    a.py
    b.py
  reverse_map.json
  mapping_subset.json
  manifest.json          (solo se --export-manifest)
  chunks/                (solo se --chunk-output)
    chunk_0001.txt
    chunk_0002.txt
    ...
    manifest.json        (manifest dei chunk)
```

---

## 9. Come usare gli output in una chat LLM

**Caso A — File piccoli (senza chunking)**
1. Apri `out/`
2. Copia i file compressi (sono molto più piccoli)
3. Incollali nella chat LLM
4. Incolla anche `mapping_subset.json`  
   → contiene solo i placeholder effettivamente usati  
5. Chiedi al modello di ricostruire i file usando mapping + file compressi

**Caso B — File grandi (con chunking)**
1. Apri `out/chunks/`
2. Copia:
   - `chunks/manifest.json`
   - tutti i chunk `chunk_*.txt`
   - `mapping_subset.json`
3. Incollali nella chat LLM seguendo la sequenza:
   - manifest dei chunk
   - mapping
   - chunk (uno o più per messaggio)
4. Chiedi al modello di ricostruire i file concatenando i chunk nell’ordine indicato

---

## 10. Flusso tipico (senza chunking)
1. Metti i tuoi file in una directory  
2. Lancia il comando  
3. Ottieni file compressi  
4. Incolla in chat LLM  
5. Risparmi token e mantieni reversibilità totale

---

## 11. Flusso tipico (con chunking)
1. Metti i tuoi file in una directory  
2. Lancia:
   ```sh
   python3 cli.py --input ./src --chunk-output
   ```
3. Ottieni:
   - file compressi normali
   - chunk in `out/chunks/`
4. In chat LLM:
   - incolla `chunks/manifest.json`
   - incolla `mapping_subset.json`
   - incolla i chunk
5. Chiedi la ricostruzione

---

## 12. Parametri CLI
(ordinati alfabeticamente)

| **Flag** | **Tipo** | **Descrizione** | **Range / note** | **Esempio** |
| --- | --- | --- | --- | --- |
| **--B_max_lines** | intero | Numero massimo di righe per candidati block. | ≥ B_min_lines | `--B_max_lines 20` |
| **--B_min_lines** | intero | Numero minimo di righe per candidati block. | minimo 1 | `--B_min_lines 5` |
| **--chunk-output** | flag | Genera chunk dei file compressi in `OUT_DIR/chunks/`. | flag booleano | `--chunk-output` |
| **--chunk-size** | intero | Dimensione massima dei chunk in caratteri. | default 16000 | `--chunk-size 16000` |
| **--export-manifest** | flag | Genera `manifest.json` compatto (paths, files, ph, v). | flag booleano | `--export-manifest` |
| **--include-pointless** | flag | NON esclude estensioni binarie/inutili durante lo scan. | default: esclusi | `--include-pointless` |
| **--input, -i** | stringa | Directory o file‑lista da processare. | deve esistere | `--input ./project` |
| **--L_min** | intero | Lunghezza minima substring per rolling hash. | 4–2000; default 64 | `--L_min 24` |
| **--min_total_saving** | intero | Risparmio minimo richiesto per accettare una sostituzione. | minimo 0; default 100 | `--min_total_saving 20` |
| **--N_min** | intero | Occorrenze minime per considerare una substring candidata. | minimo 2 | `--N_min 2` |
| **--no-export-mapping** | stringa opzionale | Disabilita l’export di `mapping_subset.json` o esclude file specifici. | senza valore → nessun export; con lista → esclude quei file | `--no-export-mapping`, `--no-export-mapping a/b.txt,c/d.py` |
| **--output, -o** | stringa | Directory di output. | default: `./compressed_output` | `--output ./out` |
| **--placeholder-blk** | stringa formato | Formato placeholder per block. | più corto → output più piccolo | `--placeholder-blk "§§b{:03d}§§"` |
| **--placeholder-sub** | stringa formato | Formato placeholder per substring. | più corto → output più piccolo | `--placeholder-sub "§§s{:03d}§§"` |
| **--verify-roundtrip** | flag | Verifica roundtrip e fallisce se non coincide. | flag booleano | `--verify-roundtrip` |

---

## 13. Parametri ottimizzabili
Range minimo/massimo, preset consigliati e note operative.

| Parametro | Range | Aggressivo | Conservativo | Max risparmio token | Note |
|----------|:-----:|-----------:|-------------:|---------------------:|------|
| **L_min** | 4 / ~2000 | 16 | 64 | 24–32 | Più basso → più match → più placeholder → più compressione. |
| **N_min** | 2 / ~100 | 2 | 3–4 | 2 | 2 = massimo rilevamento ripetizioni. |
| **B_min_lines** | 1 / ~50 | 2 | 5 | 3 | Blocchi troppo piccoli = più placeholder. |
| **B_max_lines** | B_min_lines / ~200 | 8–12 | 20 | 6–10 | Più basso → blocchi più granulari. |
| **min_total_saving** | 0 / ∞ | 0–10 | 100 | 0 | 0 = accetta tutto ciò che comprime anche di 1 carattere. |
| **chunk-size** | 2000 / ∞ | 8000 | 16000 | 4000–8000 | Influisce solo sui chunk, non sulla compressione. |

---

## 14. Preset completi

**Preset completo (aggressivo)**

```sh
python3 cli.py \
  --input ../directory/file.sh \
  --output ./out \
  --L_min 30 \
  --N_min 2 \
  --B_min_lines 3 \
  --B_max_lines 10 \
  --min_total_saving 20 \
  --placeholder-sub "§§s{:03d}§§" \
  --placeholder-blk "§§b{:03d}§§" \
  --export-manifest \
  --verify-roundtrip \
  --chunk-output \
  --chunk-size 15000
```

---

**Preset tipico**

```sh
python3 cli.py \
  --input ../selected/directory/ \
  --L_min 32 \
  --N_min 2 \
  --B_min_lines 3 \
  --B_max_lines 10 \
  --min_total_saving 20 \
  --export-manifest \
  --verify-roundtrip
```

---

## 15. Comandi per generare il manifest

### **Genera solo il manifest (senza compressione)**
```sh
python3 cli.py --input INPUT_DIR --output OUT_DIR --export-manifest
```

### **Pipeline completa + manifest**
```sh
python3 cli.py --input INPUT_DIR --output OUT_DIR --export-manifest
```

### **Esempio reale**
```sh
python3 cli.py -i ../directory/file.xx -o ./out --export-manifest
```

---

## 16. Dove trovare il manifest e cosa contiene

### **manifest.json** (struttura originale)
Percorso:  
`OUT_DIR/manifest.json`

Contiene:
- `paths`: elenco file
- `files`: placeholder usati per file
- `ph`: metadati placeholder
- `v`: versione schema

### **chunks/manifest.json** (solo se chunking attivo)
Percorso:  
`OUT_DIR/chunks/manifest.json`

Contiene:
- elenco chunk
- ordine dei chunk per ogni file
- SHA256 atteso (se presente)

---

## 17. Note operative rapide
- L’input può essere una directory o una file‑lista.  
- I file binari/inutili vengono esclusi automaticamente (usa `--include-pointless` per includerli).  
- `mapping_subset.json` è pensato per l’uso in chat LLM.  
- `reverse_map.json` è completo ma molto grande.  
- `--export-manifest` è idempotente.  
- I chunk sono utili per file molto grandi o per chat con limiti di input. 

---
