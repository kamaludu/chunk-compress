Ecco i **prompt ottimali**, già calibrati per Copilot *Smart* e soprattutto *Think Deeper*, seguendo la pipeline più efficiente:

- **Prima** mapping (dizionario)  
- **Poi** file compressi  
- **Poi** ricostruzione  
- **Poi** analisi / modifiche  

Sono scritti per essere **copiati e incollati** senza modifiche.

---

# 1) **Inizia sessione**
Usalo come primo messaggio della chat.

> **PROMPT — Inizio sessione**  
> Sto per fornirti un dizionario di placeholder e poi uno o più file compressi che li utilizzano.  
> Il tuo compito sarà:  
> 1) leggere il mapping come *vocabolario* dei placeholder  
> 2) applicarlo ai file compressi  
> 3) ricostruire i file originali in modo esatto  
> 4) opzionalmente analizzarli o modificarli su mia richiesta  
>  
> Conferma quando sei pronto a ricevere il mapping.

---

# 2) **Incolla mapping_subset.json**
Dopo la conferma di Copilot, incolla il mapping.

> **PROMPT — Incolla mapping**  
> Questo è il mapping dei placeholder.  
> Usalo come dizionario `placeholder → contenuto`.  
> Non fare ancora nulla: limitati a confermare che il mapping è stato caricato correttamente.  
>  
> *(qui incolli `mapping_subset.json`)*

---

# 3) **Incolla file compressi**
Dopo che Copilot conferma di aver caricato il mapping.

> **PROMPT — Incolla file compressi**  
> Ora ti fornisco uno o più file compressi che contengono i placeholder del mapping.  
> Non ricostruire ancora: conferma solo che li hai ricevuti.  
>  
> *(incolla i file compressi, uno o più)*

---

# 4) **Chiedi ricostruzione**
Quando mapping + file compressi sono caricati.

> **PROMPT — Ricostruzione**  
> Ora ricostruisci il file (o i file) sostituendo ogni placeholder con il contenuto corrispondente dal mapping.  
>  
> Regole:  
> - nessuna invenzione  
> - nessuna correzione automatica  
> - ricostruzione *esatta* del testo originale  
> - se un placeholder non è nel mapping, segnalalo  
>  
> Restituisci il file ricostruito.

---

# 5) **Chiedi analisi o modifiche**
Dopo che Copilot ha ricostruito correttamente.

> **PROMPT — Analisi o modifiche**  
> Ora analizza il file ricostruito e produci:  
> - elenco dei problemi  
> - suggerimenti  
> - eventuali modifiche richieste  
>  
> Oppure, se voglio una trasformazione:  
>  
> “Applica le seguenti modifiche al file ricostruito: …”  
>  
> Mantieni sempre la struttura e non inventare contenuti non presenti.

---

# 🎯 Sequenza finale consigliata (ultra‑efficiente)
1. Inizia sessione  
2. Incolla mapping  
3. Incolla file compressi  
4. Ricostruzione  
5. Analisi o modifiche
x
---
