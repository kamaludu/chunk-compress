# 🔥 PROMPT MASTER — (ottimizzato per Copilot Think Deeper)

Pipeline ottimale: **manifest → mapping → file compressi → ricostruzione → analisi**

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

# 🎯 Sequenza finale consigliata (ultra‑efficiente)

```text
1. Inizio sessione
2. Incolla manifest
3. Incolla mapping
4. Incolla file compressi
5. Ricostruzione
6. Analisi o modifiche
```

---
