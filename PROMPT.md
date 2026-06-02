[![Compressore locale LLM‑ready](https://img.shields.io/badge/Compressore_locale_LLM‑ready-00aa55?style=for-the-badge&label=>&labelColor=004d00)](README.md)

# 🔥 PROMPT MASTER - senza uso di CHUNKS
(ottimizzato per Copilot Think Deeper)

Pipeline ottimale:  
**manifest → mapping → file compressi → ricostruzione → analisi**

---

## **1) Inizio sessione**
*(Stabilisce il contesto, definisce i ruoli e impedisce a Copilot di anticipare azioni)*

```text
Sto per fornirti:
1) un manifest dei file (struttura, percorsi, placeholder usati)
2) un mapping dei placeholder → contenuto
3) uno o più file compressi che usano quei placeholder

Il tuo compito sarà:
- leggere il manifest come mappa della struttura del progetto
- leggere il mapping come vocabolario dei placeholder
- applicare il mapping ai file compressi
- ricostruire i file originali in modo esatto, senza invenzioni o correzioni implicite
- opzionalmente analizzarli o modificarli su mia richiesta

Nota:
- Non devi ricostruire nulla finché non te lo chiedo esplicitamente.
- Ogni fase deve essere confermata prima di procedere alla successiva.

Conferma quando sei pronto a ricevere il manifest.
```

---

## **2) Incolla manifest.json**
*(Copilot deve solo caricarlo; non deve interpretarlo né usarlo ancora)*

```text
Questo è il manifest dei file.

Contiene:
- paths: elenco dei file in ordine deterministico
- files: per ogni file, indice → sha → placeholder usati
- ph: metadati dei placeholder (sha, lunghezza)
- v: versione dello schema

Istruzioni:
- Non usarlo ancora.
- Non tentare di ricostruire nulla.
- Limitati a confermare che il manifest è stato caricato correttamente.

(qui incollerò manifest.json)
```

---

## **3) Incolla mapping_subset.json**
*(Copilot deve caricare il dizionario dei placeholder, ma non applicarlo ancora)*

```text
Questo è il mapping dei placeholder.
Usalo come dizionario placeholder → contenuto.

Istruzioni:
- Non applicare ancora il mapping.
- Non tentare di ricostruire i file.
- Conferma solo che il mapping è stato caricato correttamente.

(qui incollerò mapping_subset.json)
```

---

## **4) Incolla file compressi**
*(Copilot deve solo riceverli; non deve ancora ricostruire)*

```text
Ora ti fornisco uno o più file compressi che contengono i placeholder del mapping.

Istruzioni:
- Non ricostruire ancora.
- Non applicare il mapping.
- Conferma solo che hai ricevuto i file compressi.

(qui incollerò i file compressi)
```

---

## **5) Ricostruzione**
*(Qui Copilot deve applicare mapping + manifest per ricostruire i file esatti)*

```text
Ora ricostruisci il file (o i file) sostituendo ogni placeholder con il contenuto corrispondente dal mapping.

Regole di ricostruzione:
- Nessuna invenzione.
- Nessuna correzione automatica.
- Nessuna riformattazione non richiesta.
- La ricostruzione deve essere esatta, carattere per carattere.
- Se un placeholder non è presente nel mapping, segnalalo chiaramente.

Restituisci il file ricostruito.
```

---

## **6) Analisi o modifiche**
*(Solo dopo la ricostruzione puoi chiedere analisi, refactoring, modifiche, ecc.)*

```text
Ora analizza il file ricostruito e produci:
- elenco dei problemi
- suggerimenti di miglioramento
- eventuali modifiche richieste

Oppure, se voglio una trasformazione:

"Applica le seguenti modifiche al file ricostruito: …"

Regole:
- Mantieni sempre la struttura del file.
- Non inventare contenuti non presenti.
- Non alterare parti non richieste.
```

---

## 🎯 Sequenza finale consigliata

```text
1. Inizio sessione
2. Incolla manifest
3. Incolla mapping
4. Incolla file compressi
5. Ricostruzione
6. Analisi o modifiche
```

---


# 🔥 PROMPT MASTER — con uso di CHUNKS

Pipeline ottimale:  
**chunks/manifest.json → mapping_subset.json → chunk files → assemblaggio → ricostruzione → verifica SHA → analisi**

---

## **1) Inizio sessione**
```text
Sto per fornirti, in sequenza controllata:

1) il chunks/manifest.json  
   (descrive come i file originali sono stati suddivisi in chunk e l’ordine dei chunk)

2) il mapping_subset.json  
   (dizionario placeholder → contenuto originale)

3) uno o più chunk files  
   (pezzi di file compressi, contenenti placeholder)

Il tuo compito sarà:

- caricare ogni elemento senza usarlo finché non te lo chiedo
- confermare il caricamento di ogni elemento
- ricostruire i file originali concatenando i chunk nell’ordine indicato
- applicare il mapping ai placeholder
- verificare l’integrità tramite SHA256 se presente nel manifest
- segnalare chunk mancanti, placeholder mancanti o mismatch di SHA
- non inventare, non correggere, non riformattare nulla

Conferma quando sei pronto a ricevere il chunks/manifest.json.
```

---

## **2) Incolla chunks/manifest.json**
```text
Questo è il chunks/manifest.json.

Contiene per ogni file:
- percorso relativo
- elenco ordinato dei chunk_id che compongono il file
- sha256 atteso del file ricostruito (se presente)
- metadati aggiuntivi

Istruzioni:
- NON usarlo ancora
- NON ricostruire nulla
- Conferma solo che il chunks/manifest.json è stato caricato correttamente

(qui incollerò chunks/manifest.json)
```

---

## **3) Incolla mapping_subset.json**
```text
Questo è il mapping dei placeholder (placeholder → contenuto originale).

Istruzioni:
- NON applicare ancora il mapping
- NON ricostruire nulla
- Conferma solo che il mapping è stato caricato correttamente

(qui incollerò mapping_subset.json)
```

---

## **4) Incolla i chunk files**
```text
Ora ti fornirò i chunk files generati dal compressore.

Ogni chunk:
- ha un chunk_id univoco
- contiene testo già compresso (LLM‑ready)
- può contenere placeholder
- deve essere assemblato nell’ordine indicato nel chunks/manifest.json

Istruzioni:
- NON ricostruire ancora
- NON applicare il mapping
- Conferma solo la ricezione di ogni chunk_id
- Se un chunk è troppo grande per un singolo messaggio, chiedimi di inviarlo suddiviso
- Se mancano chunk rispetto al manifest, segnalalo immediatamente

(qui incollerò i chunk, uno per messaggio o più per messaggio)
```

---

## **5) Ricostruzione (solo quando te lo chiede esplicitamente)**
```text
Quando ti darò il comando “Procedi con la ricostruzione”, esegui quanto segue per OGNI file elencato nel chunks/manifest.json:

1. Recupera la lista ordinata dei chunk_id del file.
2. Concatenali nell’ordine esatto per ottenere il testo compresso completo.
3. Applica il mapping:
   - sostituisci ogni placeholder con il contenuto corrispondente
   - se un placeholder non esiste nel mapping, interrompi e segnalalo

4. Verifica integrità:
   - se nel manifest è presente sha256 atteso → calcola sha256 del file ricostruito e confrontalo
   - se lo SHA non è presente → limita la verifica alla ricostruzione sintattica

5. Output:
   - stato: RICOSTRUITO / FALLITO
   - sha atteso e sha calcolato (se disponibili)
   - elenco chunk mancanti o placeholder mancanti (se presenti)
   - il file ricostruito (solo se te lo chiedo esplicitamente)

Regole fondamentali:
- Nessuna invenzione
- Nessuna correzione automatica
- Nessuna riformattazione
- Ricostruzione esatta, carattere per carattere
```

---

## **6) Analisi o modifiche (solo dopo ricostruzione)**
```text
Dopo che avrai ricostruito correttamente i file, potrò chiederti:

A) Analisi
- elenco dei problemi
- punti critici
- suggerimenti di miglioramento
- refactoring mirato
- spiegazioni tecniche

B) Modifiche controllate
Se ti chiedo modifiche, applicale seguendo queste regole:

1. Mantieni la struttura del file.
2. Non inventare contenuti non presenti.
3. Non alterare parti non richieste.
4. Se una modifica è ambigua, chiedi chiarimenti.
5. Se una modifica richiede di toccare placeholder, avvisami prima.

Esempi di richieste valide:
- “Rendi più leggibile questa funzione.”
- “Rimuovi solo i commenti superflui.”
- “Applica queste modifiche al file ricostruito: …”
```

---

## **7) Sequenza consigliata (chunk workflow completo)**
```text
1. Inizio sessione
2. Incolla chunks/manifest.json
3. Incolla mapping_subset.json
4. Incolla tutti i chunk (con chunk_id)
5. Comando: “Procedi con la ricostruzione”
6. Verifica SHA e segnalazione problemi
7. Analisi o modifiche su file ricostruiti
```

---

## **8) Note tecniche finali**

- I chunk sono porzioni di file compressi (LLM‑ready) che contengono placeholder.
- L’ordine dei chunk è definito SOLO dal chunks/manifest.json.
- Il mapping è globale e può essere applicato a chunk diversi.
- Se manca un chunk, un placeholder o uno SHA, devi segnalarlo senza tentare di indovinare.
- La ricostruzione deve essere esatta, carattere per carattere.
- Se un chunk è troppo grande per un singolo messaggio, chiedi di inviarlo suddiviso.

---
