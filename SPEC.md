[![Compressore locale LLM‑ready](https://img.shields.io/badge/Compressore_locale_LLM‑ready-00aa55?style=for-the-badge&label=>&labelColor=004d00)](README.md)

## SPEC tecnica per core.py

Specifica completa e rigorosa per **core.py**, per sviluppo, review e test.

---

### 1. Scelte fondamentali e convenzioni globali
- **Offset e posizioni**: tutti gli offset `start` e `end` sono **in byte** rispetto al file originale. Se utile per debugging, includere anche `start_char`/`end_char`, ma la logica interna e i confronti usano **solo byte**.
- **Hashing**: tutti gli SHA usati per confronto sono **SHA256 sui bytes** del file o del contenuto.
- **Encoding**: i file vengono letti in **binary**. Se decodificati in UTF‑8 per operazioni testuali, mantenere anche la rappresentazione `bytes` per tutte le operazioni di offset e hashing.
- **Determinismo**: tutte le scelte (ordinamenti, tie‑breaker, assegnazione ID) devono essere riproducibili dallo stesso input e parametri.
- **Percorsi relativi**: tutti i percorsi salvati in output (`reverse_map`, `blocks/`) sono **relativi a OUT_DIR**.

---

### 2. Interfacce pubbliche e tipi di ritorno

#### `scan_files(input_path) -> List[FileMeta]`
- **Input**: `input_path` string (directory o file-lista).
- **Output**: `List[FileMeta]`.
- **Comportamento**:
  - Se `input_path` è directory: elenco ricorsivo di file regolari, ordinati alfabeticamente per percorso relativo.
  - Se file-lista: leggere linee non vuote, ignorare commenti `#`.
  - Ignora file non esistenti o non leggibili; se nessun file valido trovato → solleva `NoFilesFoundError`.
  - Calcola `size` in bytes e `sha256` leggendo in streaming.
- **FileMeta schema**:
```json
{ "path": "/abs/path", "size": 1234, "sha256": "hex" }
```

#### `load_contents(file_metas) -> Dict[path, ContentBlob]`
- **Input**: lista `FileMeta`.
- **Output**: dict `path` → `ContentBlob`.
- **ContentBlob**:
```json
{
  "bytes": "<raw bytes>",
  "text": "<utf8 string or null>",
  "line_index": [{"line_start_byte": int, "line_end_byte": int}],
  "error": null
}
```
- **Comportamento**:
  - Legge in binary; tenta decodifica UTF‑8. Se decodifica fallisce, `text` = `null`, `error` = descrizione; `bytes` sempre presente.
  - Costruisce `line_index` per mapping byte→linea.
  - Non modifica file originali.

#### `find_repetitions(contents, L_min, N_min, B_min_lines, B_max_lines, L_max) -> List[Candidate]`
- **Input**: `contents` dict, parametri interi.
- **Output**: lista `Candidate`.
- **Candidate schema**:
```json
{
  "id_hash": "sha256(content_bytes)",
  "type": "substring"|"block",
  "content_bytes": "<bytes>",
  "occurrences": [{"path": "...", "start_byte": int, "end_byte": int}]
}
```
- **Comportamento**:
  - **Substring phase**: rolling hash su finestre `L_min` (Rabin‑Karp 64‑bit + verifica byte‑wise; opzionale doppio hash). Raggruppa hash → occorrenze; filtra gruppi con occorrenze ≥ `N_min`; per ogni gruppo estende greedy sinistra/destra fino a mismatch o `L_max`.
  - **Block phase**: split per linee; per dimensioni fisse `{B_min_lines, mid, B_max_lines}` (es. `{5,10,20}`) scorre blocchi contigui, calcola hash del blocco bytes, raggruppa e produce candidate con occorrenze ≥ 2.
  - **Collision handling**: prima di accettare occorrenze uguali, verificare uguaglianza byte‑wise.
  - **Vincoli**: non attraversa file boundary; nessun fuzzy matching.

#### `select_replacements(candidates, placeholder_fmt_sub, placeholder_fmt_blk, min_total_saving) -> List[Replacement]`
- **Input**: `candidates` list, placeholder formats (es. `"§§s{:03d}§§"`), `min_total_saving` int.
- **Output**: lista `Replacement`.
- **Replacement schema**:
```json
{
  "id": "S:001",
  "type": "substring"|"block",
  "placeholder": "§§s001§§",
  "content_bytes": "<bytes>",
  "occurrences": [{"path":"...","start_byte":int,"end_byte":int}],
  "estimated_saving": int
}
```
- **Comportamento**:
  - Calcola `estimated_saving = (len(content_bytes) - len(placeholder_bytes)) * (occurrences_count - 1)`.
  - Ordina candidati per `estimated_saving` decrescente.
  - Seleziona greedy: per ogni candidato verifica che **nessuna** delle sue occorrenze si sovrapponga byte‑wise a intervalli già occupati; se ok, seleziona e marca intervalli.
  - **Tie‑breaker deterministico**: ordina per `(estimated_saving desc, len(content_bytes) desc, sha256(content_bytes) asc, occurrences_paths_sorted asc)`.
  - Assegna ID in modo deterministico: numerazione sequenziale separata per substring e block dopo ordinamento tie‑breaker.
  - Filtra candidati con `estimated_saving < min_total_saving`.

#### `apply_placeholders(contents, replacements, max_json_inline, blocks_dir) -> (llm_ready, reverse_map)`
- **Input**: `contents` dict, `replacements` list, `max_json_inline` int, `blocks_dir` path relative a OUT_DIR.
- **Output**:
  - `llm_ready`: dict `path` → bytes del file trasformato (usare bytes per scrittura).
  - `reverse_map`: struttura JSON serializzabile (vedi schema).
- **Comportamento**:
  - Per ogni file costruisce lista di intervalli approvati, ordina per `start_byte`, verifica non sovrapposizione; ricostruisce bytes concatenando segmenti originali e placeholder bytes.
  - Non usare `str.replace`; usare slicing byte‑wise.
  - Popola `reverse_map.placeholders` con `content` inline se `len(content_bytes) <= max_json_inline`, altrimenti salva in `blocks_dir/B_<id>.bin` e usa `content_file` con percorso relativo.
  - `reverse_map` include `sha256` e `length` per ogni placeholder e lista occorrenze con `start_byte`/`end_byte`.

#### `roundtrip_check(file_metas, llm_ready, reverse_map) -> (bool, List[str])`
- **Input**: `file_metas`, `llm_ready`, `reverse_map`.
- **Output**: `(ok: bool, details: List[str])`.
- **Comportamento**:
  - Per ogni file in `llm_ready` ricostruisce bytes sostituendo placeholder con `content_bytes` usando le occorrenze registrate (non replace globale).
  - Calcola `sha256` del bytes ricostruito e confronta con `file_metas.sha256`.
  - Se mismatch, aggiunge dettaglio deterministico: `"{path}: mismatch at offset {first_mismatch_offset}, expected_sha={expected}, got_sha={got}, placeholders_involved=[...]"`.
  - `ok = True` solo se tutti i file corrispondono.

---

### 3. Formati JSON e file ausiliari

#### reverse_map.json schema esemplificativo
```json
{
  "placeholders": {
    "S:001": {
      "type": "substring",
      "content": "base64 or omitted",
      "content_file": "blocks/B_S_001.bin",
      "sha256": "hex",
      "length": 123,
      "occurrences": [{"path": "src/a.py", "start_byte": 120, "end_byte": 243}]
    }
  },
  "files": {
    "src/a.py": {"sha256": "hex", "size": 1234}
  },
  "metadata": {
    "tool_version": "1.0.0",
    "params": {"L_min":64,"N_min":2,"B_min_lines":5,"B_max_lines":20,"L_max":2000,"min_total_saving":100},
    "created_at": "ISO8601"
  }
}
```
- **Note**:
  - `content` è presente solo se `length <= max_json_inline` e può essere base64‑encoded per sicurezza; altrimenti `content_file` è obbligatorio.
  - `blocks/` directory: `OUT_DIR/blocks/B_<id>.bin`.

#### chunks/manifest.json schema esemplificativo
```json
{
  "chunks": {
    "chunk_0001": {"sha256":"hex","length":12345},
    "chunk_0002": {"sha256":"hex","length":54321}
  },
  "files": {
    "src/large.py": {"chunks":["chunk_0001","chunk_0002"], "sha256": "hex_optional"}
  },
  "metadata": {"tool_version":"1.0.0","created_at":"ISO8601"}
}
```
- **Comportamento**: `sha256` per file è opzionale; se presente va verificato durante ricostruzione.

---

### 4. Algoritmi, limiti e complessità

#### Substring detection
- **Rolling hash**: Rabin‑Karp 64‑bit + verifica byte‑wise; opzionale doppio hash per collisioni.
- **Fasi**:
  1. Calcola rolling hash su ogni file per finestre `L_min`.
  2. Raggruppa hash → occorrenze; filtra gruppi con occorrenze ≥ `N_min`.
  3. Per ogni gruppo, prendi seed (prima occorrenza deterministica) e estendi greedy sinistra/destra byte‑wise fino a mismatch o `L_max`.
  4. Calcola `sha256(content_bytes)` e crea `Candidate`.
- **Limiti**: `L_max` default 2000; estensioni limitate per evitare O(n²).

#### Block detection
- **Dimensioni fisse**: usare set predefinito `{B_min_lines, mid, B_max_lines}`.
- **Fasi**:
  1. Per ogni file e dimensione scorre blocchi contigui (sliding window per linee).
  2. Calcola hash del blocco bytes; raggruppa e produce candidate con occorrenze ≥ 2.
- **Complessità**: O(total_lines × number_of_sizes).

#### Selection and conflict resolution
- **Metric**: `estimated_saving`.
- **Greedy**: ordina candidati per tie‑breaker definito; seleziona se nessuna occorrenza sovrappone intervalli già marcati.
- **Sovrapposizioni**: rifiuta candidati che causano sovrapposizioni byte‑wise; i candidati rifiutati non vengono ripescati.

---

### 5. Regole conservative e sicurezza
- **Heuristica string literal/regex**:
  - Implementare `is_in_string_like_context(path, start_byte, end_byte, content_blob) -> bool`.
  - Regole minime: se file estensione è codice noto, e la linea contiene un numero dispari di delimitatori `"` o `'` tra inizio linea e `start_byte`, considerare occorrenza in string literal e **escluderla**.
  - Per regex in linguaggi che usano `/.../`, applicare analoga heuristica.
- **Template markers**: escludere occorrenze che contengono `{{`, `}}`, `${` o sequenze di escape tipiche `\n`, `\t` se appaiono in contesto template.
- **Non alterare** indentazione o line endings; placeholder sostituisce esattamente la sequenza di bytes trovata.
- **Fallback**: un candidato è valido se ha almeno `N_min` occorrenze non escluse.

---

### 6. Operazioni I/O, atomicità, logging e temp
- **Atomic write**:
  - Scrivere output in `OUT_DIR/.tmp_<pid>_<ts>/`.
  - Solo se tutti i check passano, rinominare atomically `.tmp_...` → `OUT_DIR`.
- **Temp cleanup**: su crash, lasciare `.tmp_...` per debug e fornire comando `--cleanup-temp`.
- **Logging**:
  - Livelli: `ERROR`, `WARN`, `INFO`, `DEBUG`.
  - Messaggi standard per: file saltati, placeholder creati, candidate rifiutati per sovrapposizione, roundtrip mismatch.
- **Parallelismo**:
  - Consentito per file indipendenti nelle fasi di hashing e block detection; sincronizzare accesso alla mappa globale hash.
- **Memory**:
  - Raccomandare streaming per file > 100MB; limitare buffer per rolling hash.

---

### 7. Parametri consigliati, test e checklist di rilascio

#### Parametri consigliati iniziali
- `L_min = 64`
- `N_min = 2`
- `block sizes = {5,10,20}`
- `L_max = 2000`
- `min_total_saving = 100`
- `max_json_inline = 4096` bytes
- `blocks_dir = "blocks"`

#### Test minimo obbligatorio
- **Test A**: due file identici con paragrafo ripetuto → placeholder creato, roundtrip OK.
- **Test B**: file codice con string literal ripetuta → string literal esclusa dalla sostituzione.
- **Test C**: sovrapposizione candidate → greedy selection e tie‑break deterministico.
- **Test D**: file non UTF‑8 → `text=null`, `bytes` usati, comportamento configurabile.
- **Test E**: chunking end‑to‑end con `OUT_DIR/chunks/manifest.json` e ricostruzione da chunk.
