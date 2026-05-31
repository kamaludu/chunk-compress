### Overview
Specifica completa e rigorosa per **core.py**. Scopo: implementare la pipeline minima che legge file testuali e di codice, individua ripetizioni esatte, applica placeholder testuali reversibili e produce `llm_ready` + `reverse_map` + verifica roundtrip. Nessun parsing profondo, nessun tokenizer, solo confronto testuale e hashing.

---

### Funzioni pubbliche e interfacce
Ogni funzione è descritta con **input**, **output**, e comportamento deterministico.

#### `scan_files(input_path) -> List[FileMeta]`
- **Input**: `input_path` string (directory o file-lista).
- **Output**: lista di `FileMeta` oggetti:  
  - **path** string assoluto, **size** int bytes, **sha256** hex string.
- **Comportamento**:  
  - Se `input_path` è directory, elenca ricorsivamente file regolari ordinati alfabeticamente.  
  - Se è file-lista, legge linee non vuote come percorsi.  
  - Ignora file non esistenti o non leggibili; segnala via eccezione solo se nessun file valido trovato.  
  - Calcola `sha256` leggendo in streaming.

#### `load_contents(file_metas) -> Dict[path, text]`
- **Input**: lista `FileMeta`.
- **Output**: dizionario mapping `path` → `text` (UTF-8).
- **Comportamento**:  
  - Legge ogni file in modalità binaria e decodifica UTF-8; su errore di decodifica fallisce per quel file e lo segnala nel risultato (entry mancante + warning).  
  - Non modifica file originali.

#### `find_repetitions(contents, L_min, N_min, B_min_lines, B_max_lines) -> List[Candidate]`
- **Input**: `contents` dict, parametri interi.  
- **Output**: lista di `Candidate` con campi: **id_hash**, **type** ("substring"|"block"), **content**, **occurrences** list di `{path,start,end}`.
- **Comportamento**: due fasi separate e non intrecciate:
  - **Substring phase**: usa n‑gram hashing su finestre fisse `L_min` con rolling hash per efficienza; raggruppa occorrenze con stesso hash; per ogni gruppo con occorrenze ≥ `N_min` estende greedy i confini a sinistra e destra confermando uguaglianza carattere per carattere su tutte le occorrenze; produce candidate solo se lunghezza finale ≥ `L_min`.
  - **Block phase**: split per linee; per ogni file scorre blocchi di dimensione fissa o di poche dimensioni predefinite (es. 5, 10, 20 linee) per evitare esplosione; calcola hash del blocco; raggruppa occorrenze con stesso hash; produce candidate se occorrenze ≥ 2.
- **Vincoli**: non considera estensioni che attraversano confini di file; non tenta fuzzy matching.

#### `select_replacements(candidates, placeholder_fmt_sub, placeholder_fmt_blk, min_total_saving) -> List[Replacement]`
- **Input**: lista `Candidate`, formati placeholder, soglia risparmio.
- **Output**: lista `Replacement` con campi: **id** (es. `S:001`), **type**, **content**, **occurrences** (posizioni), **placeholder** string.
- **Comportamento**:  
  - Calcola risparmio stimato per ogni candidate: `(len(content) - len(placeholder)) * (occurrences_count - 1)`.  
  - Ordina candidati per risparmio decrescente; seleziona greedily evitando sovrapposizioni per file.  
  - Risolve conflitti scegliendo il candidato con risparmio maggiore; in caso di pareggio sceglie il contenuto più lungo; assegnazione ID deterministica (ordinamento alfabetico dei path delle occorrenze, poi contatore).  
  - Filtra i candidati con risparmio totale < `min_total_saving`.

#### `apply_placeholders(contents, replacements) -> (llm_ready, reverse_map)`
- **Input**: `contents` dict, `replacements` list.
- **Output**:  
  - `llm_ready`: dict `path` → testo trasformato con placeholder.  
  - `reverse_map`: struttura JSON serializzabile (vedi sezione Strutture dati).
- **Comportamento**:  
  - Per ogni file costruisce lista di intervalli approvati, ordina per `start`, verifica non sovrapposizione; ricostruisce testo concatenando segmenti originali e placeholder.  
  - Non usa `str.replace` globale; usa posizioni per sostituzione atomica.  
  - Popola `reverse_map` con mapping placeholder → contenuto originale e lista occorrenze.

#### `roundtrip_check(file_metas, llm_ready, reverse_map) -> (bool, List[str])`
- **Input**: `file_metas` originali, `llm_ready`, `reverse_map`.
- **Output**: boolean `ok`, lista `details` con mismatch o errori.
- **Comportamento**:  
  - Per ogni file in `llm_ready` ricostruisce il testo sostituendo ogni placeholder con il contenuto corrispondente usando le posizioni registrate nel `reverse_map` (non con replace globale).  
  - Calcola sha256 del testo ricostruito e confronta con `sha256` in `file_metas`.  
  - Restituisce `ok = True` solo se tutti i file corrispondono; altrimenti `ok = False` e `details` contiene descrizioni deterministiche dei mismatch.

---

### Strutture dati interne e formato reverse_map
Definire formati JSON semplici, deterministici e verificabili.

#### FileMeta
```json
{ "path": "/abs/path", "size": 1234, "sha256": "hex" }
```

#### Candidate
```json
{ "id_hash": "sha256(content)", "type": "substring"|"block", "content": "exact text", "occurrences": [{"path": "...", "start": int, "end": int}] }
```

#### Replacement
```json
{ "id": "S:001", "type": "substring"|"block", "placeholder": "<<S:001>>", "content": "exact text", "occurrences": [{"path":"...","start":int,"end":int}] }
```

#### reverse_map JSON schema top level
- **placeholders**: object mapping `id` → `{ "type", "content" or "content_file", "sha256", "length", "occurrences": [...] }`
- **files**: optional manifest with original file metas
- **metadata**: tool version, parameters, timestamp

Esempio sintetico
```json
{
  "placeholders": {
    "S:001": {
      "type": "substring",
      "content": "function foo() { return 1; }",
      "sha256": "abc...",
      "length": 24,
      "occurrences": [{"path":"/p/a.js","start":120,"end":144}]
    }
  },
  "metadata": { "L_min":64, "N_min":2, "created_at":"ISO8601" }
}
```
Nota: se `content` supera soglia `max_json_inline` il campo diventa `content_file` con percorso relativo a `blocks/B_001.txt`.

---

### Algoritmi dettagliati e complessità
Fornire regole chiare per implementazione efficiente e deterministica.

#### Substring detection algorithm
- **Step 1**: per ogni file calcola rolling hash su finestre di lunghezza `L_min` (Rabin-Karp con base e modulo a 64-bit o doppio hash per collisione ridotta). Memorizza mappa `hash -> list[(path, offset)]`.
- **Step 2**: filtra hash con lista di occorrenze ≥ `N_min`.
- **Step 3**: per ogni gruppo seleziona la prima occorrenza come seed; per ogni occorrenza estende i confini:
  - estensione a destra: confronta carattere per carattere tra occorrenze e seed fino a mismatch; stessa per sinistra.
  - l’estensione è limitata da lunghezza massima ragionevole per evitare O(n²); si può imporre `L_max`.
- **Step 4**: calcola SHA256 del testo esteso per identificatore unico; produce `Candidate`.
- **Complessità**: rolling hash O(total_chars); estensioni costose solo per gruppi con occorrenze multiple; limite `L_max` mantiene costi sotto controllo.

#### Block detection algorithm
- **Approccio**: non esplorare tutte le dimensioni; usare set di dimensioni fisse es. `{5,10,20}` linee.
- **Step**: per ogni file e per ogni dimensione scorre blocchi contigui, calcola hash del blocco, raggruppa occorrenze; produce candidate se occorrenze ≥ 2.
- **Complessità**: O(total_lines × number_of_sizes).

#### Selection and conflict resolution
- **Metric**: risparmio totale stimato.  
- **Greedy selection**: ordina candidati per risparmio decrescente; per ogni candidato verifica che nessuna delle sue occorrenze si sovrapponga a intervalli già occupati; se ok, seleziona e marca intervalli occupati.  
- **Determinismo**: tie-breaker basato su `sha256(content)` e lista occorrenze ordinata.

---

### Regole conservative per sicurezza e integrità
Minimo indispensabile per evitare corruzione del codice.

- **Non sostituire** se una occorrenza è interamente contenuta all’interno di una string literal o regex non verificabile senza parsing. Heuristica minima:  
  - se il file ha estensione di codice conosciuta, e la occorrenza è su una singola linea che contiene un numero dispari di delimitatori di stringa (`"` o `'`) o delimitatori di regex (`/`), **escludere** quella occorrenza.  
- **Non sostituire** se la substring contiene template markers `{{`, `}}`, `${` o sequenze di escape `\n` che appaiono in contesti di template.  
- **Non modificare** indentazione o line endings: placeholder sostituisce esattamente la sequenza di caratteri trovata.  
- **Fallback**: se una occorrenza è esclusa, il candidato può ancora essere selezionato se ha almeno `N_min` occorrenze non escluse.

---

### Roundtrip verification e garanzie
Procedure per garantire reversibilità e non perdita.

- **Roundtrip ricostruzione**: usare le posizioni registrate in `reverse_map` per reinserire i contenuti originali nelle stringhe `llm_ready`. Non usare sostituzioni testuali globali.  
- **Checksum**: confrontare `sha256` ricostruito con `sha256` originale per ogni file.  
- **Fallimento**: se mismatch, abortare promozione dell’output e scrivere log dettagliato con: file path, placeholder id coinvolti, differenze di lunghezza e primo offset di mismatch.  
- **Atomic write**: scrivere output in directory temporanea e rinominare solo se tutti i check passano.

---

### Output attesi e parametri minimi
- **llm_ready**: directory con file trasformati, stessa struttura relativa rispetto alla directory di input.  
- **reverse_map.json**: JSON con `placeholders`, `metadata`, e riferimento a eventuali `blocks/` file.  
- **report**: oggetto o testo con `orig_total_chars`, `new_total_chars`, `saved_chars`, `saved_pct`, `num_placeholders`, `roundtrip_ok`.

Parametri consigliati iniziali: `L_min = 64`, `N_min = 2`, block sizes `{5,10,20}`, `L_max = 2000`, `min_total_saving = 100`.

---

### Note implementative e test minimo
- **Determinismo**: tutte le scelte devono essere riproducibili dallo stesso input e parametri.  
- **Test minimo**: file solo testo con paragrafi ripetuti; file codice con funzioni identiche; file con string literal che contengono ripetizioni per verificare esclusione.  
- **Performance**: implementare rolling hash e limitare estensioni con `L_max`; usare streaming per file grandi.

---
